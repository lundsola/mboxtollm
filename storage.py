import logging
import os
from typing import Optional

import chromadb
from sentence_transformers import SentenceTransformer
import torch

from config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL

logger = logging.getLogger(__name__)


class EmailStore:
    """Persistent email storage and semantic search using ChromaDB."""

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        persist_dir = persist_dir or CHROMA_PERSIST_DIR
        model_name = model_name or EMBEDDING_MODEL

        os.makedirs(persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_dir)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Loading embedding model %s on %s", model_name, device)
        self.model = SentenceTransformer(model_name, device=device)

    def store_messages(self, messages: list[dict], collection_name: str = "emails"):
        """Store email messages with embeddings in ChromaDB."""
        collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Filter to messages with body text and a valid id
        valid = [m for m in messages if m.get("cleaned_body") and m.get("id")]

        if not valid:
            logger.warning("No valid messages to store")
            return 0

        # Deduplicate against already-stored ids
        existing_ids = set()
        try:
            existing = collection.get(ids=[m["id"] for m in valid])
            existing_ids = set(existing["ids"])
        except Exception:
            pass

        new_msgs = [m for m in valid if m["id"] not in existing_ids]
        if not new_msgs:
            logger.info("All %d messages already stored", len(valid))
            return 0

        # Batch encode and upsert
        bodies = [m["cleaned_body"] for m in new_msgs]
        logger.info("Embedding %d new messages...", len(new_msgs))
        embeddings = self.model.encode(bodies, show_progress_bar=True).tolist()

        ids = [m["id"] for m in new_msgs]
        documents = bodies
        metadatas = [
            {
                "subject": m.get("subject", ""),
                "from": m.get("from", ""),
                "to": m.get("to", ""),
                "date": str(m.get("date", "")),
                "conversation_id": m.get("conversation_id", ""),
                "in_reply_to": m.get("in_reply_to") or "",
            }
            for m in new_msgs
        ]

        # ChromaDB has a batch limit; insert in chunks
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            end = i + batch_size
            collection.add(
                ids=ids[i:end],
                embeddings=embeddings[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end],
            )

        logger.info("Stored %d messages in collection %r", len(new_msgs), collection_name)
        return len(new_msgs)

    def search(
        self,
        query: str,
        collection_name: str = "emails",
        k: int = 10,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """Semantic search over stored emails."""
        collection = self.client.get_or_create_collection(name=collection_name)

        query_embedding = self.model.encode([query]).tolist()
        kwargs = {
            "query_embeddings": query_embedding,
            "n_results": min(k, collection.count()),
        }
        if where:
            kwargs["where"] = where

        if collection.count() == 0:
            return []

        results = collection.query(**kwargs)

        hits = []
        for i in range(len(results["ids"][0])):
            hit = {
                "id": results["ids"][0][i],
                "cleaned_body": results["documents"][0][i],
                "distance": results["distances"][0][i] if results.get("distances") else None,
                **(results["metadatas"][0][i] if results.get("metadatas") else {}),
            }
            hits.append(hit)
        return hits

    def get_thread(
        self, conversation_id: str, collection_name: str = "emails"
    ) -> list[dict]:
        """Retrieve all messages in a conversation thread."""
        collection = self.client.get_or_create_collection(name=collection_name)

        results = collection.get(
            where={"conversation_id": conversation_id},
            include=["documents", "metadatas"],
        )

        messages = []
        for i in range(len(results["ids"])):
            msg = {
                "id": results["ids"][i],
                "cleaned_body": results["documents"][i],
                **(results["metadatas"][i] if results.get("metadatas") else {}),
            }
            messages.append(msg)

        # Sort by date
        messages.sort(key=lambda m: m.get("date", ""))
        return messages

    def get_message(self, message_id: str, collection_name: str = "emails") -> Optional[dict]:
        """Retrieve a single message by ID."""
        collection = self.client.get_or_create_collection(name=collection_name)
        results = collection.get(
            ids=[message_id], include=["documents", "metadatas"]
        )
        if not results["ids"]:
            return None
        return {
            "id": results["ids"][0],
            "cleaned_body": results["documents"][0],
            **(results["metadatas"][0] if results.get("metadatas") else {}),
        }

    def list_collections(self) -> list[dict]:
        """List all collections with their message counts."""
        collections = self.client.list_collections()
        return [
            {"name": c.name, "count": c.count()}
            for c in collections
        ]

    def collection_stats(self, collection_name: str = "emails") -> dict:
        """Get statistics for a collection."""
        collection = self.client.get_or_create_collection(name=collection_name)
        return {
            "name": collection_name,
            "count": collection.count(),
        }

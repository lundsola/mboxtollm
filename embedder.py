import logging

import faiss
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)


class Embedder:
    def __init__(self, model_name=None):
        model_name = model_name or EMBEDDING_MODEL
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Loading embedding model %s on %s...", model_name, self.device)
        self.model = SentenceTransformer(model_name, device=self.device)
        self.index = None
        self.messages = []

    def embed_messages(self, messages):
        filtered = [m for m in messages if m.get("cleaned_body")]
        if not filtered:
            logger.warning("No messages with body text to embed")
            return

        contents = [m["cleaned_body"] for m in filtered]
        logger.info("Generating embeddings for %d messages...", len(contents))
        vectors = self.model.encode(
            contents, show_progress_bar=True, device=self.device
        )
        vectors = np.array(vectors).astype("float32")

        self.index = faiss.IndexFlatL2(vectors.shape[1])
        self.index.add(vectors)
        self.messages = filtered
        logger.info("FAISS index built with %d vectors", self.index.ntotal)

    def search(self, query, k=5):
        if self.index is None:
            raise RuntimeError("No index built yet. Call embed_messages() first.")
        vec = self.model.encode([query], device=self.device)
        D, I = self.index.search(np.array(vec).astype("float32"), k)
        return [self.messages[i] for i in I[0] if i < len(self.messages)]

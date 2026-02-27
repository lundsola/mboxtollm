import logging

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings,
    KnowledgeGraphIndex,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.graph_stores.neo4j import Neo4jGraphStore

import chromadb

from config import (
    DATA_DIR,
    CHROMA_PERSIST_DIR,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    EMBEDDING_MODEL,
)

logger = logging.getLogger(__name__)


def build_index():
    # Step 1: Load documents
    logger.info("Loading documents from %s...", DATA_DIR)
    documents = SimpleDirectoryReader(DATA_DIR).load_data()

    # Step 2: Set up Chroma vector store
    logger.info("Setting up Chroma vector store at %s...", CHROMA_PERSIST_DIR)
    chroma_client = chromadb.Client()
    chroma_collection = chroma_client.get_or_create_collection("emails")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    embed_model = HuggingFaceEmbedding(
        model_name=f"sentence-transformers/{EMBEDDING_MODEL}"
    )
    Settings.embed_model = embed_model

    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Step 3: Create vector index
    logger.info("Creating vector index...")
    vector_index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
    )
    logger.info("Vector index created with Chroma")

    # Step 4: Connect to Neo4j for Knowledge Graph
    logger.info("Connecting to Neo4j and building Knowledge Graph...")
    graph_store = Neo4jGraphStore(
        username=NEO4J_USER,
        password=NEO4J_PASSWORD,
        url=NEO4J_URI,
    )
    kg_index = KnowledgeGraphIndex.from_documents(
        documents, graph_store=graph_store
    )
    logger.info("Knowledge graph created in Neo4j")

    return vector_index, kg_index


def query(vector_index, question: str, top_k: int = 5) -> str:
    query_engine = vector_index.as_query_engine(similarity_top_k=top_k)
    return str(query_engine.query(question))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    vi, _ = build_index()
    response = query(vi, "What did Ola say about wall anchoring?")
    print(response)

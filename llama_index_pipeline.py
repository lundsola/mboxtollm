from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    ServiceContext,
    KnowledgeGraphIndex,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.graph_stores.neo4j import Neo4jGraphStore

from chromadb.config import Settings as ChromaSettings
import chromadb
import os

# --- Config ---
DATA_DIR = "data"
CHROMA_PERSIST_DIR = "./chroma_store"
NEO4J_URL = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "your_password"  # 🔒 Replace with your actual password

# --- Step 1: Load documents ---
print("📂 Loading documents...")
documents = SimpleDirectoryReader(DATA_DIR).load_data()

# --- Step 2: Set up Chroma vector store ---
print("⚙️ Setting up Chroma vector store...")
chroma_client = chromadb.Client(ChromaSettings(anonymized_telemetry=False))
vector_store = ChromaVectorStore(
    chroma_collection_name="emails", chroma_client=chroma_client
)

embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
service_context = ServiceContext.from_defaults(embed_model=embed_model)

storage_context = StorageContext.from_defaults(vector_store=vector_store)

# --- Step 3: Create vector index ---
print("🔍 Creating vector index...")
vector_index = VectorStoreIndex.from_documents(
    documents,
    storage_context=storage_context,
    service_context=service_context,
)
print("✅ Vector index created with Chroma")

# --- Step 4: Connect to Neo4j for Knowledge Graph ---
print("🔌 Connecting to Neo4j and building Knowledge Graph...")
graph_store = Neo4jGraphStore(
    username=NEO4J_USERNAME,
    password=NEO4J_PASSWORD,
    url=NEO4J_URL,
)
kg_index = KnowledgeGraphIndex.from_documents(documents, graph_store=graph_store)
print("✅ Knowledge graph created in Neo4j")

# --- Step 5: Query example ---
print("💬 Running test query...")
query_engine = vector_index.as_query_engine(similarity_top_k=5)
response = query_engine.query("What did Ola say about wall anchoring?")
print("\n📬 Response:")
print(response)

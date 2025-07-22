import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import torch

class Embedder:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        print("🧠 Loading embedding model...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"💻 Embedding will run on: {self.device.upper()}")
        self.model = SentenceTransformer(model_name, device=self.device)
        self.index = None
        self.messages = []

    def embed_messages(self, messages):
        # Ensure all messages have a non-empty cleaned body
        filtered = [m for m in messages if m.get("cleaned_body")]
        contents = [m["cleaned_body"] for m in filtered]

        print(f"🧠 Generating embeddings for {len(contents)} messages...")
        vectors = self.model.encode(
            contents,
            show_progress_bar=True,
            device=self.device
        )

        # Create FAISS index
        self.index = faiss.IndexFlatL2(vectors[0].shape[0])
        self.index.add(np.array(vectors).astype("float32"))
        self.messages = filtered

    def search(self, query, k=5):
        vec = self.model.encode([query], device=self.device)
        D, I = self.index.search(np.array(vec).astype("float32"), k)
        return [self.messages[i] for i in I[0]]


# 📬 mboxtollm

**mboxtollm** is an open-source pipeline to transform large `.mbox` email archives into a threaded, deduplicated **knowledge graph** and **vector store** — optimized for use in Retrieval-Augmented Generation (RAG) workflows with ChatGPT, Ollama, or other LLMs.

---

## ✨ Features

- Parses `.mbox` files without loading everything into memory
- Extracts and deduplicates new email content (removing quoted replies)
- Reconstructs threads using `Message-ID` and `In-Reply-To`
- Builds an in-memory graph with `networkx`
- Embeds emails using `sentence-transformers`
- Stores vector embeddings in FAISS for fast semantic search
- Designed to be extended into Neo4j, Flask API, or ChatGPT Plugins

---

## 📦 Install

```bash
git clone https://github.com/yourusername/mboxtollm.git
cd mboxtollm
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# mboxtollm

**mboxtollm** is an open-source pipeline to transform large `.mbox` and `.pst` email archives into a threaded, deduplicated **knowledge graph** and **vector store** — optimized for use in Retrieval-Augmented Generation (RAG) workflows with ChatGPT, Ollama, or other LLMs.

---

## Features

- Parses `.mbox` files and `.eml` folders without loading everything into memory
- Extracts Outlook `.pst` archives via the Windows COM API
- Extracts and deduplicates new email content (removing quoted replies)
- Reconstructs threads using `Message-ID`, `In-Reply-To`, and `conversation_id`
- Builds an in-memory graph with `networkx`
- Embeds emails using `sentence-transformers` (GPU-accelerated when available)
- Stores vector embeddings in FAISS for fast semantic search
- Extracts entities and triplets with spaCy for knowledge graph construction
- Exports to Neo4j for persistent graph storage
- Integrates with LlamaIndex + ChromaDB for advanced RAG pipelines

---

## Install

```bash
git clone https://github.com/lundsola/mboxtollm.git
cd mboxtollm
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Optional extras

```bash
# For Outlook PST extraction (Windows only)
pip install -e ".[outlook]"

# For LlamaIndex RAG pipeline
pip install -e ".[llama]"

# For entity/triplet extraction with spaCy
pip install -e ".[ner]"
python -m spacy download en_core_web_trf

# For development (pytest)
pip install -e ".[dev]"
```

---

## Configuration

Copy the example environment file and edit it:

```bash
cp .env.example .env
```

Key settings:

| Variable | Default | Description |
|---|---|---|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j connection URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `changeme` | Neo4j password |
| `INPUT_FILE` | `data/pst_output.jsonl` | Default input file |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer model |

---

## Usage

### 1. Extract emails to JSONL

From an `.eml` folder:
```bash
make extract-eml
```

From Outlook PST (Windows only):
```bash
make extract-pst
```

### 2. Run the pipeline

```bash
# Default: loads data/pst_output.jsonl, builds graph + embeddings, runs example query
make run

# Custom input and query
python main.py -i data/my_emails.mbox -q "project deadline"

# Verbose logging
python main.py -v
```

### 3. Export to Neo4j

```bash
# Export email thread graph
make export-neo4j

# Export entity triplets
python triplets_to_neo4js.py
```

### 4. Run LlamaIndex RAG pipeline

```bash
python llama_index_pipeline.py
```

---

## Architecture

```
.mbox / .eml / .pst
        |
        v
  +--------------+
  | Email Parser |  -> JSONL (cleaned, deduplicated)
  +------+-------+
         |
    +----+----+
    v         v
+--------+ +----------+
| Graph  | | Embedder |
|Builder | | (FAISS)  |
+---+----+ +----+-----+
    |           |
    v           v
  Neo4j    Semantic Search / RAG
```

---

## Running tests

```bash
make test
```

---

## License

MIT

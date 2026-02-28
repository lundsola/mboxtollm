# mboxtollm

**mboxtollm** is a service that lets you upload old email archives (`.mbox`, `.eml`, `.pst`), search them semantically, and use AI to generate summaries and storylines from decades of email history.

Built for people who have 25+ years of email archives and want to actually find things in them.

---

## Features

**Email ingestion**
- Parses `.mbox` files and `.eml` folders
- Extracts Outlook `.pst` archives via Windows COM API
- Cleans and deduplicates content (strips quoted replies)
- Reconstructs conversation threads from email headers

**Search & AI**
- Semantic search powered by sentence-transformers + ChromaDB
- Ask natural-language questions answered by Claude (Anthropic)
- Summarize conversation threads with one API call
- Generate chronological storylines about any topic from your archive

**API**
- REST API (FastAPI) for all operations
- Upload files, search, ask questions, get storylines
- Background processing for large archives
- Persistent storage — upload once, search forever

---

## Quick start

```bash
git clone https://github.com/lundsola/mboxtollm.git
cd mboxtollm
python3 -m venv venv
source venv/bin/activate
pip install -e .

# Configure
cp .env.example .env
# Edit .env — set at minimum ANTHROPIC_API_KEY

# Start the API server
make serve
```

The API is now running at `http://localhost:8000`. Visit `http://localhost:8000/docs` for interactive API documentation.

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/upload` | Upload .mbox or .jsonl file for processing |
| `POST` | `/search` | Semantic search across stored emails |
| `POST` | `/ask` | Ask a question — retrieves context, answers with Claude |
| `POST` | `/summarize` | Summarize a thread (by conversation_id or message_ids) |
| `POST` | `/storyline` | Generate a chronological narrative about a topic |
| `GET` | `/threads/{id}` | Get all messages in a conversation |
| `GET` | `/collections` | List all email collections |
| `GET` | `/collections/{name}/stats` | Collection statistics |
| `GET` | `/health` | Health check |

### Example: Upload and search

```bash
# Upload an archive
curl -X POST http://localhost:8000/upload \
  -F "file=@my_emails.mbox" \
  -F "collection=work"

# Search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "budget meeting Q3", "collection": "work"}'

# Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What did we decide about the office move?"}'

# Generate a storyline
curl -X POST http://localhost:8000/storyline \
  -H "Content-Type: application/json" \
  -d '{"topic": "the Johnson project from 2003 to 2005"}'
```

---

## CLI usage

The original CLI still works for quick local processing:

```bash
# Process a file and search from the terminal
python main.py -i data/my_emails.mbox -q "project deadline"

# Extract emails to JSONL first
make extract-eml      # from .eml folder
make extract-pst      # from Outlook PST (Windows only)
```

---

## Configuration

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | (required) | Your Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Claude model to use |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer model |
| `CHROMA_PERSIST_DIR` | `./chroma_store` | Where ChromaDB stores data |
| `UPLOAD_DIR` | `data/uploads` | Where uploaded files are saved |
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |

---

## Optional extras

```bash
pip install -e ".[outlook]"   # PST extraction (Windows only)
pip install -e ".[ner]"       # Entity extraction with spaCy
pip install -e ".[neo4j]"     # Neo4j graph export
pip install -e ".[dev]"       # pytest + httpx for testing
```

---

## Architecture

```
Upload .mbox/.eml/.pst
         |
         v
  +---------------+
  | Email Parser  |  parse, clean, dedup, thread
  +-------+-------+
          |
    +-----+------+
    v            v
+--------+  +----------+
| Thread |  | ChromaDB |  persistent vector store
| Graph  |  +-----+----+
+--------+        |
                  v
          +-------+--------+
          | FastAPI Server |
          +--+----+----+---+
             |    |    |
             v    v    v
         search  ask  storyline
                  |    |
                  v    v
              Claude (Anthropic)
```

---

## Running tests

```bash
make test
```

---

## License

MIT

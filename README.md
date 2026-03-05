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
- Ask natural-language questions answered by your choice of LLM
- Summarize conversation threads with one API call
- Generate chronological storylines about any topic from your archive
- Supports **Anthropic Claude**, **OpenAI GPT**, and **Google Gemini**

**Web interface**
- Upload archives via drag & drop
- Search with real-time results
- Ask questions and get AI-powered answers
- Generate storylines from any topic
- Collection management (multi-tenant: each user/project gets its own collection)

**Deployment**
- Docker + Docker Compose for one-command deployment
- Persistent storage via volumes
- Health checks built in

---

## Quick start with Docker

```bash
git clone https://github.com/lundsola/mboxtollm.git
cd mboxtollm
cp .env.example .env
# Edit .env — set your LLM API key

docker compose up -d
```

Open `http://localhost:8000` for the web interface, or `http://localhost:8000/docs` for API documentation.

## Quick start without Docker

```bash
git clone https://github.com/lundsola/mboxtollm.git
cd mboxtollm
python3 -m venv venv
source venv/bin/activate
pip install -e ".[anthropic]"

cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY

make serve
```

---

## Web interface

The built-in web UI has four tabs:

- **Search** — semantic search across your email archive
- **Ask** — ask natural-language questions, get AI answers with source citations
- **Storyline** — generate chronological narratives about any topic
- **Upload** — drag & drop `.mbox` or `.jsonl` files, manage collections

---

## API endpoints

All API endpoints are under `/api/`:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/upload` | Upload .mbox or .jsonl file for processing |
| `POST` | `/api/search` | Semantic search across stored emails |
| `POST` | `/api/ask` | Ask a question — retrieves context, answers with LLM |
| `POST` | `/api/summarize` | Summarize a thread (by conversation_id or message_ids) |
| `POST` | `/api/storyline` | Generate a chronological narrative about a topic |
| `GET` | `/api/threads/{id}` | Get all messages in a conversation |
| `GET` | `/api/collections` | List all email collections |
| `GET` | `/api/collections/{name}/stats` | Collection statistics |
| `GET` | `/api/health` | Health check |

### Example: Upload and search

```bash
# Upload an archive
curl -X POST http://localhost:8000/api/upload \
  -F "file=@my_emails.mbox" \
  -F "collection=work"

# Search
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "budget meeting Q3", "collection": "work"}'

# Ask a question
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What did we decide about the office move?"}'

# Generate a storyline
curl -X POST http://localhost:8000/api/storyline \
  -H "Content-Type: application/json" \
  -d '{"topic": "the Johnson project from 2003 to 2005"}'
```

---

## Configuration

```bash
cp .env.example .env
```

### LLM provider

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `anthropic` | Which LLM to use: `anthropic`, `openai`, or `google` |
| `ANTHROPIC_API_KEY` | | Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Claude model |
| `OPENAI_API_KEY` | | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model |
| `GOOGLE_API_KEY` | | Google Gemini API key |
| `GOOGLE_MODEL` | `gemini-2.0-flash` | Gemini model |

### Storage & server

| Variable | Default | Description |
|---|---|---|
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer model |
| `CHROMA_PERSIST_DIR` | `./chroma_store` | ChromaDB storage path |
| `UPLOAD_DIR` | `data/uploads` | Uploaded files directory |
| `API_PORT` | `8000` | Server port |

---

## Optional extras

```bash
pip install -e ".[anthropic]"   # Anthropic Claude
pip install -e ".[openai]"      # OpenAI GPT
pip install -e ".[google]"      # Google Gemini
pip install -e ".[all-llms]"    # All three LLM providers
pip install -e ".[outlook]"     # PST extraction (Windows only)
pip install -e ".[ner]"         # Entity extraction with spaCy
pip install -e ".[neo4j]"       # Neo4j graph export
pip install -e ".[dev]"         # pytest + httpx for testing
```

---

## CLI usage

The CLI still works for quick local processing:

```bash
python main.py -i data/my_emails.mbox -q "project deadline"
make extract-eml      # from .eml folder
make extract-pst      # from Outlook PST (Windows only)
```

---

## Architecture

```
            Browser / curl
                |
                v
        +-------+--------+
        | FastAPI + Web UI |
        +--+----+----+----+
           |    |    |    |
           v    v    v    v
       upload search ask storyline
           |    |    |    |
           v    v    v    v
      +--------+ +------+------+
      | Parser | | ChromaDB    |
      | Thread | | (persistent |
      | Graph  | |  vectors)   |
      +--------+ +------+------+
                         |
                    +----+----+
                    |  LLM    |
                    | Provider|
                    +-+--+--+-+
                      |  |  |
                      v  v  v
                Anthropic / OpenAI / Google
```

---

## Running tests

```bash
make test
```

---

## License

MIT

import logging
import os
import shutil
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, LLM_PROVIDER, UPLOAD_DIR
from graph_builder import build_thread_graph
from load_messages import load_messages
from storage import EmailStore

logger = logging.getLogger(__name__)

store: Optional[EmailStore] = None
llm = None  # Lazy-loaded to avoid requiring API key for search-only use


@asynccontextmanager
async def lifespan(app: FastAPI):
    global store
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    logger.info("Initializing email store...")
    store = EmailStore()
    logger.info("Ready.")
    yield


app = FastAPI(
    title="mboxtollm",
    description="Search, summarize, and build storylines from email archives",
    version="0.4.0",
    lifespan=lifespan,
)


def _has_any_llm_key() -> bool:
    return bool(ANTHROPIC_API_KEY or OPENAI_API_KEY or GOOGLE_API_KEY)


def _get_llm():
    """Lazy-load the LLM provider."""
    global llm
    if llm is None:
        if not _has_any_llm_key():
            raise HTTPException(
                status_code=503,
                detail="No LLM API key configured. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY in .env",
            )
        from llm_provider import LLMProvider

        llm = LLMProvider()
    return llm


# --- Request/Response models ---


class SearchRequest(BaseModel):
    query: str
    k: int = 10
    collection: str = "emails"


class SummarizeRequest(BaseModel):
    message_ids: Optional[list[str]] = None
    conversation_id: Optional[str] = None
    collection: str = "emails"


class StorylineRequest(BaseModel):
    topic: str
    k: int = 20
    collection: str = "emails"


class AskRequest(BaseModel):
    question: str
    k: int = 10
    collection: str = "emails"


# --- Background task: process uploaded file ---


def _process_upload(filepath: str, collection: str):
    """Parse and store an uploaded email archive (runs in background)."""
    try:
        logger.info("Processing upload: %s -> collection %r", filepath, collection)
        messages = load_messages(filepath)
        logger.info("Parsed %d messages from %s", len(messages), filepath)

        graph = build_thread_graph(messages)
        logger.info(
            "Thread graph: %d nodes, %d edges",
            graph.number_of_nodes(),
            graph.number_of_edges(),
        )

        stored = store.store_messages(messages, collection_name=collection)
        logger.info("Stored %d new messages", stored)
    except Exception:
        logger.exception("Failed to process upload: %s", filepath)


# --- API Endpoints ---


@app.post("/api/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    collection: str = Query(default="emails", description="Target collection name"),
):
    """Upload an .mbox or .jsonl email archive for processing."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in (".mbox", ".jsonl"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {suffix}. Use .mbox or .jsonl",
        )

    upload_id = uuid.uuid4().hex[:12]
    safe_name = f"{upload_id}{suffix}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    logger.info("Saved upload %s (%s)", safe_name, file.filename)
    background_tasks.add_task(_process_upload, filepath, collection)

    return {
        "status": "processing",
        "upload_id": upload_id,
        "filename": file.filename,
        "collection": collection,
    }


@app.post("/api/search")
async def search(req: SearchRequest):
    """Semantic search across stored emails."""
    results = store.search(query=req.query, collection_name=req.collection, k=req.k)
    return {"query": req.query, "count": len(results), "results": results}


@app.post("/api/ask")
async def ask(req: AskRequest):
    """Ask a question — retrieves relevant emails then answers using the configured LLM."""
    provider = _get_llm()

    context = store.search(query=req.question, collection_name=req.collection, k=req.k)
    if not context:
        raise HTTPException(status_code=404, detail="No relevant emails found")

    answer = provider.answer_question(req.question, context)
    return {
        "question": req.question,
        "answer": answer,
        "sources": [
            {"id": m["id"], "subject": m.get("subject", ""), "from": m.get("from", "")}
            for m in context
        ],
    }


@app.post("/api/summarize")
async def summarize(req: SummarizeRequest):
    """Summarize a conversation thread using the configured LLM."""
    provider = _get_llm()

    if req.conversation_id:
        messages = store.get_thread(req.conversation_id, collection_name=req.collection)
    elif req.message_ids:
        messages = []
        for mid in req.message_ids:
            msg = store.get_message(mid, collection_name=req.collection)
            if msg:
                messages.append(msg)
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either conversation_id or message_ids",
        )

    if not messages:
        raise HTTPException(status_code=404, detail="No messages found")

    summary = provider.summarize_thread(messages)
    return {"message_count": len(messages), "summary": summary}


@app.post("/api/storyline")
async def storyline(req: StorylineRequest):
    """Generate a chronological narrative about a topic from the email archive."""
    provider = _get_llm()

    context = store.search(query=req.topic, collection_name=req.collection, k=req.k)
    if not context:
        raise HTTPException(status_code=404, detail="No relevant emails found")

    context.sort(key=lambda m: m.get("date", ""))

    story = provider.generate_storyline(context, req.topic)
    return {
        "topic": req.topic,
        "email_count": len(context),
        "storyline": story,
        "date_range": {
            "earliest": context[0].get("date", "unknown"),
            "latest": context[-1].get("date", "unknown"),
        },
    }


@app.get("/api/threads/{conversation_id}")
async def get_thread(conversation_id: str, collection: str = "emails"):
    """Get all messages in a conversation thread."""
    messages = store.get_thread(conversation_id, collection_name=collection)
    if not messages:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"conversation_id": conversation_id, "count": len(messages), "messages": messages}


@app.get("/api/collections")
async def list_collections():
    """List all email collections."""
    return {"collections": store.list_collections()}


@app.get("/api/collections/{name}/stats")
async def collection_stats(name: str):
    """Get stats for a collection."""
    return store.collection_stats(name)


@app.get("/api/health")
async def health():
    """Health check."""
    return {
        "status": "ok",
        "llm_provider": LLM_PROVIDER,
        "llm_configured": _has_any_llm_key(),
    }


# --- Serve web frontend ---

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    """Serve the web frontend."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "mboxtollm API. Visit /docs for API documentation."}

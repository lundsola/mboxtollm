# Gemini embeddings pilot

Gemini is available alongside the unchanged local encoder. TerminusDB remains
authoritative; SQLite vectors are derived. No local model or new SDK is required.

Set `GEMINI_API_KEY` securely in the runtime environment. Do not paste keys in
chat, commit them, or put their value on the command line. The Jev key is separate.
Confirm your Google project billing, quotas and applicable data-use terms before
using real mail. Indexing sends subject and body spans to Google; searching sends
queries, and candidate discovery sends source email spans. Jev is separately opt-in.

With TerminusDB environment variables already configured:

```bash
python semantic_cli.py --archive pilot --index pilot-gemini.sqlite --embedding-provider gemini --allow-google index
python semantic_cli.py --archive pilot --index pilot-gemini.sqlite --embedding-provider gemini --allow-google search 'Vilka mejl handlar om samma projekt?'
```

Use a NEW index path when switching from a local model. Do not mix vector spaces.
The adapter uses `gemini-embedding-2`, 768 dimensions, retrieval-specific query
and document prefixes, and one HTTP request per span (no multi-input aggregation).
Subject and body remain separately weighted by the existing retrieval code.
No title is duplicated into body vectors. Identity records model, dimensions,
prompt format and chunk policy; Google's model name is not an immutable weights
revision. Re-evaluate and rebuild if provider behavior changes.

Conservative chunking caps input at 1000 UTF-8 bytes and preserves source spans.
Queries exceeding that cap fail rather than truncate. HTTP errors, quota errors,
invalid responses and timeouts fail safely without retries or provider error text.
Reindex failure rolls back the current email; previously indexed emails remain.
Rerunning indexing currently embeds them again, so start with a small dedicated
synthetic archive and monitor cost. There is no ANN, caching, quota scheduler or
production-scale throughput guarantee yet.

Verification: `python -m unittest discover -s tests -p 'test_semantic*.py'`.
Gemini tests use an injected fake transport; no Google call or semantic quality
evaluation is performed by tests. Live credentials, model access, retrieval quality
and costs still require a separate runtime smoke test.

Official API and formatting reference:
https://ai.google.dev/gemini-api/docs/embeddings

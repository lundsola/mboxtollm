# Semantic retrieval pilot

The new opt-in path is:
TerminusDB Email -> local or Gemini subject/body embeddings -> candidate retrieval ->
optional Jev evaluation -> TerminusDB RelationAssessment documents.
The legacy API and web UI are unchanged. No live models or services run on import.

## What is implemented

- Separate subject and body vectors. Long fields split into lossless character
  spans until they fit the tokenizer budget; no silent model truncation.
- One best chunk per field and email. Default score is 35% subject / 65% body;
  these are provisional weights, not calibrated relevance probabilities.
- Persistent SQLite derived vectors and snippets; one email updated atomically.
- Query-scoped archive filtering, model-identity and dimension checks.
- Read-only agent tools: search, read_email, thread, candidates. These are Python
  operations ready for orchestration, not an autonomous agent or MCP server yet.
- Budgeted candidate evaluation: max 20 pairs per explicit invocation, default 5.
- Jev's judgments stored as unreviewed assessments with real Email references,
  input hashes, model and question versions. They never become accepted facts.

## Running

For Google-hosted embeddings without local weights, see [GEMINI.md](GEMINI.md).
The local commands below remain supported; changing provider needs a new index.

Install the existing sentence-transformers dependency and terminusdb-client in a
virtual environment. Provision a local symmetric text embedding model and note
its immutable revision. LocalEncoder refuses automatic weight downloads and uses
plain encode, so models requiring query/document prefixes need a future adapter.
The revision label is caller-supplied, not a verified weight checksum.

Use the same TerminusDB environment variables as TERMINUSDB.md. Common CLI options:

```sh
python semantic_cli.py --archive pilot --index /private/pilot.sqlite --model-path /models/embedding --model-revision COMMIT_SHA index
python semantic_cli.py --archive pilot --index /private/pilot.sqlite --model-path /models/embedding --model-revision COMMIT_SHA search 'projektets budget'
python semantic_cli.py --archive pilot --index /private/pilot.sqlite --model-path /models/embedding --model-revision COMMIT_SHA candidates Email/ID
```

On a dedicated test DB, initialize RelationAssessment once using the
`init-assessment-schema` subcommand (Email schema must already exist).
`assess Email/ID --max-pairs 5 --allow-external` explicitly permits selected email
content to leave the machine. Requires TYPESAFE_API_KEY. Do not use real mail
until privacy/retention and access controls have been reviewed. Long candidates
can fail Jev's input limit; no automatic truncation or retries. Earlier successful
pairs remain saved if a later pair fails; re-evaluation upserts the same IDs.

## Honest limitations

This is exact cosine search scanning the archive's vectors, not an ANN backend.
It is suitable for correctness tests and small pilots, NOT the 10M-triple archive.
Candidate generation searches each source chunk, so compute still grows with
source length. Replace this backend with ANN before bulk relation generation.
There is no cross-process ingestion queue, durable checkpoints, or delete sync.
After deleting authoritative emails, rebuild the derived index at a new path;
read_email and assessment writes recheck membership but raw search can be stale.
The local index contains private snippets and needs filesystem access protection.
Archive scoping is not authentication: only a trusted caller may select an archive.

No semantic quality claims are made from fake embeddings. Production acceptance
needs a local real model, labeled Swedish/English search cases, relation precision
evaluation, and live TerminusDB schema/round-trip verification. HTML-only mail
still contains markup. Character splitting has no overlap; improve boundaries
and chunk context based on evaluation rather than assuming optimal retrieval.

```sh
python -m unittest discover -s tests -p 'test_semantic*.py'
python -m unittest discover -s tests -p 'test_jev*.py'
python -m unittest discover -s tests -p 'test_terminus*.py'
```

Tests use synthetic vectors, mail and Jev responses. The explicit TerminusDB
integration test remains opt-in, as described in TERMINUSDB.md.

# TerminusDB pilot (opt-in)

Legacy FastAPI/Chroma and Neo4j scripts are unchanged. This milestone adds a
separate CLI, not a production migration. Retain original archives outside git.

Install `terminusdb-client` in a virtual environment. Create a NEW schema-enabled
database on your own TerminusDB instance first; the CLI never creates/deletes DBs.
Set `TERMINUSDB_URL`, `TERMINUSDB_DATABASE`, `TERMINUSDB_KEY` and optionally
`TERMINUSDB_TEAM` / `TERMINUSDB_USER` (default `admin`). Never commit secrets.

```sh
python terminus_store.py --archive pilot --init-schema
python terminus_store.py --archive pilot --mbox /path/to/synthetic.mbox
python terminus_store.py --archive pilot --mbox /path/to/synthetic.mbox
python terminus_store.py --archive pilot --thread '<root@example.test>'
python -m unittest discover -s tests -p 'test_terminus*.py'
```

Initialize schema once. Schema conflicts and import errors propagate to the CLI.
An import is atomic per batch, not per archive; rerun after failure. `processed`
counts source records, not new documents. Stable IDs include archive, Message-ID
and source hash, so same-ID/different-content variants are preserved. References
remain strings so replies can arrive before parents. No LLM sends mail externally.

## Verification and limits

Unit tests use an in-memory client double: they do NOT verify server schema/API
compatibility. Before connecting the UI, run the above sequence against a disposable
database and verify three stored documents and a two-message thread for the test
fixture. No production database should be used for this acceptance check.

Alternatively set `TERMINUSDB_TEST_DATABASE` to a NEW disposable schema-enabled
database and run the unittest command to enable the real-server acceptance test.
It installs the schema and leaves synthetic data for inspection; use a fresh
database for each run. Without this variable the integration test is skipped.

Thread retrieval currently scans one archive and returns stable ID order, not date
order. It is a correctness pilot, not suitable for the previous 10M-triple scale.
Next: server-side traversal, explicit person/reply documents, durable job status,
raw-source storage, MIME/attachment hardening, integration tests and derived vector
index synchronization. UI authentication must precede exposing real email archives.

Client contract: https://terminusdb.com/docs/python/
Schema: https://terminusdb.com/docs/add-a-document/

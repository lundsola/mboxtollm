# Project direction

Evolve mboxtollm into an email knowledge service with TerminusDB as the
authoritative document/graph store. Keep the existing Chroma application working
until the new path has integration tests. Vector indexes are derived data.

## Working rules
- Never commit real email archives, credentials, or extracted private content.
- Use synthetic fixtures. No LLM calls or production database writes in tests.
- Preserve source text and provenance; do not silently discard malformed mail.
- Stable IDs and repeatable imports are required. Keep archive boundaries explicit.
- Keep facts from email separate from model-generated claims.
- Do not remove the legacy pipeline or migrate existing stores implicitly.
- Run `python -m unittest discover -s tests -p 'test_terminus*.py'` for the pilot.
- Report mocked tests separately from real database integration tests.

## Current milestone
An opt-in CLI imports MBOX into a dedicated TerminusDB database and retrieves
reply-connected threads. No web API integration or vector search migration yet.

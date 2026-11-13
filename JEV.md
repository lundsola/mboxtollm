# Jev relation evaluation (optional, not wired to ingestion)

`jev_relations.JevRelationEvaluator` judges a candidate pair already selected by
search. It does not compute embeddings, generate relation explanations, persist
graph edges, or autonomously search. Those integrations are subsequent work.

The module uses the documented HTTP endpoint directly (Python standard library),
so it requires no SDK installation. Contract checked against
https://docs.typesafe.ai/introduction/quickstart .

## Security and configuration

External evaluation is disabled by default. Explicitly construct the evaluator
with `enabled=True` only when sending the candidate content is approved. Set
`TYPESAFE_API_KEY` in the runtime secret store or environment, never in git/chat.
The environment variable is not read from a .env file automatically.

Only subject, body, ID and archive of each candidate are sent. Even these may be
sensitive: start with synthetic mail. No live call is made by import or tests.
HTTP redirects are refused; errors exclude response bodies; no automatic retries
or background batch spend. Input above 24,000 serialized characters fails rather
than silently truncating. This is a safety budget, not a documented token limit.

## Python usage (requires explicit external-data approval)

```python
from jev_relations import JevRelationEvaluator

evaluator = JevRelationEvaluator(enabled=True, model="jev-latest")
# a and b: Terminus pilot Email documents, same archive, different @id values.
assessments = evaluator.evaluate(a, b)
```

Independent Noul questions assess same project, same event, and B following up A.
All results, including low scores, remain `unreviewed` assessments, not facts.
There is deliberately no automatic acceptance threshold before evaluation on a
labeled dataset. A valid typed answer can still be wrong. Input text is untrusted;
the question instructions are a mitigation, not a prompt-injection guarantee.

Records include email IDs, input hash, requested/returned model, question version
and timestamp. IDs identify the same input/model/question assessment, not unique
execution events. Retain versioned source documents separately for reproducibility.
`jev-latest` is mutable: configure an available pinned model for repeatable runs.

## Tests and next integration

Run `python -m unittest discover -s tests -p 'test_jev*.py'`.
Tests mock transport and use only synthetic data; live API behavior is unverified.
Next: subject/body embeddings -> bounded candidate selection -> these assessments
-> explicit TerminusDB assessment schema/persistence -> evaluated review policy.

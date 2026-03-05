import json
import logging
import re

from neo4j import GraphDatabase
from tqdm import tqdm

from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger(__name__)

INPUT_FILE = "data/triplets_with_email.jsonl"
BATCH_SIZE = 1000

# Only allow safe relationship names (alphanumeric + underscore)
_SAFE_REL_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def create_constraints(tx):
    tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Email) REQUIRE e.id IS UNIQUE")
    tx.run(
        "CREATE CONSTRAINT IF NOT EXISTS FOR (ent:Entity) REQUIRE ent.name IS UNIQUE"
    )


def _sanitize_rel_type(predicate: str) -> str:
    """Convert a predicate to a safe Neo4j relationship type."""
    rel = predicate.upper().replace(" ", "_")
    if not _SAFE_REL_RE.match(rel):
        raise ValueError(f"Unsafe relationship type: {rel!r}")
    return rel


def insert_batch(tx, batch):
    for row in batch:
        subj = row["subject"]
        rel_type = _sanitize_rel_type(row["predicate"])
        obj = row["object"]
        email_id = row["email_id"]

        # Use APOC or parameterised relationship creation.
        # Since relationship types cannot be parameterised in Cypher,
        # we validate the string above to prevent injection.
        tx.run(
            f"""
            MERGE (s:Entity {{name: $subj}})
            MERGE (o:Entity {{name: $obj}})
            MERGE (s)-[:{rel_type}]->(o)
            MERGE (e:Email {{id: $email_id}})
            MERGE (s)-[:MENTIONED_IN]->(e)
            MERGE (o)-[:MENTIONED_IN]->(e)
            """,
            subj=subj,
            obj=obj,
            email_id=email_id,
        )


def main():
    logging.basicConfig(level=logging.INFO)

    logger.info("Reading triplets from %s...", INPUT_FILE)
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]

    logger.info("Loaded %d triplets", len(lines))

    with driver.session() as session:
        logger.info("Creating constraints...")
        session.execute_write(create_constraints)

        logger.info("Inserting triplets into Neo4j...")
        for i in tqdm(range(0, len(lines), BATCH_SIZE), desc="Inserting"):
            batch = lines[i : i + BATCH_SIZE]
            session.execute_write(insert_batch, batch)

    logger.info("Import complete.")


if __name__ == "__main__":
    main()

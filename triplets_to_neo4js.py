import json
from neo4j import GraphDatabase
from tqdm import tqdm

INPUT_FILE = "data/triplets_with_email.jsonl"
BATCH_SIZE = 1000

# Neo4j credentials
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "test1234"  # Replace with your actual Neo4j password

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def create_constraints(tx):
    tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Email) REQUIRE e.id IS UNIQUE")
    tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (ent:Entity) REQUIRE ent.name IS UNIQUE")


def insert_batch(tx, batch):
    for row in batch:
        subj = row["subject"]
        pred = row["predicate"].upper().replace(" ", "_")
        obj = row["object"]
        email_id = row["email_id"]

        tx.run(f"""
            MERGE (s:Entity {{name: $subj}})
            MERGE (o:Entity {{name: $obj}})
            MERGE (s)-[:{pred}]->(o)
            MERGE (e:Email {{id: $email_id}})
            MERGE (s)-[:MENTIONED_IN]->(e)
            MERGE (o)-[:MENTIONED_IN]->(e)
        """, subj=subj, obj=obj, email_id=email_id)


def main():
    print("📥 Reading triplets from file...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]

    print(f"📦 Loaded {len(lines):,} triplets")

    with driver.session() as session:
        print("🔒 Creating constraints...")
        session.execute_write(create_constraints)

        print("🚀 Inserting triplets into Neo4j...")
        for i in tqdm(range(0, len(lines), BATCH_SIZE), desc="Inserting"):
            batch = lines[i:i + BATCH_SIZE]
            session.execute_write(insert_batch, batch)

    print("✅ Import complete.")


if __name__ == "__main__":
    main()

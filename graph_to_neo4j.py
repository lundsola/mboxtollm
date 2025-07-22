# graph_to_neo4j.py

from neo4j import GraphDatabase
from load_messages import load_messages
from graph_builder import build_thread_graph
import os

class Neo4jExporter:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def export_graph(self, G):
        with self.driver.session() as session:
            print("📤 Creating constraints...")
            session.run("CREATE CONSTRAINT email_id IF NOT EXISTS FOR (e:Email) REQUIRE e.id IS UNIQUE")

            print("📤 Inserting nodes...")
            for node_id, data in G.nodes(data=True):
                session.run("""
                    MERGE (e:Email {id: $id})
                    SET e.subject = $subject,
                        e.sender = $sender,
                        e.date = $date,
                        e.body = $body
                """, {
                    "id": node_id,
                    "subject": data.get("subject"),
                    "sender": data.get("from"),
                    "date": str(data.get("date")),
                    "body": data.get("cleaned_body")
                })

            print("🔗 Creating edges...")
            for src, tgt in G.edges():
                session.run("""
                    MATCH (a:Email {id: $src}), (b:Email {id: $tgt})
                    MERGE (a)-[:REPLY_TO]->(b)
                """, {"src": src, "tgt": tgt})

            print("✅ Done exporting graph.")

if __name__ == "__main__":
    INPUT_FILE = "data/pst_output.jsonl"

    print("📥 Loading and building graph...")
    messages = load_messages(INPUT_FILE)
    G = build_thread_graph(messages)

    exporter = Neo4jExporter("bolt://localhost:7687", "neo4j", "test1234")
    exporter.export_graph(G)
    exporter.close()


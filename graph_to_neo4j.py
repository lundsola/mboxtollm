import logging
import os

from neo4j import GraphDatabase

from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, INPUT_FILE
from load_messages import load_messages
from graph_builder import build_thread_graph

logger = logging.getLogger(__name__)


class Neo4jExporter:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def export_graph(self, G):
        with self.driver.session() as session:
            logger.info("Creating constraints...")
            session.run(
                "CREATE CONSTRAINT email_id IF NOT EXISTS "
                "FOR (e:Email) REQUIRE e.id IS UNIQUE"
            )

            logger.info("Inserting %d nodes...", G.number_of_nodes())
            for node_id, data in G.nodes(data=True):
                session.run(
                    """
                    MERGE (e:Email {id: $id})
                    SET e.subject = $subject,
                        e.sender = $sender,
                        e.date = $date,
                        e.body = $body
                    """,
                    {
                        "id": node_id,
                        "subject": data.get("subject"),
                        "sender": data.get("from"),
                        "date": str(data.get("date")),
                        "body": data.get("cleaned_body"),
                    },
                )

            logger.info("Creating %d edges...", G.number_of_edges())
            for src, tgt in G.edges():
                session.run(
                    """
                    MATCH (a:Email {id: $src}), (b:Email {id: $tgt})
                    MERGE (a)-[:REPLY_TO]->(b)
                    """,
                    {"src": src, "tgt": tgt},
                )

            logger.info("Done exporting graph.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    logger.info("Loading and building graph from %s...", INPUT_FILE)
    messages = load_messages(INPUT_FILE)
    G = build_thread_graph(messages)

    exporter = Neo4jExporter(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        exporter.export_graph(G)
    finally:
        exporter.close()

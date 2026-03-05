import argparse
import logging
import os

from load_messages import load_messages
from graph_builder import build_thread_graph
from embedder import Embedder
from config import INPUT_FILE

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Transform email archives into a knowledge graph and vector store"
    )
    parser.add_argument(
        "-i",
        "--input",
        default=INPUT_FILE,
        help="Path to .mbox or .jsonl file (default: %(default)s)",
    )
    parser.add_argument(
        "-q",
        "--query",
        default=None,
        help="Run a semantic search query after building the index",
    )
    parser.add_argument(
        "-k",
        "--top-k",
        type=int,
        default=5,
        help="Number of results to return (default: %(default)s)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not os.path.exists(args.input):
        logger.error("Missing file: %s", args.input)
        return

    logger.info("Loading messages from %s", args.input)
    messages = load_messages(args.input)
    logger.info("Loaded %d messages", len(messages))

    logger.info("Building thread graph...")
    graph = build_thread_graph(messages)
    logger.info(
        "Graph has %d nodes and %d edges",
        graph.number_of_nodes(),
        graph.number_of_edges(),
    )

    logger.info("Embedding messages for RAG...")
    embedder = Embedder()
    embedder.embed_messages(messages)

    query = args.query or "budget deadline discussion"
    logger.info("Running search: %r", query)
    results = embedder.search(query, k=args.top_k)
    for r in results:
        print(f"- {r.get('subject', '(no subject)')} ({r.get('from', '?')})")
        body = r.get("cleaned_body", "")
        print(f"  {body[:120]}...\n")


if __name__ == "__main__":
    main()

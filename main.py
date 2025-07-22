from load_messages import load_messages
from graph_builder import build_thread_graph
from embedder import Embedder
import os

INPUT_FILE = "data/pst_output.jsonl"

def main():
    print(f"Looking for file: {INPUT_FILE}")
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Missing file: {INPUT_FILE}")
        return

    print(f"📥 Loading messages from {INPUT_FILE}")
    messages = load_messages(INPUT_FILE)
    print(f"✅ Loaded {len(messages)} messages")

    print("🧵 Building graph...")
    graph = build_thread_graph(messages)
    print(f"✅ Graph has {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")

    print("🔎 Embedding for RAG...")
    embedder = Embedder()
    embedder.embed_messages(messages)

    print("💬 Example RAG search:")
    results = embedder.search("budget deadline discussion")
    for r in results:
        print(f"- {r['subject']} ({r['from']})\n  {r['cleaned_body'][:120]}...\n")

if __name__ == "__main__":
    main()


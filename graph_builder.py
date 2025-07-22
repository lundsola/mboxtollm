from collections import defaultdict
import networkx as nx

def build_thread_graph(messages):
    G = nx.DiGraph()
    grouped = defaultdict(list)

    # Add nodes and group by conversation
    for msg in messages:
        msg_id = msg.get('id')
        if not msg_id:
            continue

        G.add_node(msg_id, **msg)
        conv_id = msg.get("conversation_id")
        if conv_id:
            grouped[conv_id].append(msg)

    # Create REPLY_TO-like edges within each conversation
    for thread_msgs in grouped.values():
        thread_msgs = [m for m in thread_msgs if m.get("date")]
        thread_msgs.sort(key=lambda m: m["date"])
        for i in range(1, len(thread_msgs)):
            parent = thread_msgs[i - 1]["id"]
            child = thread_msgs[i]["id"]
            G.add_edge(parent, child)

    return G


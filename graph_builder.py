import logging
from collections import defaultdict

import networkx as nx

logger = logging.getLogger(__name__)


def build_thread_graph(messages):
    G = nx.DiGraph()
    id_map = {}
    grouped = defaultdict(list)

    # Index messages by id and add nodes
    for msg in messages:
        msg_id = msg.get("id")
        if not msg_id:
            continue

        G.add_node(msg_id, **msg)
        id_map[msg_id] = msg

        conv_id = msg.get("conversation_id")
        if conv_id:
            grouped[conv_id].append(msg)

    # Create edges from in_reply_to / references when available
    reply_edges = 0
    for msg in messages:
        msg_id = msg.get("id")
        parent_id = msg.get("in_reply_to")
        if msg_id and parent_id and parent_id in id_map:
            G.add_edge(parent_id, msg_id)
            reply_edges += 1

    # Fall back to conversation_id-based chronological ordering
    # for messages without explicit reply headers
    for thread_msgs in grouped.values():
        dated = [m for m in thread_msgs if m.get("date")]
        dated.sort(key=lambda m: str(m["date"]))
        for i in range(1, len(dated)):
            parent = dated[i - 1]["id"]
            child = dated[i]["id"]
            if not G.has_edge(parent, child):
                G.add_edge(parent, child)

    logger.info(
        "Graph built: %d nodes, %d edges (%d from reply headers)",
        G.number_of_nodes(),
        G.number_of_edges(),
        reply_edges,
    )
    return G

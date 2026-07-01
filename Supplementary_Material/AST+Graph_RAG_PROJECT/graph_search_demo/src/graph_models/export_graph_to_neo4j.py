import json
from tqdm import tqdm
import networkx as nx
from neo4j import GraphDatabase

NEO4J_URI = "neo4j://localhost"  # or neo4j+s://xxxx.databases.neo4j.io
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "YOUR_NEO4J_PASSWORD"
NEO4J_DATABASE = "neo4j"

CREATE_NODE_QUERY = """
    UNWIND $nodes AS node
    MERGE (n:Node {id: node.id})
    SET n.name = node.name, 
        n.is_leaf = node.is_leaf,
        n.path = node.path, 
        n.type = node.type, 
        n.community_id = node.community_id,    
        n.description = node.description,
        n.comment = node.comment,
        n.report = node.report
    WITH n
    WHERE n.is_leaf = false
    MERGE (c:Community {id: n.community_id})
    MERGE (n)-[:BELONGS_TO]->(c)
"""

CREATE_EDGE_QUERY = """
    UNWIND $edges AS edge
    MATCH (a:Node {id: edge.source})
    MATCH (b:Node {id: edge.target})
    CALL apoc.create.relationship(a, edge.type, {}, b) YIELD rel
    RETURN rel
"""


def export_graph_to_neo4j(graph_path: str):
    print("Start export graph to neo4j......")
    G: nx.DiGraph = nx.node_link_graph(json.load(open(graph_path, "r")))
    node_list = list(G.nodes(data=True))
    edge_list = list(G.edges(data=True))

    driver = GraphDatabase.driver(
        NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
    )

    driver.execute_query("MATCH (n) DETACH DELETE n", database_=NEO4J_DATABASE)

    batch_size = 1000
    for i in tqdm(range(0, len(node_list), batch_size), desc="Saving nodes"):
        end_index = min(i + batch_size, len(node_list))
        node_batch = node_list[i:end_index]
        node_data = [{"id": _[0], **_[1]} for _ in node_batch]
        # print(f"Processing node {i} to {end_index} ......")
        driver.execute_query(
            CREATE_NODE_QUERY, {"nodes": node_data}, database_=NEO4J_DATABASE
        )

    for i in tqdm(range(0, len(edge_list), batch_size), desc="Saving edges"):
        end_index = min(i + batch_size, len(edge_list))
        edge_batch = edge_list[i:end_index]
        edge_data = [
            {"source": _[0], "target": _[1], **_[2]} for _ in edge_batch
        ]
        # print(f"Processing edge {i} to {end_index} ......")
        driver.execute_query(
            CREATE_EDGE_QUERY, {"edges": edge_data}, database_=NEO4J_DATABASE
        )

    print("Successfully export graph to neo4j !")

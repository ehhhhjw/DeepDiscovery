import threading
import networkx as nx
import json


class SingletonLoadGraph:
    _graph_map = {}
    _lock = {}  # 创建一个锁对象

    def get_code_graph(graph_path) -> nx.Graph:
        with open(graph_path, "r") as f:
            return nx.node_link_graph(json.load(f))

    def get_community(community_path) -> dict:
        with open(community_path, "r") as f:
            return json.load(f)

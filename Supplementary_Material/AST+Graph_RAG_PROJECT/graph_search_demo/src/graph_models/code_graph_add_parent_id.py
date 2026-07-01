def add_parent_id_to_node(data):
    nodes = data.get("nodes")
    parent_ids = {}
    for i in range(len(nodes)):
        node = nodes[i]
        if not node["is_leaf"]:
            parent_ids[node["name"]] = node["id"]

    for i in range(len(nodes)):
        node = nodes[i]
        name: str = node["name"]
        parent_name = ".".join(name.split(".")[:-1])
        node["parent_id"] = (
            parent_ids.get(parent_name, -1) if node["is_leaf"] else -1
        )
    return data

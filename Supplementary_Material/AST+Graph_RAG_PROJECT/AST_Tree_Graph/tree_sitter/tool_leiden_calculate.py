import igraph as ig
import leidenalg as la

# 创建一个示例图
g = ig.Graph(edges=[(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3), (6, 7), (7, 8), (8, 6), (0, 3), (3, 6)])

# 显示图信息
print(f"Number of vertices: {g.vcount()}")
print(f"Number of edges: {g.ecount()}")

# 使用Leiden算法进行社区检测
partition = la.find_partition(g, la.CPMVertexPartition, resolution_parameter=0.01)

# 输出结果
communities = partition.as_cover()
print("Detected communities:")
for idx, community in enumerate(communities):
    print(f"Community {idx}: {community}")

# 可视化图和社区
layout = g.layout("kamada_kawai")
ig.plot(partition, layout=layout, vertex_size=20, margin=20)
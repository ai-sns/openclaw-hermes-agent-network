def sort_nodes_by_connections(workflow):
    """
    按照连接关系对工作流中的节点进行排序。
    
    :param workflow: 包含节点和连接线的工作流数据。
    :return: 排序后的节点列表。
    """
    # 提取节点和连接线
    nodes = {node['id']: node for node in workflow['nodes']}
    lines = workflow['lines']

    # 查找开始节点和结束节点
    start_node = next(node for node in nodes.values() if node['type'] == 'start')
    end_node = next(node for node in nodes.values() if node['type'] == 'end')

    # 创建连接字典
    connections = {node['id']: [] for node in nodes.values()}
    for line in lines:
        connections[line['connector1Id']].append(line['connector2Id'])

    # 按顺序遍历节点
    sorted_nodes = []
    visited = set()
    current_node_id = start_node['id']

    # 使用 BFS 进行遍历
    def bfs(start_id):
        queue = [start_id]
        while queue:
            node_id = queue.pop(0)
            if node_id not in visited:
                visited.add(node_id)
                sorted_nodes.append(nodes[node_id])
                if node_id in connections:
                    queue.extend(connections[node_id])

    bfs(current_node_id)

    # 将结束节点添加到最后
    if end_node['id'] not in visited:
        sorted_nodes.append(end_node)

    return sorted_nodes

def get_next_nodes(workflow, node_id):
    """
    获取指定节点的所有后继节点。
    
    :param workflow: 包含节点和连接线的工作流数据。
    :param node_id: 指定节点的 ID。
    :return: 指定节点的所有后继节点列表。
    """
    # 提取所有节点和连接线
    nodes = {node['id']: node for node in workflow['nodes']}
    lines = workflow['lines']

    # 创建连接字典
    connections = {node['id']: [] for node in nodes.values()}
    for line in lines:
        connections[line['connector1Id']].append(line['connector2Id'])

    # 获取后继节点
    return [nodes[next_id] for next_id in connections.get(node_id, [])]

# 示例输入
workflow = {
    "workflow": {"id": "", "title": "", "description": "", "tags": ""},
    "nodes": [
        {"id": "node1", "x": 189, "y": 136, "title": "Node 1", "type": "start", "type_str": "开始", "description": "", "plugin": "", "connectors": [{"cx": 249, "cy": 126}, {"cx": 319, "cy": 196}, {"cx": 249, "cy": 266}, {"cx": 179, "cy": 196}]},
        {"id": "node2", "x": 941, "y": 138, "title": "Node 2", "type": "end", "type_str": "结束", "description": "", "plugin": "", "connectors": [{"cx": 1001, "cy": 128}, {"cx": 1071, "cy": 198}, {"cx": 1001, "cy": 268}, {"cx": 931, "cy": 198}]},
        {"id": "node3", "x": 420, "y": 138, "title": "Node 3", "type": "llm", "type_str": "大模型", "description": "", "plugin": "", "connectors": [{"cx": 480, "cy": 128}, {"cx": 550, "cy": 198}, {"cx": 480, "cy": 268}, {"cx": 410, "cy": 198}]},
        {"id": "node4", "x": 682, "y": 145, "title": "Node 4", "type": "code", "type_str": "代码插件", "description": "", "plugin": "", "connectors": [{"cx": 742, "cy": 135}, {"cx": 812, "cy": 205}, {"cx": 742, "cy": 275}, {"cx": 672, "cy": 205}]},
        {"id": "node5", "x": 670, "y": 395, "title": "Node 5", "type": "human", "type_str": "人类介入", "description": "", "plugin": "", "connectors": [{"cx": 730, "cy": 385}, {"cx": 800, "cy": 455}, {"cx": 730, "cy": 525}, {"cx": 660, "cy": 455}]}
    ],
    "lines": [
        {"connector1Id": "node1", "connector2Id": "node3", "connector1Index": 1, "connector2Index": 3},
        {"connector1Id": "node3", "connector2Id": "node4", "connector1Index": 1, "connector2Index": 3},
        {"connector1Id": "node4", "connector2Id": "node2", "connector1Index": 1, "connector2Index": 3},
        {"connector1Id": "node3", "connector2Id": "node5", "connector1Index": 3, "connector2Index": 3},
        {"connector1Id": "node5", "connector2Id": "node2", "connector1Index": 1, "connector2Index": 3}
    ]
}

# 对工作流进行节点排序
sorted_nodes = sort_nodes_by_connections(workflow)
for node in sorted_nodes:
    print(node['title'])

# 获取某个节点的后继节点示例
next_nodes = get_next_nodes(workflow, "node3")
print("Node 3's next nodes:")
for next_node in next_nodes:
    print(next_node['title'])
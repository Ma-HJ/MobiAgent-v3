import networkx as nx  # 添加网络图库支持DAG
import matplotlib.pyplot as plt  # 用于可视化DAG

class ExecutionGraph:
    """执行路径的有向无环图表示"""

    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_counter = 0  # 用于给节点编号

    def add_state_node(self, image_path, step_info=None):
        """添加状态节点（界面截图）"""
        node_id = f"state_{self.node_counter}"
        self.node_counter += 1
        self.graph.add_node(node_id,
                            image_path=image_path,
                            step_info=step_info)
        return node_id

    def add_action_edge(self, from_node, to_node, action_info):
        """添加动作边（从一个界面到另一个界面的动作）"""
        self.graph.add_edge(from_node, to_node, action=action_info)

    def save_graph(self, save_path):
        """保存图结构到文件"""
        graph_data = {
            'nodes': [],
            'edges': []
        }

        for node in self.graph.nodes(data=True):
            node_id, attrs = node
            graph_data['nodes'].append({
                'id': node_id,
                'image_path': attrs.get('image_path', ''),
                'step_info': attrs.get('step_info', {})
            })

        for edge in self.graph.edges(data=True):
            source, target, attrs = edge
            graph_data['edges'].append({
                'source': source,
                'target': target,
                'action': attrs.get('action', {})
            })

        graph_file = os.path.join(save_path, "execution_graph.json")
        with open(graph_file, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=4)

    def visualize_graph(self, save_path):
        """可视化DAG并保存图像"""
        pos = nx.spring_layout(self.graph)  # 使用spring布局
        plt.figure(figsize=(12, 8))

        # 绘制节点
        node_labels = {}
        for node in self.graph.nodes():
            node_labels[node] = node.split('_')[1]  # 只显示数字部分

        nx.draw_networkx_nodes(self.graph, pos, node_color='lightblue', node_size=500)
        nx.draw_networkx_labels(self.graph, pos, node_labels, font_size=8)
        nx.draw_networkx_edges(self.graph, pos, arrows=True, arrowsize=20)

        # 获取边标签（动作信息）
        edge_labels = {}
        for edge in self.graph.edges(data=True):
            source, target, attrs = edge
            action = attrs.get('action', {}).get('action', 'unknown')
            edge_labels[(source, target)] = action

        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels, font_size=6)

        plt.title("Execution Path DAG")
        plt.axis('off')
        dag_image_path = os.path.join(save_path, "dag_visualization.png")
        plt.savefig(dag_image_path, bbox_inches='tight')
        plt.close()

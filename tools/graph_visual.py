import base64
import json
import os
import networkx as nx
from pyvis.network import Network
import random


def write_nx_graph(graph: nx.Graph, file_name):
    print(f"Writing graph with {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    nx.write_graphml(graph, file_name)

def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def create_graph(graph_path):
    graph = nx.Graph()
    with open(graph_path, "r", encoding='utf-8') as f:
        content = f.read()
    data = json.loads(content)
    for node in data['nodes']:
        # 只添加特定的节点属性
        allowed_attributes = ['description']
        filtered_node_data = {k: v for k, v in node.items() if k in allowed_attributes}
        root_path = os.path.dirname(os.getcwd())
        image = os.path.join(root_path, node['image_path'][2:]).replace('\\', '/')
        base64_image = image_to_base64(image)
        graph.add_node(node['state_id'], shape='image', image=f"data:image/png;base64,{base64_image}", **filtered_node_data)
    for edge in data['edges']:
        allowed_attributes = ['thought', 'description', 'is_error_transition']
        filtered_edge_data = {k: v for k, v in edge.items() if k in allowed_attributes}
        graph.add_edge(edge['from_state'], edge['to_state'], **filtered_edge_data)
    output_dir = os.path.join(os.path.dirname(graph_path), "graph.graphml")

    write_nx_graph(graph, output_dir)
    return output_dir


def create_html(graph_path):
    graphml_path = create_graph(graph_path)
    # Load the GraphML file
    G = nx.read_graphml(graphml_path)

    # Create a Pyvis network
    net = Network(height="100vh", notebook=True)

    # Convert NetworkX graph to Pyvis network
    net.from_nx(G)

    # Add colors and title to nodes
    for node in net.nodes:
        node["color"] = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        if "description" in node:
            node["title"] = f"{node['description']}"

    # Add title to edges
    for edge in net.edges:
        if "description" in edge:
            edge["title"] = f"{edge['description']}\nerror: {edge['is_error_transition']}"

    # Save and display the network
    graph_dir = os.path.dirname(graph_path)
    net.show(os.path.join(graph_dir, "graph.html"))

path = os.path.join(os.getcwd(), "logs/20260310_141230/ClockTimerEntry/state_graph.json")
create_html(path)

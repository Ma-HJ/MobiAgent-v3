# tools/state_graph_manager.py
import json
import math
import os
import uuid
from typing import Dict, List, Tuple, Optional
from PIL import Image
import PIL
import numpy as np
import hashlib
import cv2


class StateNode:
    """表示界面状态的节点"""

    def __init__(self, image_path: str, xml_path: str, state_id: str = None):
        self.state_id = state_id or f"State_{uuid.uuid4().hex[:8]}"
        self.image_path = image_path
        self.xml_path = xml_path
        self.description = ''

    def calculate_features(self) -> str:
        """计算界面的相似性特征，用于状态匹配"""
        # 使用XML内容的哈希值作为主要特征
        if os.path.exists(self.xml_path):
            with open(self.xml_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
                # 返回XML内容的哈希值作为特征
                return hashlib.md5(xml_content.encode()).hexdigest()
        return ""

    def to_dict(self):
        return {
            'state_id': self.state_id,
            'image_path': self.image_path,
            'xml_path': self.xml_path,
            'description': self.description
        }


class TransitionEdge:
    """表示界面转换的边"""

    def __init__(self, from_state: str, to_state: str, action: Dict, is_error_transition: bool = False, edge_id: str = None):
        self.edge_id = edge_id or f"Edge_{uuid.uuid4().hex[:8]}"
        self.from_state = from_state  # 源状态ID
        self.to_state = to_state  # 目标状态ID
        self.action = action  # 执行的动作
        self.is_error_transition = is_error_transition  # 是否是错误转换

    def to_dict(self):
        return {
            'edge_id': self.edge_id,
            'from_state': self.from_state,
            'to_state': self.to_state,
            "thought": self.action['thought'],
            "description": self.action['description'],
            'is_error_transition': self.is_error_transition
        }


class StateGraphManager:
    """状态图管理器"""
    root_node: StateNode = None
    cur_node: StateNode = None

    def __init__(self, graph_path: str = None):
        self.graph_path = graph_path
        self.nodes: Dict[str, StateNode] = {}
        self.edges: Dict[str, list[TransitionEdge]] = {}
        self.load_graph()

    def load_graph(self):
        """从文件加载状态图"""
        if os.path.exists(self.graph_path):
            try:
                with open(self.graph_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 重建节点
                for node_data in data.get('nodes', []):
                    node = StateNode(
                        image_path=node_data['image_path'],
                        xml_path=node_data['xml_path'],
                        state_id=node_data['state_id']
                    )
                    node.timestamp = node_data.get('timestamp')
                    self.nodes[node.state_id] = node

                # 重建边
                for edge_data in data.get('edges', []):
                    edge = TransitionEdge(
                        from_state=edge_data['from_state'],
                        to_state=edge_data['to_state'],
                        action=edge_data['action'],
                        edge_id=edge_data['edge_id']
                    )
                    edge.success_count = edge_data.get('success_count', 1)
                    edge.error_count = edge_data.get('error_count', 0)
                    edge.is_error_transition = edge_data.get('is_error_transition', False)
                    self.edges[edge_data['from_state']].append(edge)

            except Exception as e:
                print(f"加载状态图失败: {e}")
                # 初始化为空图
                self.nodes = {}
                self.edges = {}
        else:

            # 初始化为空图
            self.nodes = {}
            self.edges = {}

    def save_graph(self):
        """保存状态图到文件"""
        data = {
            'nodes': [node.to_dict() for node in self.nodes.values()],
            'edges': [edge.to_dict() for from_id, edge_list in self.edges.items() for edge in edge_list]
        }

        with open(self.graph_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def find_similar_state(self, file_path: str, threshold: float = 0.85, method: str = 'image') -> Optional[str]:
        """查找相似的状态节点"""
        if not os.path.exists(file_path):
            return None

        # 计算待匹配XML的特征
        # with open(xml_path, 'r', encoding='utf-8') as f:
        #     target_xml_content = f.read()
        img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
        img_array: np.ndarray = np.array(img)

        # 先与当前节点作比较
        # similarity = self._calculate_xml_similarity(target_xml_content, self.cur_node.xml_path)
        similarity = self._calculate_image_similarity(img_array, self.cur_node.image_path)

        if similarity >= threshold:
            return self.cur_node.state_id

        # 在现有节点中查找相似状态
        for state_id, node in self.nodes.items():
            # similarity = self._calculate_xml_similarity(target_xml_content, node.xml_path)
            similarity = self._calculate_image_similarity(img_array, node.image_path)
            if similarity >= threshold:
                return state_id

        return None

    def _calculate_xml_similarity(self, xml_content, candidate_xml_path) -> float:
        """计算两个XML文件的相似度"""
        with open(candidate_xml_path, 'r', encoding='utf-8') as f:
            candidate_xml_content = f.read()
        score = 0.0

        return score

    def _calculate_image_similarity(self, img1_array, img_path2):
        try:
            img2 = cv2.imread(img_path2, cv2.IMREAD_GRAYSCALE)
            # img2 = PIL.Image.open(img_path2)
        except IOError:
            print("Error in opening one of the images.")
            return

        # Convert images to numpy arrays
        img2_array = np.array(img2)

        # Check if dimensions are the same
        # if img1_array.shape != img2_array.shape:
        #     print("Images have different dimensions.")
        #     return False, False

        # Calculate the number of equal pixels
        equal_pixels = np.sum(img1_array == img2_array)

        # Total number of pixels
        total_pixels = img1_array.size

        # Calculate the ratio of equal pixels
        similarity_ratio = equal_pixels / total_pixels
        return similarity_ratio

    def add_state_node(self, node: StateNode) -> str:
        """添加新的状态节点"""
        self.nodes[node.state_id] = node
        return node.state_id

    def add_edge(self, edge: TransitionEdge) -> str:
        """添加状态节点"""
        self.edges[edge.from_state].append(edge)
        return edge.edge_id

    def _calculate_dist(self, coordinate1: list, coordinate2: list):
        distance = math.sqrt((coordinate1[0] - coordinate2[0]) ** 2 + (coordinate1[1] - coordinate2[1]) ** 2)
        if distance < 140:
            return True
        return False

    def add_transition_edge(self, from_state: str, to_state: str, action: Dict, is_error: bool = False) -> str:
        """添加状态转换边"""
        # 检查是否已存在相同的转换
        same_transitions = [edge for edge in self.edges[from_state] if edge.to_state == to_state]
        for edge in same_transitions:
            # 动作意图一样或者点击距离太近
            if edge.action['description'] == action['description']:
                edge.is_error_transition = True
                return edge.edge_id
            if edge.action['action'] == action['action'] and action['action'] in ['click', 'long_press']:
                if self._calculate_dist(edge.action['coordinate'], action['coordinate']):
                    return edge.edge_id

        # 创建新边
        edge = TransitionEdge(from_state, to_state, action, is_error)

        self.edges[from_state].append(edge)
        return edge.edge_id

    # def get_available_transitions(self, state_id: str) -> List[TransitionEdge]:
    #     """获取指定状态的所有可用转换"""
    #     return [edge for edge in self.edges if edge.from_state == state_id]

    def get_error_transitions(self, state_id: str) -> List:
        """获取指定状态的错误转换"""
        if state_id not in self.edges:
            return []
        return [edge.action for edge in self.edges[state_id] if edge.is_error_transition]

    def get_state_graph(self) -> Dict:
        """获取完整的状态图，包括节点描述和边的action信息"""
        graph = {
            'nodes': [],
            'edges': []
        }

        # 添加所有节点信息
        for state_id, node in self.nodes.items():
            graph['nodes'].append({
                'state_id': node.state_id,
                'description': node.description
            })

        # 添加所有边信息
        for from_state, edge_list in self.edges.items():
            for edge in edge_list:
                graph['edges'].append({
                    'from_state': edge.from_state,
                    'to_state': edge.to_state,
                    'action': edge.action["description"]
                })

        return graph
    # def mark_transition_as_error(self, from_state: str, action: Dict):
    #     """标记特定转换为错误"""
    #     for edge in self.edges:
    #         if (edge.from_state == from_state and
    #                 json.dumps(edge.action, sort_keys=True) == json.dumps(action, sort_keys=True)):
    #             edge.is_error_transition = True
    #             edge.error_count += 1
    #             return
    #
    # def get_preferred_next_action(self, current_state_id: str) -> Optional[Dict]:
    #     """根据历史数据推荐下一个动作"""
    #     available_transitions = self.get_available_transitions(current_state_id)
    #
    #     # 过滤掉错误转换
    #     valid_transitions = [t for t in available_transitions if not t.is_error_transition]
    #
    #     if not valid_transitions:
    #         return None
    #
    #     # 选择成功率最高的转换
    #     best_transition = max(valid_transitions, key=lambda x: x.success_count / (x.success_count + x.error_count) if (
    #                                                                                                                               x.success_count + x.error_count) > 0 else 0)
    #     return best_transition.action

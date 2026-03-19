
import os
import json
import uuid
from typing import Dict, List, Tuple, Optional
from PIL import Image
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import cv2


class UIStateManager:
    """
    管理界面状态，包括界面特征、XML内容、截图等
    支持界面匹配和错误历史追踪
    """

    def __init__(self, save_path: str):
        self.save_path = save_path
        self.ui_states_path = os.path.join(save_path, "ui_states")
        self.rounds_path = os.path.join(save_path, "rounds")
        self.current_round = 0

        os.makedirs(self.ui_states_path, exist_ok=True)
        os.makedirs(self.rounds_path, exist_ok=True)

        # 存储所有轮次的界面状态
        self.all_rounds_ui_states: Dict[int, List[Dict]] = {}
        self.current_round_ui_states: List[Dict] = []
        self.error_history: List[Dict] = []  # 存储错误历史

    def save_ui_state(self,
                     step: int,
                     image_path: str,
                     xml_path: str,
                     xml_content: str,
                     action_taken: Optional[Dict] = None,
                     outcome: Optional[str] = None,
                     error_description: Optional[str] = None) -> str:
        """
        保存当前界面状态
        """
        # 计算图像特征
        image_features = self._extract_image_features(image_path)

        # 提取XML文本特征
        xml_text_features = self._extract_xml_text_features(xml_content)

        ui_state_id = str(uuid.uuid4())

        ui_state = {
            "id": ui_state_id,
            "step": step,
            "image_path": image_path,
            "xml_path": xml_path,
            "xml_content": xml_content,
            "image_features": image_features.tolist() if image_features is not None else [],
            "xml_text_features": xml_text_features,
            "action_taken": action_taken,
            "outcome": outcome,
            "error_description": error_description,
            "timestamp": str(uuid.uuid4())  # 用于排序
        }

        # 保存到当前轮次
        self.current_round_ui_states.append(ui_state)

        # 保存状态到文件
        state_file_path = os.path.join(self.ui_states_path, f"state_{ui_state_id}.json")
        with open(state_file_path, 'w', encoding='utf-8') as f:
            # 将numpy数组转换为列表以便JSON序列化
            serializable_state = ui_state.copy()
            serializable_state['image_features'] = ui_state['image_features']
            json.dump(serializable_state, f, ensure_ascii=False, indent=2)

        return ui_state_id

    def match_current_interface(self, current_xml_content: str, current_image_path: str) -> Optional[Tuple[Dict, float]]:
        """
        匹配当前界面到历史界面状态
        返回最相似的状态和相似度分数
        """
        if not self.all_rounds_ui_states:
            return None

        # 提取当前界面的特征
        current_image_features = self._extract_image_features(current_image_path)
        current_xml_text_features = self._extract_xml_text_features(current_xml_content)

        best_match = None
        best_similarity = 0.0

        # 在所有历史界面状态中查找最佳匹配
        for round_num, states in self.all_rounds_ui_states.items():
            for state in states:
                # 计算综合相似度（图像相似度 + XML文本相似度）
                image_sim = 0.0
                if current_image_features is not None and state['image_features']:
                    img_feat = np.array(state['image_features'])
                    if img_feat.size > 0:
                        image_sim = self._calculate_image_similarity(
                            current_image_features, img_feat
                        )

                xml_sim = self._calculate_text_similarity(
                    current_xml_text_features, state['xml_text_features']
                )

                # 综合相似度（可调整权重）
                combined_sim = 0.6 * xml_sim + 0.4 * image_sim

                if combined_sim > best_similarity:
                    best_similarity = combined_sim
                    best_match = (state, combined_sim)

        return best_match if best_similarity > 0.5 else None  # 设定阈值

    def _extract_image_features(self, image_path: str) -> Optional[np.ndarray]:
        """
        提取图像特征（使用ORB算法或其他简单方法）
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                return None

            # 使用ORB特征提取（轻量级）
            orb = cv2.ORB_create(nfeatures=50)  # 减少特征数量以提高效率
            keypoints, descriptors = orb.detectAndCompute(img, None)

            if descriptors is not None:
                # 限制特征数量
                if descriptors.shape[0] > 50:
                    descriptors = descriptors[:50]
                return descriptors.flatten()
            else:
                return np.array([])
        except Exception as e:
            print(f"Error extracting image features: {e}")
            return None

    def _extract_xml_text_features(self, xml_content: str) -> str:
        """
        从XML中提取文本特征（提取UI元素的文本内容）
        """
        import re
        # 提取所有文本内容，如text、content-desc等属性
        texts = re.findall(r'(text|content-desc)="([^"]*)"', xml_content)
        combined_text = " ".join([text[1] for text in texts if text[1].strip()])
        return combined_text

    def _calculate_image_similarity(self, feat1: np.ndarray, feat2: np.ndarray) -> float:
        """
        计算两个图像特征之间的相似度
        """
        try:
            # 如果特征向量长度不同，进行填充或截断
            min_len = min(len(feat1), len(feat2))
            feat1_trunc = feat1[:min_len]
            feat2_trunc = feat2[:min_len]

            # 计算余弦相似度
            dot_product = np.dot(feat1_trunc, feat2_trunc)
            norm1 = np.linalg.norm(feat1_trunc)
            norm2 = np.linalg.norm(feat2_trunc)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            return max(0.0, similarity)  # 确保非负
        except:
            return 0.0

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本之间的相似度
        """
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0

        try:
            # 使用TF-IDF和余弦相似度
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform([text1, text2])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)
        except:
            # 如果TF-IDF失败，使用简单的字符重叠
            set1, set2 = set(text1), set(text2)
            intersection = set1.intersection(set2)
            union = set1.union(set2)
            return len(intersection) / len(union) if union else 0.0

    def add_error_history(self, ui_state_id: str, error_description: str, action: Dict):
        """
        添加错误历史记录
        """
        error_record = {
            "ui_state_id": ui_state_id,
            "error_description": error_description,
            "action": action,
            "timestamp": str(uuid.uuid4())
        }
        self.error_history.append(error_record)

    def get_error_avoidance_info(self, matched_state: Dict) -> str:
        """
        获取基于匹配状态的错误避免信息
        """
        if not self.error_history:
            return ""

        avoidance_info = []

        # 查找与匹配状态相关的错误历史
        for error in self.error_history:
            if error['ui_state_id'] == matched_state['id']:
                avoidance_info.append(f"Avoid action '{error['action']}' which previously caused: {error['error_description']}")

        return "\n".join(avoidance_info) if avoidance_info else ""

    def start_new_round(self):
        """
        开始新的一轮执行
        """
        # 保存当前轮次的状态
        if self.current_round_ui_states:
            self.all_rounds_ui_states[self.current_round] = self.current_round_ui_states.copy()

            # 保存到文件
            round_file_path = os.path.join(self.rounds_path, f"round_{self.current_round}.json")
            with open(round_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.current_round_ui_states, f, ensure_ascii=False, indent=2)

        # 开始新轮次
        self.current_round += 1
        self.current_round_ui_states = []

    def get_first_round_states(self) -> List[Dict]:
        """
        获取第一轮的界面状态
        """
        return self.all_rounds_ui_states.get(0, [])

    def load_all_rounds(self):
        """
        加载所有已保存的轮次
        """
        for filename in os.listdir(self.rounds_path):
            if filename.startswith("round_") and filename.endswith(".json"):
                round_num = int(filename.replace("round_", "").replace(".json", ""))
                filepath = os.path.join(self.rounds_path, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.all_rounds_ui_states[round_num] = json.load(f)

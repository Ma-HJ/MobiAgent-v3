import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple


class ActionValidator:
    """验证动作的有效性基于 XML 元素属性"""
    
    def __init__(self, xml_path: str):
        """
        初始化验证器
        
        Args:
            xml_path: XML 文件路径
        """
        try:
            self.tree = ET.parse(xml_path)
            self.root = self.tree.getroot()
            self.all_nodes = []
            # 从 hierarchy 的子节点开始收集 (因为根节点是 hierarchy，不是 node)
            for child in self.root:
                self._collect_all_nodes(child)
        except Exception as e:
            print(f"Error loading XML: {e}")
            self.all_nodes = []
    
    def _collect_all_nodes(self, node, parent_bounds=None):
        """递归收集所有节点及其属性"""
        if len(self.all_nodes) == 0:
            print(f"Starting collection from root tag: {node.tag}")
        if node.tag == 'node':
            bounds = node.attrib.get('bounds', '')
            
            # 继承父节点的可见性属性 (如果子节点未指定)
            node_info = {
                'bounds': bounds,
                'clickable': node.attrib.get('clickable', 'false'),
                'enabled': node.attrib.get('enabled', 'true'),
                'focusable': node.attrib.get('focusable', 'false'),
                'scrollable': node.attrib.get('scrollable', 'false'),
                'long-clickable': node.attrib.get('long-clickable', 'false'),
                'checkable': node.attrib.get('checkable', 'false'),
                'text': node.attrib.get('text', ''),
                'content-desc': node.attrib.get('content-desc', ''),
                'resource-id': node.attrib.get('resource-id', ''),
                'class': node.attrib.get('class', ''),
                'selected': node.attrib.get('selected', 'false'),
                'checked': node.attrib.get('checked', 'false'),
            }
            
            self.all_nodes.append(node_info)
            
            # 递归处理子节点
            for child in node:
                self._collect_all_nodes(child, bounds)
    
    def _parse_bounds(self, bounds_str: str) -> Tuple[int, int, int, int]:
        """解析 bounds 字符串为坐标"""
        pattern = r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]'
        match = re.search(pattern, bounds_str)
        if match:
            return (int(match.group(1)), int(match.group(2)), 
                   int(match.group(3)), int(match.group(4)))
        return (0, 0, 0, 0)
    
    def _point_in_bounds(self, x: int, y: int, bounds_str: str) -> bool:
        """检查点是否在边界内"""
        x1, y1, x2, y2 = self._parse_bounds(bounds_str)
        return x1 <= x <= x2 and y1 <= y <= y2
    
    def _find_element_at_point(self, x: int, y: int) -> Optional[Dict]:
        """
        查找指定坐标处的 UI 元素
        
        Returns:
            匹配的元素信息字典，如果没有找到则返回 None
        """
        matched_elements = []
        
        # 找到所有包含该点的元素
        for node in self.all_nodes:
            if self._point_in_bounds(x, y, node['bounds']):
                matched_elements.append(node)
        
        if not matched_elements:
            return None
        
        # 返回最小的那个元素 (最具体的子元素)
        smallest = None
        min_area = float('inf')
        
        for elem in matched_elements:
            x1, y1, x2, y2 = self._parse_bounds(elem['bounds'])
            area = (x2 - x1) * (y2 - y1)
            if area < min_area:
                min_area = area
                smallest = elem
        
        return smallest
    
    def validate_click(self, x: int, y: int) -> Tuple[bool, str]:
        """
        验证点击动作的有效性
        
        Args:
            x: 点击的 x 坐标
            y: 点击的 y 坐标
            
        Returns:
            (是否有效，原因说明)
        """
        element = self._find_element_at_point(x, y)
        
        if element is None:
            return False, f"坐标 ({x}, {y}) 处未找到任何 UI 元素"
        
        # 检查是否启用
        if element['enabled'] != 'true':
            return False, f"元素已禁用 (enabled=false): {element.get('text', '') or element.get('content-desc', '')}"
        
        # 检查是否可点击
        if element['clickable'] != 'true':
            # 有些元素虽然 clickable=false，但可能是容器，需要检查子元素
            has_clickable_child = False
            for node in self.all_nodes:
                if (node['clickable'] == 'true' and 
                    node['enabled'] == 'true' and
                    self._point_in_bounds(x, y, node['bounds'])
                        and node != element):
                    has_clickable_child = True
                    break
            
            if not has_clickable_child:
                return False, f"元素不可点击 (clickable=false): {element.get('text', '') or element.get('content-desc', '')}"
        
        return True, f"元素可点击：{element.get('text', '') or element.get('content-desc', '') or element.get('class', '')}"
    
    def validate_long_press(self, x: int, y: int) -> Tuple[bool, str]:
        """验证长按动作的有效性"""
        element = self._find_element_at_point(x, y)
        
        if element is None:
            return False, f"坐标 ({x}, {y}) 处未找到任何 UI 元素"
        
        if element['enabled'] != 'true':
            return False, f"元素已禁用"
        
        if element['long-clickable'] != 'true' and element['clickable'] != 'true':
            return False, f"元素不支持长按 (long-clickable=false 且 clickable=false)"
        
        return True, f"元素支持长按"
    
    def validate_swipe(self, x1: int, y1: int, x2: int, y2: int) -> Tuple[bool, str]:
        """验证滑动动作的有效性"""
        start_element = self._find_element_at_point(x1, y1)
        
        if start_element is None:
            return False, f"坐标 ({x1}, {y1}) 起始处未找到任何 UI 元素"
        
        # 检查是否是可滚动元素
        if start_element['scrollable'] != 'true':
            # 虽然不是 scrollable，但如果是 clickable 的也可以滑动 (比如列表项)
            if start_element['clickable'] != 'true':
                return False, f"元素不可滚动 (scrollable=false): {start_element.get('text', '')}"
        
        return True, f"元素可滑动：{start_element.get('content-desc', '') or start_element.get('class', '')}"
    
    def validate_action(self, action_object: Dict) -> Tuple[bool, str]:
        """
        Returns:(是否有效，原因说明)
        """
        action_type = action_object.get('action', '')
        
        if action_type == 'click':
            coord = action_object.get('coordinate', [])
            if len(coord) != 2:
                return False, "点击动作缺少坐标参数"
            return self.validate_click(coord[0], coord[1])
        
        elif action_type == 'long_press':
            coord = action_object.get('coordinate', [])
            if len(coord) != 2:
                return False, "长按动作缺少坐标参数"
            return self.validate_long_press(coord[0], coord[1])
        
        elif action_type == 'swipe':
            coord1 = action_object.get('coordinate', [])
            coord2 = action_object.get('coordinate2', [])
            if len(coord1) != 2 or len(coord2) != 2:
                return False, "滑动动作缺少坐标参数"
            return self.validate_swipe(coord1[0], coord1[1], coord2[0], coord2[1])
        
        elif action_type == 'type':
            # type 动作不需要坐标验证
            return True, "输入动作无需验证"
        
        elif action_type == 'system_button':
            # 系统按钮动作无需验证
            return True, "系统按钮动作无需验证"
        
        elif action_type == 'open_app':
            # 打开应用动作无需验证
            return True, "打开应用动作无需验证"
        
        else:
            return False, f"未知的动作类型：{action_type}"

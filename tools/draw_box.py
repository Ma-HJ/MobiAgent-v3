import cv2
import re

def parse_xml(xml_path):
    """
    解析XML压缩字符串，获取元素边界信息
    Returns:
        元素边界信息以及元素的属性
    """
    xml_compressed_path = xml_path[:-4] + '_comp.txt'
    with open(xml_compressed_path, 'r', encoding='utf-8') as f:
        xml_string = f.read()

    lines = xml_string.split('\n')

    elements = []
    attrs = []
    status = []
    desc = ""
    for line in lines:
        if 'bounds' in line:
            bounds_match = re.findall(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', line)
            if bounds_match and (len(status) > 0 or len(attrs) > 0):
                # x1, y1, x2, y2 = map(int, bounds_match[0])
                # coordinates = [int(c) for c in bounds_match[0]]
                elements.append({'attributes': attrs, "status": status, 'bounds': map(int, bounds_match[0]), "description": desc})
        elif ';' in line:
            # 对于checked和selected在status中， focusable似乎没啥作用
            items = line.split(';')
            attrs = items[1].strip().split(' ') if items[1].strip() != '' else []
            if 'focusable' in attrs:
                attrs.remove('focusable')
            status = items[2].strip().split(' ') if items[2].strip() != '' else []
            desc = items[-1][:-1].strip()

    return elements

def get_attribute_colors():
    # todo：颜色应该区分优先级
    colors = {
        "check": (0, 0, 255),      # 红色
        "click": (255, 0, 0),      # 蓝色
        "scroll": (128, 0, 128),   # 紫色
        "long-click": (255, 0, 255), # 黄色
        "focusable": (255, 255, 0),  # 青色
        "selected": (0, 255, 0),  # 绿色
        "checked": (128, 128, 0),   # 橄榄色
        "hybrid": (0, 165, 255)  #橙色
    }
    return colors

def get_colors_desc():
    colors = {
        "check": "红色",
        "click": "蓝色",
        "scroll": "紫色",
        "long-click": "黄色",
        "focusable": "青色",
        "selected": "绿色",
        "checked": "橄榄色",
        "hybrid": "橙色"
    }
    return colors

def draw_element_boxes(image_path, xml_compressed_path):
    """
    根据XML压缩字符串在图片上绘制元素框
    """
    # 读取图片
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"无法加载图片: {image_path}")

    # 解析XML获取元素信息
    elements = parse_xml(xml_compressed_path)

    # 获取属性颜色映射
    attr_colors = get_attribute_colors()

    # 为每个元素绘制边框
    for element in elements:
        x1, y1, x2, y2 = element['bounds']
        # 对于无用的元素不进行绘制
        if x2-x1 > 1000 and y2-y1 > 2000:
            continue
        # # 计算多种属性的混合颜色
        # mixed_color = np.array([0, 0, 0], dtype=np.float32)
        # active_attrs = []
        #
        # for attr, value in element['attributes']:
        #     if value == "true":
        #         active_attrs.append(attr)
        #         color = np.array(attr_colors.get(attr, (128, 128, 128)))
        #         mixed_color += color
        #
        # # 如果没有激活的特殊属性，则使用默认颜色（白色）
        # if len(active_attrs) == 0:
        #     box_color = (255, 255, 255)  # 白色
        # else:
        #     # 如果有多个属性，则计算平均颜色或选择第一个属性的颜色作为主色调
        #     if len(active_attrs) == 1:
        #         box_color = tuple(map(int, attr_colors[active_attrs[0]]))
        #     else:
        #         # 多个属性时使用加权平均或其他策略
        #         box_color = tuple(map(int, mixed_color / len(active_attrs)))

        # 此处以优先级的顺序标注
        if 'selected' in element['status'] and 'checked' in element['status']:
            box_color = attr_colors['hybrid']
        elif 'selected' in element['status']:
            box_color = attr_colors['selected']
        elif 'checked' in element['status']:
            box_color = attr_colors['checked']
        elif 'click' in element['attributes']:
            box_color = attr_colors['click']
        elif 'long-click' in element['attributes']:
            box_color = attr_colors['long-click']
        elif 'check' in element['attributes']:
            box_color = attr_colors['check']
        elif 'scroll' in element['attributes']:
            box_color = attr_colors['scroll']
        else:
            box_color = attr_colors['focusable']
        # 绘制矩形框
        cv2.rectangle(image, (x1, y1), (x2, y2), box_color, 2)

    success = cv2.imwrite(image_path[:-4] + '_boxes.png', image)
    if not success:
        raise Exception(f"无法保存图片")

# def save_image_with_boxes(image_path, xml_compressed_path, output_path):
#     """
#     将带有元素框的图片保存到指定路径
#     """
#     result_image = draw_element_boxes(image_path, xml_compressed_path)
#     success = cv2.imwrite(output_path, result_image)
#     if not success:
#         raise Exception(f"无法保存图片到: {output_path}")
#
#     print(f"已成功生成带元素框的图片: {output_path}")

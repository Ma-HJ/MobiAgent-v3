import PIL
import numpy as np
import xml.etree.ElementTree as ET
from tools.bm25 import BM25


def parse_xml_to_anytree(xml_code):
    root = ET.fromstring(xml_code)

    def build_anytree(node, element, child_index, seen_elements, counter):
        element_type = element.tag
        # print(element_type)
        # Generate a unique key for the element based on its attributes
        element_key = (
            element_type,
            element.get('resource-id', ''),
            #  content-desc， text兼容问题
            element.get('content-desc', ''),
            element.get('text', ''),
            element.get('clickable', ''),
            element.get('scrollable', ''),
            element.get('package', ''),  ##
            element.get('class', ''),
            element.get('displayed', ''),
            element.get('bounds', ''),
        )
        seen_elements.add(element_key)

        # 检查是否有儿子节点
        is_leaf = not bool(list(element))

        # 检查 text 和 content-desc 是否至少有一个为真
        has_text = bool(element.get('text'))
        has_content_desc = bool(element.get('content-desc'))

        visible = has_text or has_content_desc or 'button' in element_type.lower() or 'edittext' in element.tag.lower()

        leaf_id = counter[0]  # 使用计数器作为 leaf_id
        counter[0] += 1  # 递增计数器

        anytree_node = Node(element_type, parent=node, type=element_type, visible=visible, leaf_id=leaf_id,
                            resource_id=element.get('resource-id'), content_desc=element.get('content-desc'),
                            text=element.get('text'), clickable=element.get('clickable'), is_leaf=is_leaf,
                            scrollable=element.get('scrollable'), package=element.get('package'),
                            class_label=element.get('class'), displayed=element.get('displayed'),
                            bounds=element.get('bounds'))

        for idx, child in enumerate(element):
            # print(idx)
            build_anytree(anytree_node, child, idx, seen_elements, counter)

    is_root_leaf = not bool(list(root))

    anytree_root = Node(root.tag, type=root.tag, visible=True, leaf_id=0,  # 初始计数器为 0
                        resource_id=root.get('resource-id'), content_desc=root.get('content-desc'),
                        text=root.get('text'), clickable=root.get('clickable'),
                        is_leaf=is_root_leaf, scrollable=root.get('scrollable'), package=root.get('package'),
                        class_label=root.get('class'), displayed=root.get('displayed'), bounds=root.get('bounds'))

    seen_elements = set()
    counter = [1]  # 使用列表来存储计数器的值，以便在递归中共享

    for idx, child in enumerate(root):
        # print("out",idx)
        build_anytree(anytree_root, child, idx, seen_elements, counter)

    return anytree_root


def compare_images(img_path1, img_path2, threshold):
    """
    Compare two images and determine if they are the same based on pixel values.

    :param img_path1: Path to the first image.
    :param img_path2: Path to the second image.
    :param threshold: The threshold for considering the images as the different.

    :return: True if the images are the same based on the given threshold, False otherwise.
    """
    # Open the images
    try:
        img1 = PIL.Image.open(img_path1)
        img2 = PIL.Image.open(img_path2)
    except IOError:
        print("Error in opening one of the images.")
        return False, False

    # Convert images to numpy arrays
    # print(img_path1)
    img1_array = np.array(img1)
    # print(img_path2)
    img2_array = np.array(img2)

    # Check if dimensions are the same
    if img1_array.shape != img2_array.shape:
        print("Images have different dimensions.")
        return False, False

    # Calculate the number of equal pixels
    equal_pixels = np.sum(img1_array == img2_array)

    # Total number of pixels
    total_pixels = img1_array.size

    # Calculate the ratio of equal pixels
    similarity_ratio = equal_pixels / total_pixels
    dif_ratio = 1 - similarity_ratio
    print("dif_ratio: ", dif_ratio)
    return dif_ratio < threshold, dif_ratio


def any_tree_to_html(node, layer, clickable_label):
    """Turns an AnyTree representation of view hierarchy into HTML.
    Args:
    node: an AnyTree node.
    layer: which layer is the node in.

    Returns:
    results: output HTML.
    """
    results = ''
    if 'ImageView' in node.type:
        node_type = 'img'
    elif 'IconView' in node.type:
        node_type = 'img'
    elif 'Button' in node.type:
        node_type = 'button'
    elif 'Image' in node.type:
        node_type = 'img'
    elif 'MenuItemView' in node.type:
        node_type = 'button'
    elif 'EditText' in node.type:
        node_type = 'input'
    elif 'TextView' in node.type:
        node_type = 'p'
    else:
        node_type = 'div'

    if node.clickable == "true":
        clickable_label = "true"
    elif clickable_label == "true":
        node.clickable = "true"
    if node.text:
        node.text = node.text.replace('\n', '')
    if node.content_desc:
        node.content_desc = node.content_desc.replace('\n', '')

    #  or node.class_label == 'android.widget.EditText'
    if node.is_leaf and node.visible:
        html_close_tag = node_type
        if node.scrollable == "true":
            html_close_tag = node_type
            results = '<{}{}{}{}{}{}{}{}> {} </{}>\n'.format(
                node_type,
                ' id="{}"'.format(node.resource_id)
                if node.resource_id
                else '',
                ' package="{}"'.format(node.package)
                if node.package
                else '',

                ' class="{}"'.format(''.join(node.class_label))
                if node.class_label
                else '',
                ' description="{}"'.format(node.content_desc) if node.content_desc else '',
                ' clickable="{}"'.format(node.clickable) if node.clickable else '',
                ' scrollable="{}"'.format(node.scrollable) if node.scrollable else '',
                ' bounds="{}"'.format(node.bounds) if node.bounds else '',
                '{}'.format(node.text) if node.text else '',
                html_close_tag,
            )
        else:
            results = '<{}{}{}{}{}{}{}> {} </{}>\n'.format(
                node_type,
                ' id="{}"'.format(node.resource_id)
                if node.resource_id
                else '',
                ' package="{}"'.format(node.package)
                if node.package
                else '',

                ' class="{}"'.format(''.join(node.class_label))
                if node.class_label
                else '',

                ' description="{}"'.format(node.content_desc) if node.content_desc else '',
                ' clickable="{}"'.format(node.clickable) if node.clickable else '',
                ' bounds="{}"'.format(node.bounds) if node.bounds else '',
                '{}'.format(node.text) if node.text else '',
                html_close_tag,
            )

    else:
        if node.scrollable == "true":
            html_close_tag = node_type
            results = '<{}{}{}{}{}{}{}> {} </{}>\n'.format(
                node_type,
                ' id="{}"'.format(node.resource_id)
                if node.resource_id
                else '',

                ' class="{}"'.format(''.join(node.class_label))
                if node.class_label
                else '',

                ' descript  ion="{}"'.format(node.content_desc) if node.content_desc else '',
                ' clickable="{}"'.format(node.clickable) if node.clickable else '',
                ' scrollable="{}"'.format(node.scrollable) if node.scrollable else '',
                ' bounds="{}"'.format(node.bounds) if node.bounds else '',

                '{}'.format(node.text) if node.text else '',
                html_close_tag,
            )
        for child in node.children:
            results += any_tree_to_html(child, layer + 1, clickable_label)

    return results


def compare_actions(xml1, xml2, difference_limit):
    anytree_root_1 = parse_xml_to_anytree(xml1)
    html_1 = any_tree_to_html(anytree_root_1, 0, None)
    anytree_root_2 = parse_xml_to_anytree(xml2)
    html_2 = any_tree_to_html(anytree_root_2, 0, None)
    elements1 = set(html_1.strip().split("\n"))
    elements2 = set(html_2.strip().split("\n"))
    intersection = elements1.intersection(elements2)
    union = elements1.union(elements2)
    jaccard_similarity = len(intersection) / len(union) if len(union) > 0 else 0
    print(f"Jaccard Similarity: {jaccard_similarity}")
    return jaccard_similarity > difference_limit, jaccard_similarity


def compare_image_and_xml(xml_path_1, xml_path_2, threshold_xml, screenshot_filepath_1, screenshot_filepath_2,
                          threshold_image):
    with open(xml_path_1, 'r', encoding='utf-8') as html_file:
        xml_1 = html_file.read()
    with open(xml_path_2, 'r', encoding='utf-8') as html_file:
        xml_2 = html_file.read()
    result_xml, result_nums = compare_actions(xml_1, xml_2, threshold_xml)
    result_images, result_difs = compare_images(screenshot_filepath_1, screenshot_filepath_2, threshold_image)
    return result_xml, result_images, result_nums, result_difs


def compare_unique(page1, page2, bm25, data_unique2all, data_all2unique, data_output_path, page2_dir, diff_max,
                   diff_png):
    if len(page1) > 1:
        result_xml, result_images, result_nums, result_difs = compare_image_and_xml(
            data_output_path + page2_dir + "/" + page2 + "-xml.txt",
            data_output_path + page2_dir + "/" + page1 + "-xml.txt", diff_max,
            data_output_path + page2_dir + "/" + page2 + "-screen.png",
            data_output_path + page2_dir + "/" + page1 + "-screen.png", diff_png)
        temp_valid = True
        if result_xml and result_images:
            unique_name = data_all2unique[page1]
            if unique_name in data_unique2all:
                if page2 not in data_unique2all[unique_name]:
                    data_unique2all[unique_name].append(page2)
                data_all2unique[page2] = unique_name
                temp_valid = False
        if temp_valid:
            with open(data_output_path + page2_dir + "/" + page2 + "-html.txt", 'r', encoding='utf-8') as f:
                bm_query = f.readlines()
                f.close()
            compare_index, compare_name = bm25.get_max(bm_query)
            result_xml, result_images, result_nums, result_difs = compare_image_and_xml(
                data_output_path + page2_dir + "/" + page2 + "-xml.txt",
                data_output_path + compare_name + "/" + compare_name + "-xml.txt", diff_max,
                data_output_path + page2_dir + "/" + page2 + "-screen.png",
                data_output_path + compare_name + "/" + compare_name + "-screen.png", diff_png)
            if result_xml and result_images:
                if page2 not in data_unique2all[compare_name]:
                    data_unique2all[compare_name].append(page2)
                data_all2unique[page2] = compare_name
                temp_valid = False
            else:
                data_unique2all[page2] = [page2]
                data_all2unique[page2] = page2
                bm25.appendItem(bm_query, page2)
        bm25.printPara()
    return bm25, data_unique2all, data_all2unique


# bm25,data_unique2all,data_all2unique=compare_unique(page1,page2,bm25,data_unique2all,data_all2unique,data_output_path,diff_max,diff_png)

bm25 = BM25(docs, docs_name)

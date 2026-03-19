import os
import uuid
import json
import time
import argparse
from PIL import Image
from datetime import datetime

from utils.mobile_agent_e import (
    InfoPool,
    Manager,
    Executor,
    Notetaker,
    ActionReflector,
    INPUT_KNOW
)
from utils.call_mobile_agent_e import GUIOwlWrapper
from utils.android_controller import AndroidController
from modules.validator import Validator, Designer
from modules.assistant import Assistant
from tools.utils import clean_json_markers
from constants import adb_path
from tools.state_graph_manager import StateGraphManager, StateNode, TransitionEdge

"""
首先规定好需要的记录，使用数据结构还是文件
然后记录每一轮次，直到某一轮次成功或者达到最大步数，只有检测到错误才开启新的轮次
轨迹的数据怎么记录，对图片的关键元素记录还是仅仅是描述（xml？）
动作信息的总结，怎么判定动作有效否（界面的变化 or 前面相同的动作有效否）
怎么设计精简的上下文（针对提示词欧畅，有用信息提取不到

后期：
怎么实现有效历史的复用，是否可以执行多步
时间 和 token 消耗的计算
"""
waiting_time = 2

def run_instruction(api_key, base_url, model, instruction, coor_type, log_path, max_step=25, max_rounds=5):

    assistant = Assistant('glm-4.6v-flash')
    validator = Validator(Assistant('openai/gpt-5.2'))
    controller = AndroidController(adb_path)

    save_path = log_path
    image_save_path = os.path.join(save_path, "images")
    xml_save_path = os.path.join(save_path, "xmls")
    os.makedirs(image_save_path, exist_ok=True)
    os.makedirs(xml_save_path, exist_ok=True)

    # 初始化状态图管理器
    graph_manager = StateGraphManager(os.path.join(save_path, "state_graph.json"))

    info_pool = InfoPool(
        additional_knowledge_manager='',
        additional_knowledge_executor=INPUT_KNOW,
        err_to_manager_thresh=2
    )

    vllm = GUIOwlWrapper(api_key, base_url, model)
    manager = Manager()
    executor = Executor()
    action_reflector = ActionReflector()
    message_manager, message_operator, message_reflector, message_notekeeper = None, None, None, None
    info_pool.instruction = instruction

    current_round = 1
    current_state_id = None  # 当前状态ID

    while current_round <= max_rounds:
        print(f"\n=== 开始第 {current_round} 轮尝试 ===")

        for step in range(max_step):
            if step == max_step:
                # task_result_path = os.path.join(save_path, "task_result.json")
                # current_time = datetime.now()
                # formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")
                # task_result_data = {"goal": instruction, "finish_dtime": formatted_time, "hit_step_limit": 1.0}
                # with open(task_result_path, 'w', encoding='utf-8') as json_file:
                #     json.dump(task_result_data, json_file, ensure_ascii=False, indent=4)
                print('the task has reach the max_step')
                return "Max step reached"

            if step == 0:
                current_time = datetime.now()
                formatted_time = current_time.strftime(
                    f'%Y-%m-%d-{current_time.hour * 3600 + current_time.minute * 60 + current_time.second}-{str(uuid.uuid4().hex[:8])}')
                local_image_dir = os.path.join(image_save_path, f"screenshot_{formatted_time}.png")
            else:
                local_image_dir = local_image_dir2


            # get the screenshot
            for _ in range(5):
                if not controller.get_screenshot(local_image_dir):
                    print("Get screenshot failed, retry.")
                    time.sleep(waiting_time)
                else:
                    break
            # get xml
            xml_name = f'step{step}-round{current_round}-{str(uuid.uuid4().hex[:8])}'
            local_xml_dir = os.path.join(xml_save_path, f"xml_{xml_name}.xml")
            xml_str, xml_compressed_str = controller.pull_xml(local_xml_dir)
            print("xml compressed str:\n" + xml_compressed_str)

            width, height = Image.open(local_image_dir).size

            # 查找或创建当前状态节点
            matched_state_id = graph_manager.find_similar_state(local_xml_dir)
            if matched_state_id:
                print(f"找到匹配的状态: {matched_state_id}")
                current_state_id = matched_state_id
            else:
                print("未找到匹配状态，创建新状态节点")
                current_state_id = graph_manager.add_state_node(local_image_dir, local_xml_dir)
                print(f"创建新状态节点: {current_state_id}")

            ###############
            ### designer ##
            ###############
            if step == 0:
                info_pool.related_info = ''
                designer = Designer(Assistant('glm-4.5-flash'))
                milestone_prompt = designer.get_prompt(info_pool)
                milestones_result = designer.get_milestone(milestone_prompt)
                milestones_result = clean_json_markers(milestones_result)
                milestones_data = json.loads(milestones_result)
                info_pool.milestones = milestones_data
                log_txt = os.path.join(save_path, "log.txt")
                with open(log_txt, 'w', encoding='utf-8') as f:
                    f.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S\n'))
                    f.write(f"Task goal: {instruction}\n")
                    f.write(f"Round: {current_round}\n")
                    f.write(f"milestones: {milestones_result}\n")
            with open(log_txt, 'a', encoding='utf-8') as f:
                f.write(f"---step {step} (Round {current_round})---\n")
            ###############
            ### marker ###
            ###############
            if step == 0 or info_pool.action_outcomes[-1] == 'A':
                marker_prompt = """
                You will be given the instruction of user and current picture.
                ### User Instruction: {instruction}
                Record information related to the instruction and closely associated with them, which may be used later.
                If the instruction is related to dates(such as 'this week','this Monday') or it is related to OpenTracks app, you should record the date information based on the opening screen interface.
                If there is no information related to the instructions, just output 'None.'
            
                For Example:
                1. User instruction: 'record the last day's activity'.
                Because the user command is time-related and if the current interface is the main interface and show the date, you should output 'Today's date is ***'
                2. User instruction: 'search the recipe and add it into Broccoli recipe app'
                If current interface show the details of recipes, you should record all information related to the instruction.
                """
                info, _, _ = assistant.predict_mm(marker_prompt.format(instruction=instruction), [local_image_dir])
                if len(info) < 15 and 'None' in info:
                    print('No important note')
                else:
                    print("current info: " + info)
                    if info not in info_pool.related_info:
                        info_pool.related_info += info + '\n'
            # 应该再构建一个页面转移状态
            # 标识为图片名，转移动作
            # if step == 0:
            #     # 加入图片
            # else:
            #     # 加入转移动作和新图片

            info_pool.error_flag_plan = False
            err_to_manager_thresh = info_pool.err_to_manager_thresh
            if len(info_pool.action_outcomes) >= err_to_manager_thresh:
                # check if the last err_to_manager_thresh actions are all errors
                latest_outcomes = info_pool.action_outcomes[-err_to_manager_thresh:]
                count = 0
                for outcome in latest_outcomes:
                    if outcome in ["B", "C"]:
                        count += 1
                if count == err_to_manager_thresh:
                    info_pool.error_flag_plan = True

            skip_manager = False
            ## if previous action is invalid, skip the manager and try again first ##
            if not info_pool.error_flag_plan and len(info_pool.action_history) > 0:
                if info_pool.action_history[-1]['action'] == 'invalid':
                    skip_manager = True

            if not skip_manager:
                print("\n### Manager ... ###\n")
                prompt_planning = manager.get_prompt(info_pool)
                output_planning, message_manager, raw_response = vllm.predict_mm(
                    prompt_planning,
                    [local_image_dir]
                )
                with open(log_txt, 'a', encoding='utf-8') as f:
                    f.write(f"###Manager thought: \n{output_planning}\n")

            # message_save_path = os.path.join(save_path, f"step_{step + 1}")
            # os.mkdir(message_save_path)
            # message_file = os.path.join(message_save_path, "manager.json")
            # message_data = {"name": "manager", "messages": message_manager, "response": output_planning,
            #                 "step_id": step + 1}
            # with open(message_file, 'w', encoding='utf-8') as json_file:
            #     json.dump(message_data, json_file, ensure_ascii=False, indent=4)

            parsed_result_planning = manager.parse_response(output_planning)
            info_pool.completed_plan = parsed_result_planning['completed_subgoal']
            info_pool.plan = parsed_result_planning['plan']
            if not raw_response:
                raise RuntimeError('Error calling vLLM in planning phase.')

            print('Completed subgoal: ' + info_pool.completed_plan)
            print('Planning thought: ' + parsed_result_planning['thought'])
            print('Plan: ' + info_pool.plan, "\n")

            if "Finished" in info_pool.plan.strip() and len(info_pool.plan.strip()) < 15:
                print("Instruction finished, stop the process.")
                # task_result_path = os.path.join(save_path, "task_result.json")refer the code when reach the max_step
                graph_manager.save_graph()  # 保存最终状态图
                return "Success"
            else:
                print("\n### Operator ... ###\n")

                # 检查是否有推荐的动作
                recommended_action = None
                if current_state_id:
                    recommended_action = graph_manager.get_preferred_next_action(current_state_id)
                    if recommended_action:
                        print(f"基于历史推荐动作: {recommended_action}")

                prompt_action = executor.get_prompt(info_pool)
                output_action, message_operator, raw_response = vllm.predict_mm(
                    prompt_action,
                    [local_image_dir],
                )

                if not raw_response:
                    raise RuntimeError('Error calling LLM in operator phase.')
                parsed_result_action = executor.parse_response(output_action)
                action_thought, action_object_str, action_description = parsed_result_action['thought'], \
                                                                        parsed_result_action['action'], \
                                                                        parsed_result_action['description']

                info_pool.last_action_thought = action_thought
                info_pool.last_summary = action_description

                if (not action_thought) or (not action_object_str):
                    print('Action prompt output is not in the correct format.')
                    info_pool.last_action = {"action": "invalid"}
                    info_pool.action_history.append({"action": "invalid"})
                    info_pool.summary_history.append(action_description)
                    info_pool.action_outcomes.append("C")
                    info_pool.error_descriptions.append("invalid action format, do nothing.")
                    continue

            action_object_str = action_object_str.replace("
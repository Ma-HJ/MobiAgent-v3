import os
import json
import time
import argparse
from PIL import Image
from datetime import datetime

from tools.draw_box import get_colors_desc, draw_element_boxes
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
from tools.utils import clean_json_markers, print_with_color
from tools.state_graph_manager import StateGraphManager, TransitionEdge, StateNode
from constants import api_key, adb_path, model, base_url
from android_world.env import adb_utils
from tools.validate_action import ActionValidator

"""
首先规定好需要的记录，使用数据结构还是文件
然后记录每一轮次，直到某一轮次成功或者达到最大步数，只有检测到错误才开启新的轮次
动作信息的总结，怎么判定动作有效否（界面的变化 or 前面相同的动作有效否）
怎么设计精简的上下文（针对提示词过长，有用信息提取不到

后期：
怎么实现有效历史的复用，是否可以执行多步
时间 和 token 消耗的计算
"""
waiting_time = 2


def run_instruction(env, graph_manager: StateGraphManager, instruction, coor_type, log_path, max_step, round, add_K):
    assistant = Assistant('glm-4.6v-flash')
    # validator = Validator(Assistant('openai/gpt-5.4'))
    validator = Validator(assistant)
    controller = AndroidController(adb_path)
    text_assistant = Assistant('glm-4.7-flash')

    save_path = log_path
    image_save_path = os.path.join(save_path, "images")
    xml_save_path = os.path.join(save_path, "xmls")
    os.mkdir(image_save_path)
    os.mkdir(xml_save_path)
    pending_validations = []

    info_pool = InfoPool(
        additional_knowledge_manager=add_K,
        additional_knowledge_executor=INPUT_KNOW,
        err_to_manager_thresh=2
    )

    vllm = GUIOwlWrapper(api_key, base_url, model)
    manager = Manager()
    executor = Executor()
    action_reflector = ActionReflector()

    info_pool.instruction = instruction
    info_pool.colors = get_colors_desc()
    log_txt = os.path.join(save_path, f"log.txt")

    for step in range(max_step):
        if step == max_step:
            print('the task has reach the max_step')
            break

        if step == 0:
            local_image_dir = os.path.join(image_save_path, f"screenshot_step0.png")
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
        if step == 0:
            local_xml_dir = os.path.join(xml_save_path, f"xml_step0.xml")
            controller.get_xml(local_xml_dir)
            if round == 0:
                graph_manager.cur_node = StateNode(local_image_dir, local_xml_dir)
                graph_manager.root_node = graph_manager.cur_node
                graph_manager.add_state_node(graph_manager.cur_node)
                graph_manager.edges[graph_manager.cur_node.state_id] = []
            else:
                graph_manager.cur_node = graph_manager.root_node

            # print("xml compressed str:\n" + xml_compressed_str)

        width, height = Image.open(local_image_dir).size
        print_with_color(f"Round_{round} / step_{step} is running...", 'blue')
        ###############
        ### designer ##
        ###############
        if step == 0:
            print("running designer...")
            info_pool.related_info = ''
            designer = Designer(text_assistant)
            milestone_prompt = designer.get_prompt(info_pool)
            milestones_result = designer.get_milestone(milestone_prompt)
            milestones_result = clean_json_markers(milestones_result)
            milestones_data = json.loads(milestones_result)
            info_pool.milestones = milestones_data

            with open(log_txt, 'w', encoding='utf-8') as f:
                f.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S\n'))
                f.write(f"Task goal: {instruction}\n")
                f.write(f"milestones: {milestones_result}\n")
        with open(log_txt, 'a', encoding='utf-8') as f:
            f.write(f"\n\n---step {step}\n")
        ###############
        ### marker ###
        ###############
        # if step == 0 or info_pool.action_outcomes[-1] == 'A':
        if info_pool.is_valid:
            print("running markor...")
            marker_prompt = """
            You will be given the instruction of user and current picture.
            ### User Instruction: {instruction}
            
            # Record Information
            Record information related to the instruction and closely associated with them, which may be used later.
            If the instruction is related to dates(such as 'this week','Monday', 'last day') or it is related to OpenTracks app, you should record the date information based on the opening screen interface.
            If there is no information related to the instructions, just output 'None.'
            
            # Current Screen State Analysis 
            Using the provided screenshot describe the current screen state. Such as "Homepage of <AppName>", "Search Page of <sth>", "Item Detail Page in <sth>", "Notes List in <sth>", "Settings Page of <sth>".
            
            Provide your output in the following format, which contains two parts: 
            
            ### Note ###
            <The information related to instruction>
            
            ### State ###
            <Brief natural language summary of the screen>
            """

            info, _, _ = assistant.predict_mm(marker_prompt.format(instruction=instruction), [local_image_dir])
            note = info.split("### Note ###")[-1].split("### State")[0].strip()
            state_desc = info.split("### State ###")[-1].strip()
            if 'None.' not in note:
                info_pool.related_info += note + '\n'
        graph_manager.cur_node.description = state_desc
        # if len(info) < 15 and 'None' in info:
        #     print('No important note')
        # else:
        #     print("current info: " + info)
        #     if info not in info_pool.related_info:
        #         info_pool.related_info += info + '\n'

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
            if info_pool.action_history[-1]['action'] == 'invalid' or (not info_pool.is_valid and info_pool.hint[:2] != '元素'):
                skip_manager = True

        if not skip_manager:
            print("\n### Manager ... ###\n")
            # 将界面状态告知manager
            info_pool.states = graph_manager.get_state_graph()
            # print(info_pool.states)
            prompt_planning = manager.get_prompt(info_pool)
            output_planning, message_manager, raw_response = vllm.predict_mm(
                prompt_planning,
                [local_image_dir]
            )

        parsed_result_planning = manager.parse_response(output_planning)
        info_pool.completed_plan = parsed_result_planning['completed_subgoal']
        info_pool.plan = parsed_result_planning['plan']
        if not raw_response:
            raise RuntimeError('Error calling vLLM in planning phase.')
        with open(log_txt, 'a', encoding='utf-8') as f:
            f.write(
                f"### Manager: \nCompleted subgoal: {info_pool.completed_plan}\nthought: {parsed_result_planning['thought']}\nplan: {info_pool.plan}\n")

        print('Completed subgoal: ' + info_pool.completed_plan)
        print('Planning thought: ' + parsed_result_planning['thought'])
        print('Plan: ' + info_pool.plan, "\n")

        if "Finished" in info_pool.plan.strip() and len(info_pool.plan.strip()) < 15:
            print("Instruction finished, stop the process.")
            # task_result_path = os.path.join(save_path, "task_result.json")refer the code when reach the max_step
            break
        else:
            print("\n### Operator ... ###\n")
            info_pool.wrong_actions = graph_manager.get_error_transitions(graph_manager.cur_node.state_id)
            # draw_element_boxes(local_image_dir, local_xml_dir)

            prompt_action = executor.get_prompt(info_pool)

            output_action, message_operator, raw_response = vllm.predict_mm(
                prompt_action,
                # [local_image_dir[:-4] + '_boxes.png'],
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

        action_object_str = action_object_str.replace("```", "").replace("json", "").strip()
        with open(log_txt, 'a', encoding='utf-8') as f:
            f.write(
                f"### Executor: \nthought: {action_thought}\naction: {action_object_str}\naction_description: {action_description}\n")

        print('Thought: ' + action_thought)
        print('Action: ' + action_object_str)
        print('Action description: ' + action_description)

        try:
            action_object = json.loads(action_object_str)
            action_valid = ''
            if action_object['action'] == "answer":
                answer_content = action_object['text']
                print(f"Instruction finished, answer: {answer_content}, stop the process.")
                break

            if coor_type != "abs":
                if "coordinate" in action_object:
                    action_object['coordinate'] = [int(action_object['coordinate'][0] / 1000 * width),
                                                   int(action_object['coordinate'][1] / 1000 * height)]
                    print("Coordinate: " + str(action_object['coordinate']))
                if "coordinate2" in action_object:
                    action_object['coordinate2'] = [int(action_object['coordinate2'][0] / 1000 * width),
                                                    int(action_object['coordinate2'][1] / 1000 * height)]
            judger = ActionValidator(local_xml_dir)
            is_valid, validate_result = judger.validate_action(action_object)
            info_pool.is_valid = is_valid
            if not is_valid:
                # 元素没有对应属性
                if validate_result[:2] == "元素":
                    info_pool.hint = validate_result
                # 没找到元素 或者 格式有问题, 这时候通过info_pool.is_valid跳过执行manager
                else:
                    info_pool.hint = validate_result
                continue

            if action_object['action'] == "click":
                controller.tap(action_object['coordinate'][0], action_object['coordinate'][1])
            elif action_object['action'] == "long_press":
                controller.slide(action_object['coordinate'][0], action_object['coordinate'][1],
                                 action_object['coordinate'][0], action_object['coordinate'][1])
            elif action_object['action'] == "swipe":
                controller.slide(action_object['coordinate'][0], action_object['coordinate'][1],
                                 action_object['coordinate2'][0], action_object['coordinate2'][1])
            elif action_object['action'] == "type":
                controller.type(action_object['text'])
            elif action_object['action'] == "system_button":
                if action_object['button'] == "Back":
                    controller.back()
                elif action_object['button'] == "Home":
                    action_valid = 'home'
                    controller.home()
            elif action_object['action'] == "open_app":
                print("Open app: " + action_object['text'])
                adb_utils.launch_app(action_object['text'].lower().strip(), env.controller)
        except:
            # print_with_color("Invalid action format, do nothing.", 'red')
            info_pool.last_action = {"action": "invalid"}
            info_pool.action_history.append({"action": "invalid"})
            info_pool.summary_history.append(action_description)
            info_pool.action_outcomes.append("C")
            info_pool.error_descriptions.append("invalid action format, do nothing.")
            local_image_dir2 = local_image_dir
            continue

        info_pool.last_action = action_object

        # if step == 0:
        #     time.sleep(5)  # maybe a pop-up when first open an app
        time.sleep(2)

        local_image_dir2 = os.path.join(image_save_path, f"screenshot_step{step + 1}.png")

        # get the screenshot
        for _ in range(5):
            if not controller.get_screenshot(local_image_dir2):
                print("Get screenshot failed, retry.")
                time.sleep(waiting_time)
            else:
                break

        pending_validations = [{
            "step": step,
            'future': validator.start_async_validation(validator, info_pool, [local_image_dir2], log_txt)
        }]
        print("\n### Action Reflector ... ###\n")
        prompt_action_reflect = action_reflector.get_prompt(info_pool)
        output_action_reflect, message_reflector, raw_response = vllm.predict_mm(
            prompt_action_reflect,
            [
                local_image_dir,
                local_image_dir2,
            ],
        )

        with open(log_txt, 'a', encoding='utf-8') as f:
            f.write(f"### Reflector: \n{output_action_reflect}\n")

        parsed_result_action_reflect = action_reflector.parse_response(output_action_reflect)
        outcome, error_description = (
            parsed_result_action_reflect['outcome'],
            parsed_result_action_reflect['error_description']
        )
        info_pool.changes = parsed_result_action_reflect['changes']
        info_pool.hint = 'changes'
        progress_status = info_pool.completed_plan

        if "A" in outcome:  # Successful. The result of the last action meets the expectation.
            action_outcome = "A"
        elif "B" in outcome:  # Failed. The last action results in a wrong page. I need to return to the previous state.
            action_outcome = "B"
        elif "C" in outcome:  # Failed. The last action produces no changes.
            action_outcome = "C"
        else:
            raise ValueError("Invalid outcome:", outcome)

        print('Action reflection outcome: ' + action_outcome)
        print('Action reflection error description: ' + error_description)
        print('Action result changes: ' + info_pool.changes)
        print('Action reflection progress status: ' + progress_status, "\n")

        info_pool.action_history.append(json.loads(action_object_str))
        info_pool.summary_history.append(action_description)
        info_pool.action_outcomes.append(action_outcome)
        info_pool.error_descriptions.append(error_description)
        info_pool.progress_status = progress_status

        #################
        ### Validator ###
        #################

        # validate_prompt = validator.get_prompt(info_pool)
        # validation = validator.validate(validate_prompt, [local_image_dir2])
        # validation = clean_json_markers(validation)
        # validate_data = json.loads(validation)
        # print("\n### Validator ... ###\n" + validation)
        #
        # with open(log_txt, 'a', encoding='utf-8') as f:
        #     f.write(f"### Validation: \n{validation}\n")
        #
        # # action_score = int(validate_data['action']['score'])
        # # interface_score = int(validate_data['interface']['score'])
        # # # info_pool.recommendation = validate_data['recommendation']
        # # final_score = 0.6 * action_score + 0.4 * interface_score
        # #
        # # Error_flag = False
        # # if action_score < 5 or final_score < 6:
        # #     Error_flag = True
        # current_state = validate_data['state']
        # score = int(validate_data['score'])
        #
        # Error_flag = False
        # if score < validator.get_threshold(current_state):
        #     Error_flag = True
        # 构图
        local_xml_dir = os.path.join(xml_save_path, f"xml_step{step + 1}.xml")
        controller.get_xml(local_xml_dir)
        # todo: 是否需要先看动作的有效性
        if action_valid == 'home':
            graph_manager.cur_node = graph_manager.root_node
            continue

        cur_node = graph_manager.cur_node
        new_node = StateNode(local_image_dir2, local_xml_dir)
        # graph_manager.add_state_node(local_image_dir2, local_xml_dir)
        # print("xml compressed str:\n" + xml_compressed_str)
        transition_action = {"thought": action_thought, "action": action_object, "description": action_description}

        # 新状态应该完成与之前的对比，决定是否增加新的状态
        state_id = graph_manager.find_similar_state(local_image_dir2)

        validate_data = validator.check_completed_validations(pending_validations)
        print("Validate data: \n", validate_data)
        with open(log_txt, 'a', encoding='utf-8') as f:
            f.write(f"### Validation: \n{validate_data}\n")
        Error_flag = False
        if validate_data['score'] < validator.get_threshold(validate_data['state']):
            Error_flag = True

        if state_id is None:
            graph_manager.add_state_node(new_node)
            graph_manager.edges[new_node.state_id] = []  # 初始化新节点的边
            edge = TransitionEdge(cur_node.state_id, new_node.state_id, transition_action, Error_flag)
            graph_manager.edges[cur_node.state_id].append(edge)  # 加入边
            graph_manager.cur_node = new_node
        else:
            # if state_id == cur_node.state_id:
            #     # 此时要看这个动作是否导致了错误的结果，如果是相同界面但是没啥用，那么应该仅提示动作出错
            #     graph_manager.add_transition_edge(cur_node.state_id, state_id, transition_action, Error_flag)
            #
            #     print("Same state")
            # else:
            #     # 此时已经有对应状态了，但是状态存在如果是不同的路径，则检测两点有无路径
            #     print("Different state")
            #     graph_manager.add_transition_edge(cur_node.state_id, state_id, transition_action, Error_flag)
            graph_manager.add_transition_edge(cur_node.state_id, state_id, transition_action, Error_flag)
            graph_manager.cur_node = graph_manager.nodes[state_id]
            print("No new state add")

        if Error_flag:
            # controller.home()
            # 总结执行路径（状态和动作），反思错误之处，结合改进方法
            reviewer = Assistant('glm-4.7-flash')
            # graph_manager.cur_node.description = validate_data['interface']['analysis']
            summary_prompt = f"""
You need to summarize the execution process.
### Here are some processes performed on a mobile phone, including interface nodes and transformation information edges:
{graph_manager.get_state_graph()}

### The error verification results are as follows, including analysis of the actions and the final interface, as well as recommendations.
{validate_data}

You need to first match the transformation information with the interface information, summarizing what decisions are made on a certain interface and to which interface it leads; 
then reflect on the reasons for the final errors and provide suggestions for improvement.

Provide your output in the following format, which contains three parts:
Execution Status: <A general summary of the execution path>
Error Cause: <The step where the error occurred and the reason>
Improvement Suggestions: <How to avoid the error in the next execution>"""

            result = reviewer.predict_mm(summary_prompt, [])
            with open(log_txt, 'a', encoding='utf-8') as f:
                f.write(f"\n### Experience\n{result}\n")
            return result

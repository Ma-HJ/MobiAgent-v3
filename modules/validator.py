import json

from utils.mobile_agent_e import InfoPool
from tools.utils import clean_json_markers

class Validator:
    def __init__(self, model):
        self.client = model

    def get_prompt(self, info_pool: InfoPool):
        prompt = 'You are evaluating the current step of a GUI agent based on its execution history, current interface screenshot, and user instruction.\n'
        prompt += f"### User Request ###\n{info_pool.instruction}\n\n"
        # manager
        prompt += f'### Plan ###\n{info_pool.plan}\n'
        # executor
        prompt += '### Last Action ###\n'
        prompt += f'action thought: {info_pool.last_action_thought}\n'
        prompt += f'action: {info_pool.last_action}\n'
        # prompt += f'action description: {info_pool.last_summary}\n'

        prompt += f'### Action history ###\n{info_pool.summary_history}\n'
        # prompt += f'### State changes###\n{info_pool.changes}\n'
        # reflector
        # prompt += f"Action reflection error description: {info_pool.error_descriptions[-1]}\n"
        # if info_pool.action_outcomes[-1] == "C":
        #     prompt += 'Now you should suggest the next action, because the current action is not effective or has reached the boundary.'
        prompt += f"### Milestones ###\n{info_pool.milestones}\n\n"
        prompt += """
        You should first identify which stage of the milestone you are currently in, 
        and then determine whether the corresponding milestone has already been completed or is still in the exploratory execution of that milestone based on the current situation and 'Action history'. 
        
        Two situations of the current state: 
        if the corresponding milestone is completed('PROGRESS'), check whether the dependent milestones are completed in a right order and whether the completion of the current milestone is correct; 
        if it is still exploring under the milestone('EXPLORATION'), check if it has fallen into an abnormal action loop.
        
        You should score according to the corresponding situation：
        0-2 means you believe cannot achieve the goal.
        3-4 means it is unlikely to achieve the goal.
        5-6 means it has a certain chance of achieving the goal.
        7-8 means it is very likely to achieve the goal.
        9-10 means you believe it will definitely achieve the goal. 
        
        """
        prompt += """
{
    "state": "If the corresponding milestone is completed, output 'PROGRESS'; If it is still exploring under the milestone, output 'EXPLORATION'",
    "score": "A score from 0 to 10 based on situation. Milestone is completed in wrong way and falling into an abnormal action loop should be given low score.",
    "reason": "An explanation of the score you given." 
    
}
        """
    # 以下两段的检测粒度太细，所以暂时取消
        """
### Guidelines:
Please provide the following information:

Sub-goal Completion Assessment and Score:
    Analyse whether the current action has successfully completed a sub-goal of the user instruction. 
    Consider the sequence of previous actions and their purposes. Think how the current step aligns with the expected sub-goals.
    
    Identify the current corresponding milestone, and then check whether the previous milestones have all been completed.
    It is necessary to judge whether the milestones it depends on have all been completed based on the action history.
    
    Assign a score from 0 to 10 based on the accuracy and relevance of the current step in achieving the sub-goal.
    1. If an action is repeated multiple times and receives negative feedback(Action reflection error description), you should give it a low score.
    2. If there is no corresponding action history to confirm that its dependencies node has been completed and it proceed with the current milestone, a low score should be given.
    3. If the thought is correct but just did not succeed, give it score of 7-8.
    4. Find the milestone corresponding to the current action. If there are still tasks to be completed for the current milestone, give an appropriate score.
        If you think the current milestone has been completed based on the 'Action history', but the results are incorrect, give a low score.
    5. If the current situation does not meet expectations but doesn't violate the milestone, give it score of 7-8.
    6. If the current instruction severely violates guidelines and could cause irreversible consequences, give a low score.
    
    0-2 means you believe this action definitely cannot achieve the goal.
    3-4 means it is unlikely to achieve the goal.
    5-6 means it has a certain chance of achieving the goal.
    7-8 means it is very likely to achieve the goal.
    9-10 means you believe this action will definitely achieve the goal. 

Interface Screenshot Assessment and Score:
    Evaluate the current interface screenshot to determine if it supports the user instruction. Such as if the current file name exactly match the user's requirements?
    Provide a detailed explanation of how the interface elements match the user instruction. 
    Assign a score from 0 to 10 based on the relevance and correctness of the interface elements in relation to the user instruction.
    A score of 0-6 means the current interface is very unlikely to achieve the goal, while 6-10 indicates the current interface aligns with the user's instruction.
    
Adjustment Recommendations:
    Based on the assessments above, provide specific recommendations for improving the current step. 
    If the sub-goal completion is not satisfactory, suggest what actions should be taken or what changes should be made in the next step. 
    If the interface screenshot shows issues, give the reason of issues against the user instruction.
        """

        """
Provide your output in json format, and especially avoid using unnecessary quotation marks or other punctuation marks, which contains parts:
{   
    "action": {
        "analysis": "An explanation of how the current step aligns with the expected sub-goals. And analyse whether the previous milestones have all been completed." 
        "score": "A score from 0 to 10 based on the accuracy and relevance of the current step in achieving the sub-goal."
    },
    "interface": {
        "analysis": "An explanation of how the interface elements match the user instruction." 
        "score": "A score from 0 to 10 based on the relevance and correctness of the interface elements in relation to the user instruction."
    },
    "recommendation": "If the current score is low, analyze the reasons for previous failures based on the images and provide suggestions for improvement."
}
        """
        return prompt

    def validate(self, prompt, images: []):
        response, pay_load, raw_response = self.client.predict_mm(prompt, images)

        # 对response进行处理
        return response

    def get_threshold(self, state: str):
        if state == "PROGRESS":
            return 7
        else:
            return 5

    def start_async_validation(self, validator, info_pool, images, log_txt):
        """启动异步验证"""
        import threading

        result_container = {'done': False, 'result': {}}

        def validation_worker():
            try:
                validate_prompt = validator.get_prompt(info_pool)
                validation = validator.validate(validate_prompt, images)
                validation = clean_json_markers(validation)
                validate_data = json.loads(validation)

                result_container['result'] = validate_data

            except Exception as e:
                print(f"Error during validation: {e}")
            finally:
                result_container['done'] = True

        thread = threading.Thread(target=validation_worker, daemon=True)
        thread.start()

        return {'thread': thread, 'container': result_container}

    def check_completed_validations(self, pending_validations, timeout=0):
        """检查是否有已完成的验证，如果有错误立即返回"""
        import time

        for task in pending_validations[:]:  # 使用切片复制避免修改原列表
            container = task['future']['container']
            start_time = time.time()

            # 非阻塞检查（timeout=0）
            while not container['done']:
                # if time.time() - start_time > timeout:
                #     break
                # time.sleep(0.05)
                time.sleep(1)

            if container['done']:
                return container['result']
            # 验证已完成
        #     Error_flag = container['Error_flag']
        #     result = container['result']
        #
        # return {'Error_flag': Error_flag, 'result': result}


class Designer:
    def __init__(self, model):
        self.client = model

    def get_prompt(self, info_pool: InfoPool):
        prompt = "You are tasked with transforming a user's instructions into a structured Directed Acyclic Graph (DAG). Each node in the graph represents a sub-goal with specific attributes."
        prompt += f"### User Request ###\n{info_pool.instruction}\n\n"
        prompt += """
Graph Construction Rules:
    The order of nodes should reflect the most logical and efficient sequence based on the instructions.
    Strictly follow every detail of the instructions.

Node Attributes:
    Each node must have the following attributes:
    "id": A unique identifier for the node (string, kebab-case). Nodes are numbered sequentially.
    "goal": A clear, one-sentence description of the sub-goal (string).
    "dependencies": An array of node IDs that must be completed before this node can start (array of strings).
    "next": An array of node IDs that can start immediately after this node finishes (array of strings).
    
Output Requirements:
    The output should only contain the JSON object without any additional explanations or formatting.

# Example output
{
  "nodes": [
    {
      "id": "node-1",
      "goal": "goal1",
      "dependencies": [],
      "next": ["node-2", "node-3"]
    },
    {
      "id": "node-2",
      "goal": "Rename the file to 'new_example.txt'.",
      "dependencies": ["node-1"],
      "next": ["node-4"]
    },
    {
      "id": "node-3",
      "goal": "Add a new line before the existing content.",
      "dependencies": ["node-1"],
      "next": ["node-4"]
    },
    {
      "id": "node-4",
      "goal": "Save the changes.",
      "dependencies": ["node-2", "node-3"],
      "next": []
    }
  ]
}
"""
        return prompt

    def get_milestone(self, prompt):
        response, pay_load, raw_response = self.client.predict_mm(prompt, [])

        return response



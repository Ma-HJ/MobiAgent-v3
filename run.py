import logging
import os
from datetime import datetime
import time

from android_world.env import env_launcher, adb_utils, tools
from android_world import registry

from retryAgent import run_instruction
from constants import adb_path
from tools.utils import print_with_color, display_result
from tools.state_graph_manager import StateGraphManager
from tools.controll_app import close_app, go_home

_DEVICE_CONSOLE_PORT = 5554
_EMULATOR_SETUP = False
_GRPC_PORT = 8554

ROUNDS = 5

def _log_and_print(msg: str, *args: object) -> None:
  formatted = msg % args if args else msg
  logging.info(formatted)
  print(formatted)

def init_env():
    env = env_launcher.load_and_setup_env(
        console_port=_DEVICE_CONSOLE_PORT,
        emulator_setup=_EMULATOR_SETUP,
        adb_path=adb_path,
        grpc_port=_GRPC_PORT
    )
    env.hide_automation_ui()
    print("Environment has been initialized.")
    return env


def initialize_chrome(env):
    print("Running additional chrome initialization...")
    # handle chrome initialization problem for browser tasks
    adb_utils.launch_app("chrome", env.controller)
    time.sleep(5)

    tool_controller = tools.AndroidToolController(env=env.controller)
    time.sleep(2)

    first_op = False
    try:
        print("try first variant...")
        tool_controller.click_element("Use without an account")
        time.sleep(5.0)
        first_op = True
    except:
        print("Failed to click 'Use without an account' button.")
        pass

    if not first_op:
        print("try second variant...")
        try:
            tool_controller.click_element("Accept & continue")
        except:
            pass
        time.sleep(3.0)
        try:
            tool_controller.click_element("No thanks")
        except:
            pass
        time.sleep(3.0)

    go_home()
    print("Done additional chrome initialization")

def _main():
    env = init_env()

    res_list = {}
    coor_type = 'qwen-vl'

    task_registry = registry.TaskRegistry()
    task_list = task_registry._TASKS

    now = datetime.now()
    time_str = now.strftime("%Y%m%d_%H%M%S")
    cur_path = f"./logs/{time_str}/"
    if not os.path.exists(cur_path):
        os.mkdir(cur_path)

    for taskType in task_list:

        # 先实例化
        params = taskType.generate_random_params()
        task = taskType(params)
        max_step = int(10 * task.complexity)
        _log_and_print('Running task %s with goal "%s"', task.name, task.goal)
        task_path = cur_path + task.name
        if not os.path.exists(task_path):
            os.mkdir(task_path)

        graph_manager = StateGraphManager(os.path.join(task_path, "state_graph.json"))
        round = 0
        experience = ''
        # initialize_chrome(env)
        while round < ROUNDS:
            go_home()
            print_with_color(f"Round {round}", 'blue')

            round_path = task_path + f"/round_{round}"
            if not os.path.exists(round_path):
                os.mkdir(round_path)
            # 环境配置
            task.initialize_task(env)
            if round == 0 and 'chrome' in task.goal.lower():
                initialize_chrome(env)
            try:
                result = run_instruction(env, graph_manager, task.goal, coor_type, round_path, max_step, round, experience)
            except Exception as e:
                print_with_color(f"Exception has been found.\n{e}", 'red')
                break
            finally:
                graph_manager.save_graph()
                close_app()

            # 检测到错误，重新开始
            if result is not None:
                print_with_color("Error has been found.", 'red')
                experience = result
                round += 1
                task.tear_down(env)
            else:
                break
        score = 0
        if round < ROUNDS:
            score = task.is_successful(env)
            task.tear_down(env)

        if score > 0.5:
            print(f"Task Successful ✅; {task.name}: {task. goal}")
            res_list[task.name] = 1
        else:
            print(f"Task Failed ❌; {task.name}: {task.goal}")
            res_list[task.name] = 0

    env.close()
    display_result(res_list)

if __name__ == '__main__':
    _main()

import re
import subprocess
from time import sleep

from constants import adb_path
from tools.utils import print_with_color

def execute_adb(adb_command):

  result = subprocess.run(adb_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
  if result.returncode == 0:
    return result.stdout.strip()
  print_with_color(f"Command execution failed: {adb_command}", "red")
  print_with_color(result.stderr, "red")
  return "ERROR"

# 获取当前活动
def get_current_app():
  command = adb_path + f" shell dumpsys window"
  res = execute_adb(command)

  match = re.search(r"mCurrentFocus=Window{.*?}", res)
  if match:
    window_info = match.group()
    print(window_info)

  app_info = window_info.split(" ")[-1][:-1]
  return app_info

def restart_app():
  app_info = get_current_app()

  command = adb_path + f" shell am force-stop {app_info.split('/')[0]}"
  execute_adb(command)
  # sleep(1)
  command = adb_path + f" shell am start -n {app_info}"
  execute_adb(command)

def close_app():
  app_info = get_current_app()
  command = adb_path + f" shell am force-stop {app_info.split('/')[0]}"
  execute_adb(command)

def go_home():
  command = adb_path + f" shell am start -a android.intent.action.MAIN -c android.intent.category.HOME"
  execute_adb(command)

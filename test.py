# import re
# import subprocess
#
# from constants import adb_path
#
# command = adb_path + f" shell dumpsys window"
# res = subprocess.run(command, capture_output=True, text=True, shell=True)
#
# # print(res.stdout)
#
# match = re.search(r"mCurrentFocus=Window{.*?}", res.stdout)
# if match:
#   window_info = match.group()
#   print(window_info)
#
# app = window_info.split(" ")[-1][:-1]
# print(app)

import json


# from android_world import registry
# task_registry = registry.TaskRegistry()
#
# task_list = task_registry._TASKS
#
# for task in task_list:
#     if 'browser' in str(task):
#         print('yes')
#         break
import os.path
import re

# attrs = []
# lines = yyy
# for line in lines:
#     if 'bounds' in line:
#         bounds_match = re.findall(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', line)
#         if bounds_match and (len(status) > 1 or len(attrs) > 0):
#             # x1, y1, x2, y2 = map(int, bounds_match[0])
#             # coordinates = [int(c) for c in bounds_match[0]]
#             print('ok')
#             # print(status)
#             # print(attrs)
#             # elements.append(
#             #     {'attributes': attrs, "status": status, 'bounds': map(int, bounds_match[0]), "description": desc})
#     elif ';' in line:
#         # 对于checked和selected在status中， focusable似乎没啥作用
#         items = line.split(';')
#         attrs = items[1].strip().split(' ') if items[1].strip() != '' else []
#         status = items[2].strip().split(' ') if items[2].strip() != '' else []
#         print(attrs)
#         print(status)
#         desc = items[-1][:-1].strip()


# from tools.draw_box import draw_element_boxes
# pic = "A:/EmbodiedAI/projs/Mobile-Agent-v3/mobile_v3/logs/20260126_220356/RetroPlayingQueue/round_0/images/screenshot_step0.png"
# xml = "A:/EmbodiedAI/projs/Mobile-Agent-v3/mobile_v3/logs/20260126_220356/RetroPlayingQueue/round_0/xmls/xml_step0_comp.txt"
# draw_element_boxes(pic,  xml)

# from tools.validate_action import ActionValidator
# path = os.path.join(os.getcwd(), "logs/20260302_235621/SimpleCalendarAddOneEvent/round_0/xmls/xml_step2.xml")
# print(path)
# validator = ActionValidator(path)
# width,  height = 1080, 2400
# res, reason = validator.validate_action({"action": "click", "coordinate": [int(width*0.001), int(height*0.5)]})
# print(validator.all_nodes)
# print(res, reason)
from datetime import datetime

a = datetime.now().isoformat()
print(a)
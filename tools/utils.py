import json
import re
from colorama import Fore, Style

def print_with_color(text: str, color=""):
    if color == "red":
        print(Fore.RED + text)
    elif color == "green":
        print(Fore.GREEN + text)
    elif color == "yellow":
        print(Fore.YELLOW + text)
    elif color == "blue":
        print(Fore.BLUE + text)
    elif color == "magenta":
        print(Fore.MAGENTA + text)
    elif color == "cyan":
        print(Fore.CYAN + text)
    elif color == "white":
        print(Fore.WHITE + text)
    elif color == "black":
        print(Fore.BLACK + text)
    else:
        print(text)
    print(Style.RESET_ALL)

def clean_json_markers(text):
    # 匹配 ```json 开头和 ``` 结尾的代码块
    pattern = r'```json\s*(\{.*?\})\s*```'
    # 使用 re.DOTALL 使 . 匹配包括换行符在内的所有字符
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        return matches[0]  # 返回第一个匹配的 JSON 字符串
    return text  # 如果没有匹配，返回原文本

def display_result(res_list):
    # print(json.dumps(res_list))
    total = len(res_list)
    success = 0
    for task_name, res in res_list.items():
        if res == 1:
            print(f"{task_name}\t: 1")
            success += 1
        elif res == 0:
            print(f"{task_name}\t: 0")
    print(f"Total: {total}, Success: {success}, Failed: {total - success}")
    print(f"Success Rate: {(success / total): .2f}")

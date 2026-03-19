import os
import time
import subprocess
from typing import Optional
from tools.utils import print_with_color

from .controller import Controller

class AndroidController(Controller):
    def __init__(self, adb_path):
        self.adb_path = adb_path

    def get_screenshot(self, save_path):
        command = self.adb_path + " shell rm /sdcard/screenshot.png"
        subprocess.run(command, capture_output=True, text=True, shell=True)
        time.sleep(0.5)
        command = self.adb_path + " shell screencap -p /sdcard/screenshot.png"
        subprocess.run(command, capture_output=True, text=True, shell=True)
        time.sleep(0.5)
        command = self.adb_path + f" pull /sdcard/screenshot.png {save_path}"
        subprocess.run(command, capture_output=True, text=True, shell=True)
        
        if not os.path.exists(save_path):
            return False
        else:
            return True

    # xml部分摘自 benchagent中src/executor/android_controller.py
    def compress_xml(self, xml_uncompressed: str, type="plain_text", version="v1"):
        from tools.xml_tool import UIXMLTree
        xml_parser = UIXMLTree()
        try:
            # TODO: Why level=1?
            compressed_xml = xml_parser.process(
                xml_uncompressed, level=1, str_type=type)
            if isinstance(compressed_xml, tuple):
                compressed_xml = compressed_xml[0]

            compressed_xml = compressed_xml.strip()
        except Exception as e:
            compressed_xml = None
            import traceback
            traceback.print_exc()
            print_with_color(f"XML compressed failure: {e}", 'yellow')
        return compressed_xml

    def pull_xml(self, save_path: str):
        command = self.adb_path + " shell rm /sdcard/tmp_xml.xml"
        subprocess.run(command, capture_output=True, text=True, shell=True)
        time.sleep(0.5)
        command = self.adb_path + " shell uiautomator dump /sdcard/tmp_xml.xml"
        subprocess.run(command, capture_output=True, text=True, shell=True)
        time.sleep(0.5)
        command = self.adb_path + f" pull /sdcard/tmp_xml.xml {save_path}"
        subprocess.run(command, capture_output=True, text=True, shell=True)

        if os.path.exists(save_path):
            return True
        else:
            return False

    # Pull a xml description of current device's ui to local, this operation takes roughly **2 seconds**
    def get_xml(self, save_path: str):
        start_time = time.time()  # Start timing
        for _ in range(5):
            if not self.pull_xml(save_path):
                print("Pull xml failed, retrying.")
                time.sleep(0.5)
            else:
                break

        with open(save_path, "r", encoding='utf-8') as file:
            xml_str = file.read()
        # xml_compressed = self.compress_xml(xml_str)
        #
        # compressed_xml_path = save_path[:-4] + "_comp.txt"
        #     # = os.path.join(save_dir, xml_name + "-compressed.xml")
        # with open(compressed_xml_path, "w", encoding='utf-8') as compressed_xml_file:
        #     compressed_xml_file.write(xml_compressed)

        # elapsed_time = time.time() - start_time  # Calculate elapsed time
        # logger.info(f"XML pull operation took {elapsed_time:.2f} seconds")
        # return xml_compressed
        return xml_str

    def tap(self, x, y):
        command = self.adb_path + f" shell input tap {x} {y}"
        subprocess.run(command, capture_output=True, text=True, shell=True)

    def type(self, text):
        text = text.replace("\\n", "_").replace("\n", "_")
        for char in text:
            if char == ' ':
                command = self.adb_path + f" shell input text %s"
                subprocess.run(command, capture_output=True, text=True, shell=True)
            elif char == '_':
                command = self.adb_path + f" shell input keyevent 66"
                subprocess.run(command, capture_output=True, text=True, shell=True)
            elif 'a' <= char <= 'z' or 'A' <= char <= 'Z' or char.isdigit():
                command = self.adb_path + f" shell input text {char}"
                subprocess.run(command, capture_output=True, text=True, shell=True)
            elif char in '-.,!?@\'°/:;()':
                command = self.adb_path + f" shell input text \"{char}\""
                subprocess.run(command, capture_output=True, text=True, shell=True)
            else:
                command = self.adb_path + f" shell am broadcast -a ADB_INPUT_TEXT --es msg \"{char}\""
                subprocess.run(command, capture_output=True, text=True, shell=True)

    def slide(self, x1, y1, x2, y2):
        command = self.adb_path + f" shell input swipe {x1} {y1} {x2} {y2} 500"
        subprocess.run(command, capture_output=True, text=True, shell=True)

    def back(self):
        command = self.adb_path + f" shell input keyevent 4"
        subprocess.run(command, capture_output=True, text=True, shell=True)

    def home(self):
        command = self.adb_path + f" shell am start -a android.intent.action.MAIN -c android.intent.category.HOME"
        subprocess.run(command, capture_output=True, text=True, shell=True)

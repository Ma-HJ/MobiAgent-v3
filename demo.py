import os
from agent import run_instruction


adb_path = "D:/combination/AndroidSdk/platform-tools/adb"
# api_key = os.getenv("DASHSCOPE_API_KEY")
# base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
# model = 'qwen3-vl-plus'
# api_key = os.getenv("NEWAPI_API_KEY")
# base_url = "http://ipads.chat.gpt:3006/v1",
# model = 'gpt-4o'
api_key = 'e00f5ab047914ffda7551fcc873928f7.RgMz5r1gz2XIUBqg'
base_url = "https://open.bigmodel.cn/api/paas/v4"
model = 'glm-4.6v-flash'

instruction = '设置一个早上六点的闹钟'
add_info = ''
coor_type = 'qwen-vl'

res = run_instruction(adb_path, '', api_key, base_url, model, instruction, add_info, coor_type, False)

print(res)

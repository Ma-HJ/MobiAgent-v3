import os
import time

import httpx
from openai import OpenAI
from PIL import Image
from qwen_vl_utils import smart_resize
from io import BytesIO
import base64

from constants import glm_api_text, glm_api_view

def pil_to_base64(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def image_to_base64(image_path):
  dummy_image = Image.open(image_path)
  MIN_PIXELS=3136
  MAX_PIXELS=10035200
  resized_height, resized_width = smart_resize(dummy_image.height,
      dummy_image.width,
      factor=28,
      min_pixels=MIN_PIXELS,
      max_pixels=MAX_PIXELS,)
  dummy_image = dummy_image.resize((resized_width, resized_height))
  return f"data:image/png;base64,{pil_to_base64(dummy_image)}"

class Assistant:

    def __init__(self, model='qwen3-vl-flash'):  # model='gpt-4o'
        self.model = model
        if 'qwen' in model:
            self.client = OpenAI(
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
        elif 'glm' in model:
            if 'v' in model:
                glm_api = glm_api_view
            else:
                glm_api = glm_api_text
            self.client = OpenAI(
                api_key=glm_api,
                base_url="https://open.bigmodel.cn/api/paas/v4"
            )
        elif 'gpt' in model:
            self.client = OpenAI(
                api_key=os.getenv("NEWAPI_API_KEY"),
                base_url="http://ipads.chat.gpt:3006/v1",
                http_client=httpx.Client(proxy='http://ipads:ipads123@202.120.40.82:11235'),
            )

    def predict_mm(self, prompt, images=None):
        if images is None:
            payload = [
                {"role": "user", "content": prompt},
            ]
        else:
            payload = [
                {
                    "role": "user",
                    "content": [
                         {"type": "text", "text": prompt}
                     ]
                 }
            ]
            for img in images:
                payload[0]['content'].append({'type': 'image_url', 'image_url': {'url': image_to_base64(img)}})

        counter = 10
        wait_seconds = 20
        while counter > 0:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=payload
                )
                return response.choices[0].message.content, payload, response
            except Exception as e:
                time.sleep(wait_seconds)
                counter -= 1
                print('Error calling LLM, will retry soon...')
                print(e)
        return 'Error calling LLM', None, None

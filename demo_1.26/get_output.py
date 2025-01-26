import json
import requests
import urllib.request
import urllib.parse
import websockets
 
from demo.utils import image_to_base64
 
server_address = "127.0.0.1:8188"
def queue_prompt(prompt, client_id):
    url = f"http://{server_address}/prompt"
    payload = {"prompt": prompt, "client_id": client_id}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()


def get_image_url(filename, subfolder, folder_type):
    # data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    data = {"filename": filename, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    image_url = "http://{}/view?{}".format(server_address, url_values)
    return image_url

def get_video_url(filename, subfolder, folder_type):
    # data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    data = {"filename": filename, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    video_url = "http://{}/view?{}".format(server_address, url_values)
    return video_url

#解析响应内容为JSON格式并返回 
def get_history(prompt_id):
    with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
        return json.loads(response.read())


#获取图片输出
async def get_imgoutputs(client_id, prompt):
    prompt_id = queue_prompt(prompt, client_id)['prompt_id']
    output_imagesurl=[]
    async with websockets.connect(f"ws://{server_address}/ws?clientId={client_id}") as websocket:        
        while True:
            out = await websocket.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        break 
    history = get_history(prompt_id)[prompt_id]
    print(f"prompt_id:{prompt_id}")
    for node_id, node_output in history['outputs'].items():
        if 'images' in node_output:
            for image in node_output['images']:
                image_url=get_image_url(image['filename'], image['filename'], image['type'])
                output_imagesurl.append(image_url)
        print(f"image_url:{image_url}")
        return  {"image":output_imagesurl}
#获取视频输出
async def get_videooutputs(client_id, prompt):
    prompt_id = queue_prompt(prompt, client_id)['prompt_id']
    output_imagesurl=[]
    async with websockets.connect(f"ws://{server_address}/ws?clientId={client_id}") as websocket:        
        while True:
            out = await websocket.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        break 
    history = get_history(prompt_id)[prompt_id]
    print(f"prompt_id:{prompt_id}")

#获取文本切分
async def get_splitoutputs(client_id,prompt):
    prompt_id = queue_prompt(prompt, client_id)['prompt_id']
    async with websockets.connect(f"ws://{server_address}/ws?clientId={client_id}") as websocket:        
        while True:
            out = await websocket.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        break
    history = get_history(prompt_id)[prompt_id]
    print(f"prompt_id:{prompt_id}")
# async def get_outputs(client_id, prompt):
#     prompt_id = queue_prompt(prompt, client_id)['prompt_id']
#     output_images = []
#     output_tags = []
#     output_videos=[]
#     async with websockets.connect(f"ws://{server_address}/ws?clientId={client_id}") as websocket:        
#         while True:
#             out = await websocket.recv()
#             if isinstance(out, str):
#                 # 解析接收到的JSON消息
#                 message = json.loads(out)
#                 if message['type'] == 'executing':
#                     data = message['data']
#                     # 确保只有在特定条件下才退出循环
#                     if data['node'] is None and data['prompt_id'] == prompt_id:
#                         break 
#     # 根据提示ID获取处理历史
#     history = get_history(prompt_id)[prompt_id]
#     print(f"prompt_id:{prompt}")
#     for node_id, node_output in history['outputs'].items():
#         # 如果节点输出包含图片，则将其转换为Base64编码并添加到输出列表
#         if 'images' in node_output:
#             for image in node_output['images']:
#                 image_base64 = image_to_base64(image['filename'])
#                 url=get_image_url(image['filename'], image['filename'], image['type'])
#                 print("图片url："+url)
#                 output_images.append(image_base64)          
#         if 'tags' in node_output:
#             for tag in node_output['tags']: 
#                 output_tags.append(tag)
#         if 'gifs' in node_output:
#             for video in node_output['gifs']:
#                 output_videos.append(video)
#                 video_url=get_video_url(video['filename'], video['filename'], video['type'])
#                 print("视频url："+video_url)
#     # 返回包含所有收集到的图片和标签的字典
#     return {"images": output_images, "tags": output_tags}
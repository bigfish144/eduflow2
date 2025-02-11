import os
import random
import uuid
import json
import requests
import websockets
import logging
from utils import load_json_template
# from api_utils.prompt_loader import load_checkpoint, load_controlnet, load_loras, load_prompt, load_controlnet_webui
from get_output import *
from fastapi import UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, HTTPException
import asyncio
from gradio_client import Client, handle_file
import shutil

# 配置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
server_address = "127.0.0.1:8188"
url = f"http://{server_address}/prompt"
#切分文本
async def process_split_text(text_content,data):
    client_id = str(uuid.uuid4()) 
    prompt = load_json_template('./workfolows/split_text.json')
    prompt["52"]["inputs"]["input_text"] = text_content
    prompt["52"]["inputs"]["split_num"] = data.mode
    generated_texts = await get_splitoutputs(client_id, prompt)
    # return generated_texts
#文本情绪分析
async def process_getemotion_text(data):
    client_id = str(uuid.uuid4())
    prompt = load_json_template('./workfolows/get_emotion.json')
    prompt["1"]["inputs"]["input_text"] = data.text
    generate_emo_text =await get_emotionoutputs(client_id,prompt)
    # print(generate_emo_text)
    return {"text": generate_emo_text}
#文本生成语音
async def process_texttospeech(data):
    client_id = str(uuid.uuid4())
    prompt = load_json_template('./workfolows/gsv_tts_workflow.json')
    prompt["2"]["inputs"]["text"] = data.text
    print("文本生成语音："+data.text)
    prompt["2"]["inputs"]["language"] = data.savedLangValue
    prompt["8"]["inputs"]["how_to_cut"] = data.savedCutValue
    prompt["8"]["inputs"]["speed"] = data.savedVoiceSpeedValue
    prompt["8"]["inputs"]["temperature"] = data.savedVoiceTempValue
    prompt["9"]["inputs"]["filename_prefix"] = "audio/"+data.output_name
    if data.tts_char == "voice1":
        if data.emotion == "平静":
            prompt["8"]["inputs"]["SoVITS_weight"] = "paimeng-0_e25_s11925.pth"
            prompt["8"]["inputs"]["GPT_weight"] = "paimeng-0-e10.ckpt"
            prompt["3"]["inputs"]["text"] = "说起来，我有一个疑问。那个种子发芽以后，会长出什么东西吗？"
            prompt["4"]["inputs"]["audio"] = "voice2_calm.wav"
        elif data.emotion == "兴奋":
            prompt["8"]["inputs"]["SoVITS_weight"] = "paimeng-3_e25_s2150.pth"
            prompt["8"]["inputs"]["GPT_weight"] = "paimeng-3-e10.ckpt"
            prompt["3"]["inputs"]["text"] = "真的吗？太好啦！"
            prompt["4"]["inputs"]["audio"] = "voice2_happy.wav"
        elif data.emotion == "悲伤":
            prompt["8"]["inputs"]["SoVITS_weight"] = "paimeng-4_e25_s300.pth"
            prompt["8"]["inputs"]["GPT_weight"] = "paimeng-4-e10.ckpt"
            prompt["3"]["inputs"]["text"] = "嗯，好吧。一头雾水。"
            prompt["4"]["inputs"]["audio"] = "voice2_sad.wav"
        else:
            prompt["8"]["inputs"]["SoVITS_weight"] = "paimeng-0_e25_s11925.pth"
            prompt["8"]["inputs"]["GPT_weight"] = "paimeng-0-e10.ckpt"
            prompt["3"]["inputs"]["text"] = "他似乎没沮丧，斗志反而更高了。"
            prompt["4"]["inputs"]["audio"] = "voice2_confused.wav"
        await get_audiooutputs(client_id, prompt)
        return {"outputname": data.output_name}
#自定义生成动作-museV
async def process_custommotion(data):
    client_id = str(uuid.uuid4())
    prompt = load_json_template('./workfolows/moiondiffuser.json')
    prompt["75"]["inputs"]["text"] = data.motionGenPrompt
    prompt["3"]["inputs"]["frames"] = data.motionframe
    prompt["77"]["inputs"]["select"] = data.motionLerp
    prompt["32"]["inputs"]["filename_prefix"] = "motion-pre/"+data.motionoutputname
    await get_custommotionoutputs(client_id, prompt)
    print("自定义生成动作成功："+data.motionoutputname)
    return {"outputname": data.motionoutputname}
#默认生成动作-EMAGE
async def process_defaultmotion(fileName):
    client = Client("H-Liu1997/EMAGE")
    audiopath = "./static/data/audio/"+ fileName +".flac"
    logger.info("默认生成动作:"+audiopath)
    try:
        result = client.predict(
            audio=handle_file(audiopath),  # 输入音频文件的 URL
            model_type="CaMN (Upper only)",  # 选择模型类型，可能的值有 "DisCo (Upper only)", "CaMN (Upper only)", "EMAGE (Full body + Face)"
            render_mesh=True,  # 是否渲染网格模型
            render_face=False,  # 是否渲染2D人脸标志
            render_mesh_face=False,  # 是否渲染网格人脸模型
            api_name="/inference_app"  # API 名称
        )
        print(result)
        # logger.info(f"Prediction result: {result}")
        output_dir = './static/data/motion-pre'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        # 处理视频文件并重命名
        for item in result:
            if isinstance(item, dict) and 'video' in item:
                video_path = item['video']
                if video_path:
                    basename = os.path.basename(video_path)
                    if basename == "camn_output_2dbody_audio.mp4":
                        os.remove(video_path)
                        logger.info(f"Deleted video: {video_path}")
                    elif basename == "camn_output.mp4":
                        new_video_name = fileName + ".mp4"
                        new_video_path = os.path.join(output_dir, new_video_name)
                        shutil.move(video_path, new_video_path)
                        logger.info(f"Renamed video: {video_path} to {new_video_path}")
        
        # 处理 .npz 文件
        for item in result:
            if isinstance(item, str) and item.endswith('.npz'):
                npz_file = item
                if npz_file:
                    os.remove(npz_file)
                    logger.info(f"Deleted .npz file: {npz_file}")
        
        return {"outputname": fileName + ".mp4"}
    except Exception as e:
        logger.error(f"Error in process_defaultmotion: {e}")
        raise HTTPException(status_code=500, detail=str(e))
#角色动作渲染-Musepose
async def process_charrender(data):
    client_id = str(uuid.uuid4())
    prompt = load_json_template('./workfolows/musepose-workflow-demo.json')
    prompt["29"]["inputs"]["video"] = "demo/static/data/motion-pre/"+ data.fileName +".mp4"
    prompt["28"]["inputs"]["image"] = "demo/static/data/character/"+ data.selectedCharValue
    prompt["19"]["inputs"]["filename_prefix"] = "motion/"+ data.fileName
    await get_custommotionoutputs(client_id, prompt)
    print("自定义生成动作成功："+data.fileName)
    return {"outputname": data.fileName}

#动作帧插值
async def interpolate_frames(outputname):
    print(outputname)
    client_id = str(uuid.uuid4())
    prompt = load_json_template('./workfolows/Lerp_Inter.json')
    prompt["6"]["inputs"]["filename_prefix"] = "motion/"+ outputname
    await get_custommotionoutputs(client_id, prompt)
    return {"outputname": outputname}

#口型匹配
async def process_wavtolip(data):
    client_id = str(uuid.uuid4())
    outputname = data.selectedSceneIndex
    prompt = load_json_template('./workfolows/musetalk.json')
    prompt["5"]["inputs"]["bbox_shift"] = data.bbox_shift
    prompt["5"]["inputs"]["batch_size"] = data.batchsize
    prompt["17"]["inputs"]["video"] = "demo/static/data/motion/"+ data.selectedSceneIndex +".mp4"
    prompt["15"]["inputs"]["audio_path"] = "demo/static/data/audio/"+ data.selectedSceneIndex +".flac"
    prompt["13"]["inputs"]["filename_prefix"] = "char_video/"+ outputname
    await get_audiooutputs(client_id, prompt)
    return {"outputname": outputname}

#生成角色-无参考
async def process_generateimgflux(data):
    imagesurls = []  # 存储所有生成的图像
    request_count = 4
    for i in range(request_count):
        print("生成角色无参考_第"+ str(i+1)+"次")
        client_id = str(uuid.uuid4())
        prompt = load_json_template('./workfolows/t2i_flux.json')
        prompt["25"]["inputs"]["noise_seed"] = random.randrange(10**14, 10**15)
        add_text = data.baseStyle
        lora_name = data.loraModel
        if lora_name != "null": #启用lora
            prompt["39"]["inputs"]["select"] = 2
            prompt["38"]["inputs"]["lora_name"] = lora_name
        prompt["47"]["inputs"]["text"] = data.prompt
        prompt["51"]["inputs"]["text"] = add_text
        # prompt["41"]["inputs"]["filename_prefix"] = data.selectedFileName
        prompt["67"]["inputs"]["value"] = data.width
        prompt["68"]["inputs"]["value"] = data.height
        prompt["54"]["inputs"]["select"] = data.removebgornot
        generated_images = await get_imgoutputs(client_id, prompt)
        imagesurls.append(generated_images['image_url'])  # 收集所有生成的图像的url值
    logger.info(imagesurls)
    return {"image_url": imagesurls}

#生成角色-CN
async def process_generateimgflux_with_cn(data):
    imagesurls = []  # 存储所有生成的图像
    request_count = 4
    for i in range(request_count):
        print("生成角色无参考_第"+ str(i+1)+"次")
        client_id = str(uuid.uuid4())
        prompt = load_json_template('./workfolows/FLUX_CN.json')
        prompt["14"]["inputs"]["seed"] = random.randrange(10**14, 10**15)
        add_text = data.baseStyle
        lora_name = data.loraModel
        #输入图片
        prompt["91"]["inputs"]["image"] = "input/"+data.InputRefName
        if lora_name != "null": #启用lora
            prompt["84"]["inputs"]["select"] = 2
            prompt["83"]["inputs"]["lora_name"] = lora_name
        prompt["36"]["inputs"]["strength"] = data.WeightValue
        prompt["80"]["inputs"]["text"] = data.prompt
        prompt["81"]["inputs"]["text"] = add_text
        # prompt["41"]["inputs"]["filename_prefix"] = data.selectedFileName
        prompt["76"]["inputs"]["select"] = data.CN_index
        prompt["86"]["inputs"]["select"] = data.removebgornot
        generated_images = await get_imgoutputs(client_id, prompt)
        imagesurls.append(generated_images['image_url'])  # 收集所有生成的图像的url值
    logger.info(imagesurls)
    return {"image_url": imagesurls}    

#生成角色-IPA
async def process_generateimgflux_with_ipa(data):
    imagesurls = []  # 存储所有生成的图像
    request_count = 4
    client_id = str(uuid.uuid4())
    prompt = load_json_template('./workfolows/Flux_Ipa.json')
    prompt["89"]["inputs"]["seed"] = random.randrange(10**14, 10**15)
    #输入图片
    prompt["98"]["inputs"]["image"] = "input/"+data.InputRefName
    prompt["79"]["inputs"]["weight"] = data.WeightValue
    prompt["97"]["inputs"]["text"] = data.prompt
    prompt["100"]["inputs"]["select"] = data.removebgornot
    generated_images = await get_imgoutputs(client_id, prompt)
    imagesurls.append(generated_images['image_url'])  # 收集所有生成的图像的url值
    logger.info(imagesurls)
    return {"image_url": imagesurls}

# #文生图
# async def process_generateimg(data, request_count=1):
#     imagesurls = []  # 存储所有生成的图像
#     for _ in range(request_count):
#         client_id = str(uuid.uuid4()) 
#         prompt = load_json_template('./workfolows/workflow_api.json')
#         prompt["3"]["inputs"]["seed"] = random.randrange(10**14, 10**15)
#         prompt["6"]["inputs"]["text"] = data.prompt
#         prompt["4"]["inputs"]["ckpt_name"] = data.selectedFileName
#         prompt["5"]["inputs"]["batch_size"] = data.batchsize       
#         generated_images = await get_imgoutputs(client_id, prompt)
#         imagesurls.append(generated_images['image'])  # 收集所有生成的图像的url值
#     # logger.info(imagesurls)
#     return {"images": imagesurls}
# async def process_videogenerateimg(data, request_count=1):
#     videos = []
#     for _ in range(request_count):
#         client_id = str(uuid.uuid4()) 
#         prompt = load_json_template('./workfolows/workflow_api_video.json')
#         generated_images = await get_videooutputs(client_id, prompt)
#         videos.extend(generated_images['videos'])
#     return {"video": videos}

# #图生图
# async def process_imggenerateimg(data, request_count=1):
#     logger.info("图生图")
#     imagesurls = []  # 存储所有生成的图像
#     for _ in range(request_count):
#         client_id = str(uuid.uuid4()) 
#         prompt = load_json_template('./workfolows/workflow_api_i2i.json')
#         prompt["3"]["inputs"]["seed"] = random.randrange(10**14, 10**15) 
#         prompt["6"]["inputs"]["text"] = data.prompt
#         prompt["4"]["inputs"]["ckpt_name"] = data.selectedFileName
#         prompt["10"]["inputs"]["image"] = data.imagename
#         generated_images =await get_imgoutputs(client_id,prompt)
#         imagesurls.append(generated_images['image'])
#     return {"images": imagesurls}

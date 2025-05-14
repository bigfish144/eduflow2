from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
# import random
import logging
import json
import shutil
from bs4 import BeautifulSoup
from router import *
import base64
from io import BytesIO
from PIL import Image
import pydub
from pydub import AudioSegment
import cv2
import numpy as np
import moviepy
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip,ImageSequenceClip, AudioFileClip, concatenate_audioclips, clips_array, concatenate_videoclips
import imageio
from pathlib import Path
import requests
import os
import re

# 配置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI()
"""
当访问根路径时，尝试读取并返回index.html文件的内容，如果文件不存在，则返回404错误。

Returns:
    HTMLResponse: 包含HTML内容的响应，状态码为200或404。
"""

# 初始化，将static 目录中的文件作为静态文件提供
app.mount("/static", StaticFiles(directory="./static"), name="static")
current_directory = os.getcwd()
logger.info(current_directory)
UPLOAD_DIRECTORY = "../input"
#试图打开位于"./static/index.html"路径下的HTML文件
@app.get("/", response_class=HTMLResponse)
def read_root():
    file_path = os.path.join("static", "homepage.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="File not found", status_code=404)

class TextRequest(BaseModel):
    text: str
#文本处理-生成文本
@app.post("/generate-draft")
async def generate_draft(request: TextRequest):
    user_input = request.text
    return await generate_draft_text(user_input)
    
#文本处理-存储断点
@app.post("/save_text")
async def save_text(request: TextRequest):
    original_text = request.text
    soup = BeautifulSoup(original_text, "html.parser")
    for span in soup.find_all("span", class_="cutscene-marker"):
        span.string = "*"  # 将 span 中的内容替换为 "*"
    modified_text = soup.get_text()
    try:
        file_path = "./static/data/output.txt"
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(modified_text)
        return {"message": f"文本已保存至 {file_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))  

#文本处理-获取切分文本
class SplitTextModel(BaseModel):
    mode: str
@app.post("/split_text", tags=["perfume bottle"])
async def split_text(data:SplitTextModel):
    file_path = './static/data/output.txt'
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not exist")
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as file:
        text_content = file.read()
    # logger.info(f"模式为：{data.mode}")
    split_result = await process_split_text(text_content,data)

# 文本处理-保存分镜数据
class SceneData(BaseModel): 
    scenes: dict
@app.post("/save-storyboard")
async def save_storyboard(scene_data: SceneData):
    file_path = "./static/data/storyboard.json"
    os.makedirs(os.path.dirname(file_path), exist_ok=True) 
    try:
        # print("Received data:", scene_data)
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(json.dumps(scene_data.dict(), indent=4, ensure_ascii=False))
        return {"success": True, "message": "文件保存成功"}
    except Exception as e:
        print(f"Error saving file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

#文本情感分析
class TextAnalysisRequest(BaseModel):
    text: str
@app.post("/analyze-text")
async def analyze_text(data: TextAnalysisRequest):
    text = data.text
    return await process_getemotion_text(data)

#文本情感分析-保存情感分析数据
class SaveAnalysisRequest(BaseModel):
    sceneIndex: str
    text: list
@app.post("/save-emotion-analysis")
async def save_analysis(data: SaveAnalysisRequest):
    file_path = "./static/data/emotion_analysis.json"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, 'r', encoding='utf-8') as file:
            analysis_data = json.load(file)
    else:
        analysis_data = {}  # 初始化为空对象
    analysis_data[data.sceneIndex] = data.text
    # 保存数据
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(analysis_data, file, ensure_ascii=False, indent=4)
    return {"message": "分析结果已保存"}

#文本生成语音
class TexttoSpeech(BaseModel):
    text: str
    emotion:str
    tts_char:str
    output_name:str
    savedLangValue:str
    savedCutValue:str
    savedVoiceSpeedValue:str
    savedVoiceTempValue:str
@app.post("/text-to-speech")
async def text_to_speech(data: TexttoSpeech):
    return await process_texttospeech(data)

# 移动并重命名音乐文件
class AudioFileRenameRequest(BaseModel):
    output_name: str# 获取语音文件
@app.post("/rename-audio-file")
async def get_audio_file(data: AudioFileRenameRequest):
    output_name = data.output_name
    directory = '../output/audio'
    new_file_path = './static/data/audio'
    if not os.path.exists(new_file_path):
        os.makedirs(new_file_path)
    files = os.listdir(directory)
    target_file = None
    for filename in files:
        basename = os.path.splitext(filename)[0]
        if basename == output_name:
            file_path = os.path.join(directory, filename)
            os.remove(file_path)
            logger.info(f"删除文件: {file_path}")
        else:
            target_file = filename
    if target_file:
        target_basename, target_ext = os.path.splitext(target_file)
        new_filename = f"{output_name}{target_ext}"
        old_file_path = os.path.join(directory, target_file)
        new_file_path_full = os.path.join(directory, new_filename)
        os.rename(old_file_path, new_file_path_full)
        logger.info(f"重命名文件: {old_file_path} -> {new_file_path_full}")
        # 复制文件到 new_file_path
        destination_path = os.path.join(new_file_path, new_filename)
        shutil.copy(new_file_path_full, destination_path)
        logger.info(f"复制文件: {new_file_path_full} -> {destination_path}")
        return {"fileName": new_filename}
    raise HTTPException(status_code=404, detail="文件未找到")

# 获取符合条件的音乐文件
class SelectedSceneIndex(BaseModel):
    selectedSceneIndex: str
@app.post("/get-audio-files")
async def get_audio_files(data: SelectedSceneIndex):
    selected_scene_index = data.selectedSceneIndex
    logger.info(f"获取音乐文件: {selected_scene_index}")
    AUDIO_FOLDER = './static/data/audio'
    if not os.path.exists(AUDIO_FOLDER):
        raise HTTPException(status_code=404, detail="音频文件夹未找到")
    audio_files = [
        file for file in os.listdir(AUDIO_FOLDER)
        if file.startswith(selected_scene_index + "_") and file.endswith('.flac')  # 可根据需要添加其他扩展名
    ]
    if not audio_files:
       audio_files = []
    # 自定义排序函数，按下划线后面的数字排序
    def sort_key(file_name):
        # 提取下划线后面的部分，并去掉 .flac 后缀
        number_part = file_name.split('_')[1].split('.')[0]
        return int(number_part)
    audio_files.sort(key=sort_key)
    return JSONResponse(content={"audio_files": audio_files})

#拼合音乐
class AudioFileCombineRequest(BaseModel):
    fileName: str
@app.post("/apply-audio-file")
async def apply_audio_file(data: AudioFileCombineRequest):
    fileName = data.fileName
    base_dir = "./static/data/audio"
    output_dir = "./static/data/audio"
    output_file_name = f"{output_dir}/{fileName}.flac"
    if not os.path.exists(base_dir):
        raise HTTPException(status_code=404, detail="音频文件夹未找到")
    try:
        audio_files = [
            file for file in os.listdir(base_dir)
            if file.startswith(fileName + "_") and file.endswith('.flac')  # 可根据需要添加其他扩展名
        ]
        if not audio_files:
            raise HTTPException(status_code=404, detail="未找到符合条件的音频文件")
        def sort_key(file_name):
            number_part = file_name.split('_')[1].split('.')[0]
            return int(number_part)
        # 按自定义排序函数排序
        audio_files.sort(key=sort_key)
        # 初始化一个空的音频段
        combined_audio = AudioSegment.empty()
        for audio_file in audio_files:
            audio_segment = AudioSegment.from_file(os.path.join(base_dir, audio_file))
            combined_audio += audio_segment
        # 保存拼接后的音频文件
        combined_audio.export(output_file_name, format="flac")
        return JSONResponse(content={"message": f"音频文件已成功合成并保存为 {output_file_name}", "fileName": fileName + ".flac","audio_files": audio_files})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#删除语音文件
class DeleteAudioFileRequest(BaseModel):
    fileName: str
@app.post("/delete-audio-file")
async def delete_audio_file(data: DeleteAudioFileRequest):
    file_path = os.path.join('./static/data/audio', data.fileName)
    logger.info(f"删除文件: {file_path}")
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"message": f"文件 {data.fileName} 已删除"}
    else:
        raise HTTPException(status_code=404, detail=f"文件 {data.fileName} 未找到")

#获取音乐长度
class GetAudioLengthRequest(BaseModel):
    fileName: str
@app.post("/get-audio-length")
async def get_audio_length(data: GetAudioLengthRequest):
    file_path = os.path.join('./static/data/audio', data.fileName)
    logger.info(f"获取文件长度: {file_path}")
    if os.path.exists(file_path):
        audio = AudioSegment.from_file(file_path)
        length = len(audio) / 1000  # 将毫秒转换为秒
        return {"length": length}
    else:
        raise HTTPException(status_code=404, detail="文件未找到")

#生成自定义动作-MotionDiffuser
class CustomMotionModel(BaseModel):
    motionoutputname: str
    motionGenPrompt: str
    motionLerp: int
    motionframe: int
@app.post("/generate-custommotion")
async def customMotion(data:CustomMotionModel):
    logger.info(f"生成自定义动作: {data.motionGenPrompt}")
    return await process_custommotion(data)

# 移动并重命名动作文件
class MotionFileRenameRequest(BaseModel):
    motionoutputname: str
    FloderName: str
@app.post("/renameandmove-motion-file")
async def rename_motion_file(data: MotionFileRenameRequest):
    motionoutputname = data.motionoutputname
    FloderName = data.FloderName
    directory = '../output/' + FloderName
    new_file_path = './static/data/' + FloderName
    if not os.path.exists(new_file_path):
        os.makedirs(new_file_path)
    files = os.listdir(directory)
    target_file = None
    audio_file = None
    for filename in files:
        if filename.endswith(".png"):
            os.remove(os.path.join(directory, filename))
        else:
            basename = os.path.splitext(filename)[0]
            if basename == motionoutputname:
                file_path = os.path.join(directory, filename)
                os.remove(file_path)
                logger.info(f"删除文件: {file_path}")
            else:
                if filename.endswith('-audio.mp4'):
                    audio_file = filename
                else:
                    target_file = filename
    # 如果同时存在带有 -audio.mp4 和不带 -audio.mp4 的文件，优先选择带有 -audio.mp4 的文件
    if audio_file:
        target_file = audio_file
    if target_file:
        target_basename, target_ext = os.path.splitext(target_file)
        new_filename = f"{motionoutputname}{target_ext}"
        old_file_path = os.path.join(directory, target_file)
        new_file_path_full = os.path.join(directory, new_filename)
        os.rename(old_file_path, new_file_path_full)
        logger.info(f"重命名文件: {old_file_path} -> {new_file_path_full}")
        # 复制文件到 new_file_path
        destination_path = os.path.join(new_file_path, new_filename)
        shutil.copy(new_file_path_full, destination_path)
        logger.info(f"复制文件: {new_file_path_full} -> {destination_path}")
        # 删除不带 -audio.mp4 的文件
        if audio_file and target_file != audio_file:
            non_audio_file_path = os.path.join(directory, target_file)
            os.remove(non_audio_file_path)
            logger.info(f"删除文件: {non_audio_file_path}")
        return {"fileName": new_filename}

#生成默认动作-EMAGE
class DefaultMotionModel(BaseModel):
    fileName: str
@app.post("/generate-defaultmotion")
async def defaultmotion(data:DefaultMotionModel):
    fileName = data.fileName
    logger.info(f"生成默认动作: {fileName}")
    return await process_defaultmotion(fileName)

# 生成角色渲染动作-Musepose
class CharRenderModel(BaseModel):
    fileName: str
    selectedCharValue: str
@app.post("/generate-charrender")
async def charrender(data: CharRenderModel):
    fileName = data.fileName
    selectedCharValue = data.selectedCharValue
    logger.info(f"生成角色渲染动作: {fileName}")
    return await process_charrender(data)


# 获取文件夹中所有动作文件
class GetMotionFiles(BaseModel):
    selectedSceneIndex: str
    folderName: str
@app.post("/get-motion-files")
async def get_motion_files(data: GetMotionFiles):
    selected_scene_index = data.selectedSceneIndex
    MOTION_FOLDER = './static/data/'+data.folderName
    logger.info(f"MOTION_FOLDER: {MOTION_FOLDER}")
    if not os.path.exists(MOTION_FOLDER):
        raise HTTPException(status_code=404, detail="动作文件夹未找到")
    motion_files = [
        motion for motion in os.listdir(MOTION_FOLDER)
        if motion.startswith(selected_scene_index + "_") and motion.endswith('.mp4') and '.' not in motion[:-4] # 可根据需要添加其他扩展名
    ]
    if not motion_files:
        motion_files=[]
    # 自定义排序函数，按下划线后面的数字排序
    def sort_key(file_name):
        # 提取下划线后面的部分，并去掉 .mp4 后缀
        number_part = file_name.split('_')[1].split('.')[0]
        return int(number_part)
    motion_files.sort(key=sort_key)
    return JSONResponse(content={"motion_files": motion_files})

#视频拼合与帧插值
class MotionMergeModel(BaseModel):
    selectedSceneIndex: str
    selectedCharValue: str
@app.post("/motion-apply")
async def motion_merge(data: MotionMergeModel):
    selectedSceneIndex = data.selectedSceneIndex
    selectedCharValue = data.selectedCharValue
    MOTION_FOLDER = './static/data/char_video'
    TEMP_FOLDER = os.path.join(MOTION_FOLDER, 'temp')
    if not os.path.exists(MOTION_FOLDER):
        raise HTTPException(status_code=404, detail="动作文件夹未找到")
    motion_files = [
        motion for motion in os.listdir(MOTION_FOLDER)
        if motion.startswith(selectedSceneIndex + "_") and motion.endswith('.mp4') and '.' not in motion[:-4]
    ]
    if not motion_files:
        raise HTTPException(status_code=404, detail="未找到符合条件的动作文件")
    # 自定义排序函数，按下划线后面的数字排序
    def sort_key(file_name):
        # 提取下划线后面的部分，并去掉 .flac 后缀
        number_part = file_name.split('_')[1].split('.')[0]
        return int(number_part)
    motion_files.sort(key=sort_key)
    print("motion_files:"+str(motion_files))
    # 帧插值
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
    for i in range(len(motion_files) - 1):
        current_video_path = os.path.join(MOTION_FOLDER, motion_files[i])
        next_video_path = os.path.join(MOTION_FOLDER, motion_files[i + 1])
        # 获取当前视频的最后一帧
        current_video = cv2.VideoCapture(current_video_path)
        total_frames = int(current_video.get(cv2.CAP_PROP_FRAME_COUNT))
        current_video.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
        ret, frame = current_video.read()    
        if ret:
            cv2.imwrite(os.path.join(TEMP_FOLDER, '0.png'), frame)
        current_video.release()            
        # 获取下一个视频的第一帧
        next_video = cv2.VideoCapture(next_video_path)
        ret, frame = next_video.read()
        if ret:
            cv2.imwrite(os.path.join(TEMP_FOLDER, '1.png'), frame)
        next_video.release()
        startfile = os.path.basename(current_video_path)
        endfile = os.path.basename(next_video_path)
        # 生成outputname
        start_suffix = startfile.split('_')[1].split('.')[0]
        end_suffix = endfile.split('_')[1].split('.')[0]
        outputname = f"{selectedSceneIndex}_{start_suffix}.{end_suffix}"                     
        # 运行插帧函数
        result =  await interpolate_frames(outputname)
        if result:
            logger.info(f"{outputname} 帧插值完成")
            # 调用 rename_motion_file 函数
            rename_request = MotionFileRenameRequest(motionoutputname=outputname,FloderName="char_video")
            rename_response = await rename_motion_file(rename_request)
            if rename_response:
                logger.info(f"{outputname} 重命名完成")
            else:
                logger.error(f"{outputname} 重命名失败")
        # 删除临时文件夹中的内容
        for file_name in os.listdir(TEMP_FOLDER):
            file_path = os.path.join(TEMP_FOLDER, file_name)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.error(f"Failed to delete {file_path}. Reason: {e}")
    # 删除临时文件夹
    shutil.rmtree(TEMP_FOLDER)
    # 视频拼合
    merge_motion_files = [
        motion for motion in os.listdir(MOTION_FOLDER)
        if motion.startswith(selectedSceneIndex + "_") and motion.endswith('.mp4')
    ]
    merge_motion_files.sort(key=sort_key)
    print("merge_motion_files:" + str(merge_motion_files))
    if not merge_motion_files:
        raise HTTPException(status_code=404, detail="未找到需要拼合的视频文件")

    clips = [VideoFileClip(os.path.join(MOTION_FOLDER, file)) for file in merge_motion_files]
    final_clip = concatenate_videoclips(clips)

    # 修改拼合视频的文件名
    final_video_name = f"{selectedSceneIndex}-{selectedCharValue}.mp4"
    final_clip.write_videofile(os.path.join(MOTION_FOLDER, final_video_name), codec='libx264')

    return JSONResponse(content={"status": "success", "message": "视频拼合完成", "fileName": final_video_name})

#删除冗余数据
class DeleteMotiondataModel(BaseModel):
    selectedSceneIndex: str
@app.post("/delete-motion-data")
async def delete_motion_data(data: DeleteMotiondataModel):
    selectedSceneIndex = data.selectedSceneIndex
    # 删除拼合前的视频文件
    MOTION_FOLDER = './static/data/char_video'
    merge_motion_files=[
        motion for motion in os.listdir(MOTION_FOLDER)
        if motion.startswith(selectedSceneIndex + "_") and motion.endswith('.mp4')
    ]
    for file in merge_motion_files:
        file_path = os.path.join(MOTION_FOLDER, file)
        try:
            os.unlink(file_path)
            logger.info(f"删除文件: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete {file_path}. Reason: {e}")
    #删除motion-pre对应的文件
    MOTION_PRE_FOLDER = './static/data/motion-pre'
    motionpre_files=[
        motion for motion in os.listdir(MOTION_PRE_FOLDER)
        if motion.startswith(selectedSceneIndex + "_") and motion.endswith('.mp4')
    ]
    for file in motionpre_files:
        file_path = os.path.join(MOTION_PRE_FOLDER, file)
        try:
            os.unlink(file_path)
            logger.info(f"删除文件: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete {file_path}. Reason: {e}")

    #删除motion对应的文件
    MOTIONFOLDER = './static/data/motion'
    motionfiles=[
        motion for motion in os.listdir(MOTIONFOLDER)
        if motion.startswith(selectedSceneIndex + "_") and motion.endswith('.mp4')
    ]
    for file in motionfiles:
        file_path = os.path.join(MOTIONFOLDER, file)
        try:
            os.unlink(file_path)
            logger.info(f"删除文件: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete {file_path}. Reason: {e}")
    # #删除audio对应的文件
    # AUDIO_FOLDER = './static/data/audio'
    # audio_files=[
    #     audio for audio in os.listdir(AUDIO_FOLDER)
    #     if audio.startswith(selectedSceneIndex + "_") and audio.endswith('.flac')
    # ]
    # for file in audio_files:
    #     file_path = os.path.join(AUDIO_FOLDER, file)
    #     try:
    #         os.unlink(file_path)
    #         logger.info(f"删除文件: {file_path}")
    #     except Exception as e:
    #         logger.error(f"Failed to delete {file_path}. Reason: {e}")
    return JSONResponse(content={"status": "success", "message": "删除成功"})


#口型匹配
class WavtoLipModel(BaseModel):
    fileName: str
    bbox_shift:int
    batchsize:int
@app.post("/wavtolip")
async def wavtolip(data: WavtoLipModel):
    logger.info("开始口型匹配:"+data.fileName)
    return await process_wavtolip(data)

#移除背景
class RemoveBGRequest(BaseModel):
    selectedSceneIndex: str
    selectedCharValue: str
@app.post("/remove-bgtowebm")
async def remove_bg_to_webm(request: RemoveBGRequest):
    selectedSceneIndex = request.selectedSceneIndex
    selectedCharValue = request.selectedCharValue.split(".")[0]
    folder_name = "./static/data/char_video"
    video_name = selectedSceneIndex + "-" + selectedCharValue + ".mp4"
    video_path = os.path.join(folder_name, video_name)
    logger.info("开始移除背景:"+video_path)
    basename = os.path.splitext(video_name)[0]
    sh_script_path = "/root/autodl-tmp/ComfyUI/demo/runRMBG.sh"
    try:
        result = subprocess.run(
            [sh_script_path, basename, folder_name],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print(result.stdout.decode())
    except subprocess.CalledProcessError as e:
        print(e.stderr.decode())
        raise HTTPException(status_code=500, detail="Error executing sh script")
    # 删除MP4文件
    try:
        os.remove(video_path)
        print(f"Deleted file: {video_path}")
    except Exception as e:
        print(f"Error deleting file: {video_path}, {e}")
        raise HTTPException(status_code=500, detail="Error deleting MP4 file")

    return JSONResponse(content={"message": "Background removed and MP4 file deleted"}, status_code=200)    
#获取Lora模型列表
@app.get("/get_lora_list", response_class=JSONResponse)
async def get_lora_list():
    directory_path = "../models/loras"
    if not os.path.exists(directory_path):
        raise HTTPException(status_code=404, detail=f"Directory {directory_path} not found")
    try:
        all_files = os.listdir(directory_path)
        # 筛选出以 .safetensors 结尾的文件
        lora_models = [file for file in all_files if file.endswith('.safetensors')]
        return {"lora_models": lora_models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#文本生成图片-flux-无参考
class TextToImageModel(BaseModel):
    prompt: str
    selectedFileName: str
    baseStyle: str
    loraModel: str
    width: int
    height: int
    removebgornot: int
@app.post("/generate_img")
async def generate_img(data: TextToImageModel):
    try:
        data = await process_generateimgflux(data)
        return data
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return {"error": str(e)}

#文本生成图片-flux-CN
class TextToImageWithCNModel(BaseModel):
    prompt: str
    selectedFileName: str
    InputRefName: str
    baseStyle: str
    loraModel: str
    CN_index: int
    WeightValue: float
    removebgornot: int
@app.post("/generate_img_with_cn")
async def generate_img_with_cn(data: TextToImageWithCNModel):
    return await process_generateimgflux_with_cn(data)

#文本生成图片-flux-IPA
class TextToImageWithIPAModel(BaseModel):
    prompt: str
    InputRefName: str
    removebgornot: int
    WeightValue: float
@app.post("/generate_img_with_ipa")
async def generate_img_with_ipa(data: TextToImageWithIPAModel):
    return await process_generateimgflux_with_ipa(data)  

#图片生成动画-CogVideo
class CogVideoModel(BaseModel):
    inputFile: str
    frame:int
    Inputtext:str
    removebgornot:int
@app.post("/generate_animation")
async def generate_animation(data: CogVideoModel):
    return await process_generate_animation(data)

#上传参考图到本地
@app.post("/upload-ref-image")
async def upload_image(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIRECTORY, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"message": f"文件已保存至 {file_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SaveImageRequest(BaseModel):
    imageUrl: str
    fileName: str
    FloderName: str
#保存生成图片
@app.post("/save_gen_image")
async def save_gen_image(request: SaveImageRequest):
    save_path = "./static/data/" + request.FloderName
    try:
        os.makedirs(save_path, exist_ok=True)
        # 下载图片
        response = requests.get(request.imageUrl, stream=True)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download image")
        
        # 获取文件扩展名
        content_type = response.headers.get('Content-Type')
        if 'image/png' in content_type:
            file_extension = ".png"
        elif 'image/gif' in content_type:
            file_extension = ".gif"
        elif 'image/jpeg' in content_type:
            file_extension = ".jpg"
        else:
            raise HTTPException(status_code=400, detail="Unsupported image format")
        
        # 构建保存路径
        save_filename = f"{request.fileName}{file_extension}"
        save_full_path = os.path.join(save_path, save_filename)
        
        # 保存文件
        with open(save_full_path, 'wb') as file:
            shutil.copyfileobj(response.raw, file)
        
        return {"message": "Image saved successfully", "filename": save_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'response' in locals() and response:
            response.close()

#获取文件夹中所有生成的图片
class GetImageRequest(BaseModel):
    FloderName: str
@app.post("/get_gen_image")
async def get_gen_image(request: GetImageRequest):
    FloderName = request.FloderName
    directory = './static/data/' + FloderName
    if not os.path.exists(directory):
        raise HTTPException(status_code=404, detail="文件夹未找到")
    try:
        image_files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        return {"files": image_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#删除生成的文件
class DeleteImageFileRequest(BaseModel):
    FloderName: str
    fileName: str
@app.post("/delete-image-file")
async def delete_audio_file(data: DeleteImageFileRequest):
    FloderName = data.FloderName
    fileName = data.fileName
    directory = './static/data/' + FloderName
    file_path = os.path.join(directory, fileName)
    logger.info(f"删除文件: {file_path}")
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"message": f"文件 {data.fileName} 已删除"}
    else:
        raise HTTPException(status_code=404, detail=f"文件 {data.fileName} 未找到")

#保存json数据
class SaveJosnDataModel(BaseModel):
    Jsondata: dict
    fileName: str
@app.put("/save-json-data")
async def save_json_data(data: SaveJosnDataModel):
    file_path = os.path.join('./static/data/', data.fileName)
    try:
        with open(file_path, "w") as json_file:
            json.dump(data.Jsondata, json_file, ensure_ascii=False, indent=4)
        return {"message": f"JSON data saved to {file_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#读取josn数据
class ReadJosnDataModel(BaseModel):
    fileName: str
@app.post("/read-json-data")
async def read_json_data(data: ReadJosnDataModel):
    file_path = os.path.join('./static/data/', data.fileName)
    with open(file_path, "r") as json_file:
        json_data = json.load(json_file)
    return json_data

#获取生成的角色视频列表
class GetCharVideoRequest(BaseModel):
    selectedSceneIndex: str
@app.post("/get_genchar_video")
async def get_gen_video(data: GetCharVideoRequest):
    selectedSceneIndex = data.selectedSceneIndex
    directory = './static/data/char_video'
    if not os.path.exists(directory):
        raise HTTPException(status_code=404, detail="文件夹未找到")
    try:
        # 只获取以 selectedSceneIndex + "-" 开头的视频文件
        video_files = [
            f for f in os.listdir(directory)
            if os.path.isfile(os.path.join(directory, f)) and f.startswith(selectedSceneIndex + "-") and f.endswith('.webm')
        ]
        return {"files": video_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取视频文件时出错: {str(e)}")


# # 视频合成
# @app.post("/export_video")
# async def export_video(request: Request):
#     data = await request.json()
#     layers = data.get('layers', [])
#     selected_scene_index = data.get('selectedSceneIndex', None)
#     if selected_scene_index is None:
#         raise HTTPException(status_code=400, detail="selectedSceneIndex is required")
#     # 筛选出指定scene的素材
#     selected_layers = [layer for layer in layers if layer['scene'] == selected_scene_index]
#     if not selected_layers:
#         raise HTTPException(status_code=400, detail="No layers found for the selected scene index")
#     # 按照 layerIndex 排序，layerIndex 越大，越在最前面
#     selected_layers.sort(key=lambda x: x['layerIndex'], reverse=False)
#     logger.info(f"selected_layers: {selected_layers}")
#     # 源分辨率和目标分辨率
#     source_width = 480
#     source_height = 270
#     target_width = 1920
#     target_height = 1080
#     # 计算缩放因子
#     scale_x = target_width / source_width
#     scale_y = target_height / source_height
#     video_clips = []
#     audio_clips = []
#     clips = []  # 初始化 clips 列表

#     for layer in selected_layers:
#         try:
#             position = {
#                 'top': float(layer['position']['top'].replace('px', '')) * scale_y,
#                 'left': float(layer['position']['left'].replace('px', '')) * scale_x
#             }
#             size = {
#                 'width': float(layer['size']['width'].replace('px', '')) * scale_x,
#                 'height': float(layer['size']['height'].replace('px', '')) * scale_y
#             }
#             # 解析旋转角度
#             transform = layer['transform']
#             if 'rotate' in transform:
#                 rotate_angle = float(transform.split('(')[1].split('deg')[0])
#             else:
#                 rotate_angle = 0

#             if layer['type'] == 'video':
#                 video_clip = VideoFileClip(layer['src'])
#                 video_clips.append(video_clip)
#                 if video_clip.audio:
#                     audio_clips.append(video_clip.audio)
#                 clip = video_clip
#             elif layer['type'] == 'image':
#                 image_clip = ImageClip(layer['src'])
#                 clip = image_clip

#             clips.append((clip, position, size, rotate_angle))
#         except Exception as e:
#             logger.error(f"Failed to process clip from {layer['src']}: {e}")
#             raise HTTPException(status_code=500, detail=f"Failed to process clip from {layer['src']}")

#     if not clips:
#         logger.error("No clips added to final video")
#         raise HTTPException(status_code=400, detail="No clips added to final video")

#     # 计算最大时长
#     if video_clips:
#         max_duration = np.max([clip.duration for clip in video_clips])
#         video_audio_clips = [clip.audio for clip in video_clips if clip.audio]
#         if video_audio_clips:
#             final_audio = concatenate_audioclips(video_audio_clips)
#         else:
#             final_audio = None
#     else:
#         # 获取音频文件路径
#         audio_filepath = './static/data/audio'
#         audio_files = [f for f in os.listdir(audio_filepath) if f.startswith(f"{selected_scene_index}_")]
#         for audio_file in audio_files:
#             audio_clip = AudioFileClip(os.path.join(audio_filepath, audio_file))
#             audio_clips.append(audio_clip)
#         if not audio_clips:
#             raise HTTPException(status_code=400, detail="No video or audio files found for the selected scene index")
#         final_audio = concatenate_audioclips(audio_clips)
#         max_duration = final_audio.duration

#     logger.info(f"max_duration: {max_duration}")

#     # 设置所有剪辑的属性
#     final_clips = []
#     for clip, position, size, rotate_angle in clips:
#         clip = clip.set_duration(max_duration)
#         clip = clip.set_position((position['left'], position['top']))
#         clip = clip.resize(newsize=(int(size['width']), int(size['height'])))
#         clip = clip.rotate(rotate_angle)
#         final_clips.append(clip)

#     # 创建最终的视频剪辑
#     final_clip = CompositeVideoClip(final_clips, size=(target_width, target_height)).set_duration(max_duration)

#     # 设置音频
#     if final_audio:
#         final_clip = final_clip.set_audio(final_audio)

#     # 保存最终的视频
#     output_path = f"./static/data/final_video/{selected_scene_index}.mp4"
#     os.makedirs(os.path.dirname(output_path), exist_ok=True)
#     final_clip.write_videofile(output_path, codec='libx264')
#     return JSONResponse(content={"url": output_path})

def move_and_find_latest_audio(description: str, source_dir: str, target_dir: str):
    os.makedirs(target_dir, exist_ok=True)
    safe_description = re.sub(r'[<>:"/\\|\?\*\s,，,、]', '_', description)
    logger.info(f"Searching in {source_dir} for pattern: {safe_description}_.*\.flac")

    matched_files = []
    for filename in os.listdir(source_dir):
        if filename.startswith(f"{safe_description}_") and filename.endswith(".flac"):
            # 提取数字部分（尽可能提取）
            match = re.search(rf"{re.escape(safe_description)}_(\d+)", filename)
            number = int(match.group(1)) if match else -1
            matched_files.append((number, filename))

    logger.info(f"Matched files: {matched_files}")
    
    if not matched_files:
        return None

    # 找出最大数字对应的文件
    matched_files.sort(reverse=True, key=lambda x: x[0])
    latest_number, latest_filename = matched_files[0]

    src_path = os.path.join(source_dir, latest_filename)
    dst_path = os.path.join(target_dir, latest_filename)

    if os.path.exists(dst_path):
        os.remove(dst_path)

    shutil.move(src_path, dst_path)
    logger.info(f"Moved file: {src_path} -> {dst_path}")

    return f"data/music/{latest_filename}"

#生成背景音乐
class GenerateMusicRequest(BaseModel):
    description: str
    duration: float
@app.post("/generate_music")
async def generate_music(data: GenerateMusicRequest):
    description = data.description
    duration = data.duration
    logger.info(f"生成背景音乐: {description}, 时长: {duration}")
    await process_generate_music(description, duration)
    logger.info("背景音乐生成完成")
    # 源目录和目标目录
    source_dir = "../output/music"
    target_dir = "./static/data/music"
    result_path = move_and_find_latest_audio(description, source_dir, target_dir)
    # 返回最新的文件路径
    if result_path:
        return JSONResponse(content={"audio_url": result_path})
    else:
        raise HTTPException(status_code=404, detail="未找到匹配的音频文件")


#导出视频合成
@app.post("/export_video")
async def export_video(request: Request):
    data = await request.json()
    layers = data.get('layers', [])
    selected_scene_index = data.get('selectedSceneIndex', None)
    if selected_scene_index is None:
        raise HTTPException(status_code=400, detail="selectedSceneIndex is required")
    # 筛选出指定scene的素材
    selected_layers = [layer for layer in layers if layer['scene'] == selected_scene_index]
    if not selected_layers:
        raise HTTPException(status_code=400, detail="No layers found for the selected scene index")
    # 按照 layerIndex 排序，layerIndex 越大，越在最前面
    selected_layers.sort(key=lambda x: x['layerIndex'], reverse=False)
    logger.info(f"selected_layers: {selected_layers}")
    # 源分辨率和目标分辨率
    source_width = 480
    source_height = 270
    target_width = 1920
    target_height = 1080
    # 计算缩放因子
    scale_x = target_width / source_width
    scale_y = target_height / source_height
    video_clips = []
    audio_clips = []
    clips = []  # 初始化 clips 列表
    # 计算最大时长
    for layer in selected_layers:
        if layer['type'] == 'video':
            video_clip = VideoFileClip(layer['src'])
            video_clips.append(video_clip)
            if video_clip.audio:
                audio_clips.append(video_clip.audio)
    if video_clips:
        max_duration = np.max([clip.duration for clip in video_clips])
        video_audio_clips = [clip.audio for clip in video_clips if clip.audio]
        if video_audio_clips:
            final_audio = concatenate_audioclips(video_audio_clips)
        else:
            final_audio = None
    else:
        # 获取音频文件路径
        audio_filepath = './static/data/audio'
        audio_files = [f for f in os.listdir(audio_filepath) if f.startswith(f"{selected_scene_index}_")]
        for audio_file in audio_files:
            audio_clip = AudioFileClip(os.path.join(audio_filepath, audio_file))
            audio_clips.append(audio_clip)
        if not audio_clips:
            raise HTTPException(status_code=400, detail="No video or audio files found for the selected scene index")
        final_audio = concatenate_audioclips(audio_clips)
        max_duration = final_audio.duration

    logger.info(f"max_duration: {max_duration}")

    # 处理所有的素材，包括 GIF 图片
    for layer in selected_layers:
        try:
            position = {
                'top': float(layer['position']['top'].replace('px', '')) * scale_y,
                'left': float(layer['position']['left'].replace('px', '')) * scale_x
            }
            size = {
                'width': float(layer['size']['width'].replace('px', '')) * scale_x,
                'height': float(layer['size']['height'].replace('px', '')) * scale_y
            }
            
            # 解析旋转角度
            transform = layer['transform']
            if 'rotate' in transform:
                rotate_angle = float(transform.split('(')[1].split('deg')[0])
            else:
                rotate_angle = 0

            if layer['type'] == 'video':
                if layer['src'].endswith('.webm'):
                    # 替换 .webm 为 .gif
                    gif_file = layer['src'].replace('.webm', '.gif')
                    gif_clip = VideoFileClip(gif_file, has_mask=True)
                    gif_fps = gif_clip.fps
                    gif_clip = gif_clip.set_fps(gif_fps)
                    clip = gif_clip
                    # 处理音频
                    video_clip = VideoFileClip(layer['src'])
                    if video_clip.audio:
                        audio_clips.append(video_clip.audio)
                else:
                    video_clip = VideoFileClip(layer['src'])
                    video_clips.append(video_clip)
                    if video_clip.audio:
                        audio_clips.append(video_clip.audio)
                    clip = video_clip
            elif layer['type'] == 'image':
                # 如果是 GIF 格式
                if layer['src'].endswith('.gif'):
                    gif_file = layer['src']
                    gif_clip = VideoFileClip(gif_file, has_mask=True)
                    gif_fps = gif_clip.fps
                    gif_clip = gif_clip.set_fps(gif_fps)
                    # 计算需要的重复次数来实现循环
                    loop_count = int(max_duration / gif_clip.duration) + 1
                    gif_clip = concatenate_videoclips([gif_clip] * loop_count)
                    gif_clip = gif_clip.subclip(0, max_duration)  # 截取到最大时长
                    clip = gif_clip
                else:
                    image_clip = ImageClip(layer['src'])
                    clip = image_clip

            clips.append((clip, position, size, rotate_angle))
        except Exception as e:
            logger.error(f"Failed to process clip from {layer['src']}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to process clip from {layer['src']}")

    # 设置所有剪辑的属性
    final_clips = []
    for clip, position, size, rotate_angle in clips:
        clip = clip.set_duration(max_duration)
        clip = clip.set_position((position['left'], position['top']))
        clip = clip.resize(newsize=(int(size['width']), int(size['height'])))
        clip = clip.rotate(rotate_angle)
        final_clips.append(clip)

    # 创建最终的视频剪辑
    final_clip = CompositeVideoClip(final_clips, size=(target_width, target_height)).set_duration(max_duration)

    # 设置音频
    if final_audio:
        final_clip = final_clip.set_audio(final_audio)

    # 保存最终的视频
    output_path = f"./static/data/final_video/{selected_scene_index}.mp4"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_clip.write_videofile(output_path, codec='libx264', fps=24)
    # 获取视频的第一帧
    video_capture = cv2.VideoCapture(output_path)
    success, frame = video_capture.read()

    if success:
        # 定义同名的 PNG 图片路径
        first_frame_path = os.path.splitext(output_path)[0] + ".png"
        # 保存第一帧为 PNG 文件
        cv2.imwrite(first_frame_path, frame)
        logger.info(f"视频首帧已保存至: {first_frame_path}")

    # 释放 VideoCapture 对象
    video_capture.release()
    return JSONResponse(content={"url": output_path})


import tempfile
import uuid
from fastapi.responses import StreamingResponse
from urllib.parse import unquote
from moviepy.editor import CompositeAudioClip
#保存bgm
class SaveBGMRequest(BaseModel):
    src_filename: str  # 原始文件名，如 music_001.flac
    dest_filename: str = "bgm.flac"  # 目标文件名，默认为 bgm.flac
@app.post("/save-bgm")
async def save_bgm(request: SaveBGMRequest):
    # ✅ 使用 unquote 解码文件名
    src_filename = unquote(request.src_filename)
    dest_filename = request.dest_filename
    src_path = os.path.join("./static/data/music", src_filename)
    dest_path = os.path.join("./static/data/music", dest_filename)
    if not os.path.exists(src_path):
        raise HTTPException(status_code=404, detail=f"源文件 {request.src_filename} 不存在")
    try:
        if os.path.exists(dest_path):
            os.remove(dest_path)

        shutil.copyfile(src_path, dest_path)
        return {"message": f"{dest_filename} 已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


# 导出视频
class ExportVideoRequest(BaseModel):
    export_name: str
    resolution: str

@app.post("/export-video")
async def export_video(request: ExportVideoRequest):
    input_dir = "./static/data/final_video"
    output_dir = "./static/data/exported"

    os.makedirs(output_dir, exist_ok=True)

    resolutions = {
        "480p": (854, 480),
        "720p": (1280, 720),
        "1080p": (1920, 1080)
    }
    if request.resolution not in resolutions:
        raise HTTPException(status_code=400, detail="不支持的分辨率")

    target_size = resolutions[request.resolution]

    video_files = [f for f in os.listdir(input_dir) if f.endswith(".mp4")]
    if not video_files:
        raise HTTPException(status_code=404, detail="未找到任何视频文件")

    try:
        video_files.sort(key=lambda x: int(os.path.splitext(x)[0]))
    except Exception as e:
        raise HTTPException(status_code=400, detail="文件名必须为纯数字.mp4格式")

    clips = []
    for filename in video_files:
        file_path = os.path.join(input_dir, filename)
        try:
            clip = VideoFileClip(file_path).resize(target_size)
            clips.append(clip)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"加载视频失败: {filename}")

    # Step 1: 拼接视频片段
    final_clip = concatenate_videoclips(clips)

    # Step 2: 提取整个视频的原声音轨
    original_audio = final_clip.audio

    # Step 3: 加载 BGM 并调整音量
    bgm_path = "./static/data/music/bgm.flac"
    bgm = None
    if os.path.exists(bgm_path):
        logger.info("检测到 BGM 文件，正在叠加进视频...")
        bgm = AudioFileClip(bgm_path).volumex(0.5)

    # Step 4: 合并原声与 BGM
    final_audio = None
    if original_audio and bgm:
        final_audio = CompositeAudioClip([original_audio, bgm])
    elif original_audio:
        final_audio = original_audio
    elif bgm:
        final_audio = bgm
    else:
        logger.warning("没有可用音频轨道")

    # Step 5: 设置合成后的音频轨道
    if final_audio:
        final_clip = final_clip.set_audio(final_audio)

    # Step 6: 导出最终视频
    temp_dir = tempfile.gettempdir()
    unique_id = str(uuid.uuid4())
    temp_output_path = os.path.join(temp_dir, f"{unique_id}_{request.export_name}.mp4")

    try:
        final_clip.write_videofile(temp_output_path, codec="libx264", audio_codec="aac")
    except Exception as e:
        raise HTTPException(status_code=500, detail="视频合成失败")

    def iterfile():
        with open(temp_output_path, mode="rb") as f:
            while chunk := f.read(1024 * 1024):  # 1MB chunks
                yield chunk
        os.remove(temp_output_path)  # 清理临时文件

    headers = {
        'Content-Disposition': f'attachment; filename="{request.export_name}.mp4"'
    }

    return StreamingResponse(iterfile(), media_type="video/mp4", headers=headers)
#文生图
# class TextToImageModel(BaseModel):
#     prompt: str
#     selectedFileName: str
#     queuesize: int
#     batchsize:int
# @app.post("/generate_img", tags=["perfume bottle"])
# async def generate_img(data:TextToImageModel):
#     logger.info(f"批次为：{data.queuesize}")
#     # logger.info(await process_generateimg(data,batch_size))
#     return await process_generateimg(data,data.queuesize)

# 图生图
class ImgToImgModel(BaseModel):
    imagename: str
    prompt: str
    selectedFileName: str
    queuesize: int
    batchsize:int
@app.post("/imgGenerateImg", tags=["perfume bottle"])
async def imgGenerateImg(
    prompt: str = Form(...),
    selectedFileName: str = Form(...),
    queuesize: int = Form(...),
    batchsize: int = Form(...),
    file: UploadFile = File(...)
):
    # 获取上传的图片文件名
    imagename = file.filename
    logger.info(f"Received image name: {imagename}")
    file_location = os.path.join(UPLOAD_DIRECTORY, imagename)
    # 复制上传的文件至../input 目录
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)   
    logger.info(f"Saved uploaded image: {file_location}")
    # 创建 ImgToImgModel 实例
    data = ImgToImgModel(
        imagename=imagename,
        prompt=prompt,
        selectedFileName=selectedFileName,
        queuesize=queuesize,
        batchsize=batchsize
    )
    return await process_imggenerateimg(data,data.queuesize)

#获取模型文件列表
@app.get("/get_file_list", response_class=JSONResponse)
async def get_file_list():
    directory_path = "../models/checkpoints"
    if not os.path.exists(directory_path):
        return {"detail": f"Directory {directory_path} not found"}
    try:
        files = os.listdir(directory_path)
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# cd /root/autodl-tmp/ComfyUI/demo
# 运行命令：uvicorn api:app --reload

#删除数据
def clear_folder_contents(folder_path: str):
    """
    清空指定文件夹内容，但保留该文件夹。
    参数:
        folder_path (str): 文件夹路径
    """
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail=f"路径 {folder_path} 不存在")

    if not os.path.isdir(folder_path):
        raise HTTPException(status_code=400, detail=f"{folder_path} 不是一个文件夹")

    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isfile(item_path) or os.path.islink(item_path):
            os.remove(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
def clear_json_file_content(file_path: str):
    """
    清空指定 JSON 文件的内容，但保留该文件。
    参数:
        file_path (str): JSON 文件路径
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"文件 {file_path} 不存在")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            # 如果是 Material_data.json，则写入 {"0": []}
            if "Material_data.json" in file_path:
                f.write('{"0": []}')
            else:
                f.write("{}")  # 默认清空内容为 {}
        logger.info(f"已清空 JSON 文件内容: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"无法清空文件 {file_path}: {str(e)}")


class ClearFolderRequest(BaseModel):
    option: str
@app.post("/clear-folders")
async def clear_folders(request: ClearFolderRequest):
    option = request.option
    base_dir = "/root/autodl-tmp/ComfyUI"

    # 需要清空内容的 JSON 文件列表
    json_files_to_clear = [
        os.path.join(base_dir, "demo/static/data/emotion_analysis.json"),
        os.path.join(base_dir, "demo/static/data/Material_data.json"),
        os.path.join(base_dir, "demo/static/data/storyboard.json"),
        os.path.join(base_dir, "demo/static/data/textsplit.json"),
    ]

    all_folders = [ 
        os.path.join(base_dir, "demo/static/data/music"),
        os.path.join(base_dir, "demo/static/data/audio"),
        os.path.join(base_dir, "demo/static/data/motion-pre"),
        os.path.join(base_dir, "demo/static/data/motion"),
        os.path.join(base_dir, "demo/static/data/char_video"),
        os.path.join(base_dir, "demo/static/data/final_video"),
        os.path.join(base_dir, "output/music"),
        os.path.join(base_dir, "output/audio"),
        os.path.join(base_dir, "output/motion-pre"),
        os.path.join(base_dir, "output/motion"),
        os.path.join(base_dir, "output/char_video"),
    ]

    comfyui_folders = [
        os.path.join(base_dir, "output/music"),
        os.path.join(base_dir, "output/audio"),
        os.path.join(base_dir, "output/motion-pre"),
        os.path.join(base_dir, "output/motion"),
        os.path.join(base_dir, "output/char_video"),
    ]

    if option == "all":
        logger.info("开始清空所有文件夹内容")
        target_folders = all_folders
    elif option == "comfyui":
        logger.info("开始清空ComfyUI相关文件夹内容")
        target_folders = comfyui_folders
    else:
        raise HTTPException(status_code=400, detail="无效的选项")

    deleted_paths = []
    
    # 清空文件夹内容
    for folder in target_folders:
        try:
            clear_folder_contents(folder)
            deleted_paths.append(folder)
        except Exception as e:
            return {"error": f"在处理路径 {folder} 时出错: {str(e)}"}

    # 清空 JSON 文件内容
    for json_file in json_files_to_clear:
        try:
            clear_json_file_content(json_file)
            deleted_paths.append(json_file)
        except Exception as e:
            return {"error": f"在处理文件 {json_file} 时出错: {str(e)}"}

    return {"message": f"已根据选项 `{option}` 清空以下文件夹和 JSON 文件内容", "paths_cleared": deleted_paths}
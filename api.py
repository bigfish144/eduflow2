from fastapi import FastAPI, HTTPException
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
import moviepy
from moviepy.editor import VideoFileClip, concatenate_videoclips
# 配置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# UPLOAD_DIRECTORY = "./uploaded_videos"
# if not os.path.exists(UPLOAD_DIRECTORY):
#     os.makedirs(UPLOAD_DIRECTORY)
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
#试图打开位于"./static/index.html"路径下的HTML文件
@app.get("/", response_class=HTMLResponse)
def read_root():
    file_path = os.path.join("static", "homepage.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="File not found", status_code=404)

#文本处理-存储断点
class TextRequest(BaseModel):
    text: str
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
    try:
        audio_files = [
            file for file in os.listdir(AUDIO_FOLDER)
            if file.startswith(selected_scene_index + "_") and file.endswith('.flac')  # 可根据需要添加其他扩展名
        ]
        if not audio_files:
            raise HTTPException(status_code=404, detail="未找到符合条件的音频文件")
        # 自定义排序函数，按下划线后面的数字排序
        def sort_key(file_name):
            # 提取下划线后面的部分，并去掉 .flac 后缀
            number_part = file_name.split('_')[1].split('.')[0]
            return int(number_part)
        audio_files.sort(key=sort_key)
        return JSONResponse(content={"audio_files": audio_files})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

#生成自定义动作
class CustomMotionModel(BaseModel):
    selectedCharValue: str
    motionoutputname: str
    motionGenPrompt: str
    motionmodelSelect: str
    motionLerp: int
    motionframe: int
@app.post("/generate-custommotion")
async def customMotion(data:CustomMotionModel):
    logger.info(f"生成自定义动作: {data.selectedCharValue}")
    return await process_custommotion(data)

# 移动并重命名动作文件
class MotionFileRenameRequest(BaseModel):
    motionoutputname: str
@app.post("/renameandmove-motion-file")
async def rename_motion_file(data: MotionFileRenameRequest):
    motionoutputname = data.motionoutputname
    directory = '../output/motion'
    new_file_path = './static/data/motion'
    if not os.path.exists(new_file_path):
        os.makedirs(new_file_path)
    files = os.listdir(directory)
    target_file = None
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
                target_file = filename
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
        return {"fileName": new_filename}
    raise HTTPException(status_code=404, detail="文件未找到")

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


# 获取符合条件的动作文件
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
    try:
        motion_files = [
            motion for motion in os.listdir(MOTION_FOLDER)
            if motion.startswith(selected_scene_index + "_") and motion.endswith('.mp4') and '.' not in motion[:-4] # 可根据需要添加其他扩展名
        ]
        if not motion_files:
            raise HTTPException(status_code=404, detail="未找到符合条件的动作文件")
        # 自定义排序函数，按下划线后面的数字排序
        def sort_key(file_name):
            # 提取下划线后面的部分，并去掉 .flac 后缀
            number_part = file_name.split('_')[1].split('.')[0]
            return int(number_part)
        motion_files.sort(key=sort_key)
        return JSONResponse(content={"motion_files": motion_files})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#动作拼合与帧插值
class MotionMergeModel(BaseModel):
    selectedSceneIndex: str
@app.post("/motion-apply")
async def motion_merge(data: MotionMergeModel):
    selectedSceneIndex = data.selectedSceneIndex
    MOTION_FOLDER = './static/data/motion'
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
        # 运行插帧函数（假设插帧函数名为interpolate_frames）
        result =  await interpolate_frames(outputname)
        if result:
            logger.info(f"{outputname} 帧插值完成")
            # 调用 rename_motion_file 函数
            rename_request = MotionFileRenameRequest(motionoutputname=outputname)
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
    #视频拼合
    merge_motion_files = [
        motion for motion in os.listdir(MOTION_FOLDER)
        if motion.startswith(selectedSceneIndex + "_") and motion.endswith('.mp4')
    ]
    merge_motion_files.sort(key=sort_key)
    print("merge_motion_files:"+str(merge_motion_files))
    if not merge_motion_files:
        raise HTTPException(status_code=404, detail="未找到需要拼合的视频文件")    
    clips = [VideoFileClip(os.path.join(MOTION_FOLDER, file)) for file in merge_motion_files]
    final_clip = concatenate_videoclips(clips)
    final_clip.write_videofile(os.path.join(MOTION_FOLDER, f"{selectedSceneIndex}.mp4"), codec='libx264')
    # 删除拼合前的视频文件
    for file in merge_motion_files:
        file_path = os.path.join(MOTION_FOLDER, file)
        try:
            os.unlink(file_path)
            logger.info(f"删除文件: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete {file_path}. Reason: {e}")
    return JSONResponse(content={"status": "success", "message": "视频拼合完成", "fileName": f"{selectedSceneIndex}.mp4"})
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

#文本生成图片-flux
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

#保存生成的图片
class SaveImageRequest(BaseModel):
    imageUrl: str
    charName: str
@app.post("/save_gen_image")
async def save_gen_image(request: SaveImageRequest):
    save_path = "./static/data/character"
    try:
        # 下载图片
        response = requests.get(request.imageUrl)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download image")
        file_extension = ".png"  # 默认使用 .png 扩展名
        # 构建保存路径
        save_filename = f"{request.charName}{file_extension}"
        save_full_path = os.path.join(save_path, save_filename)
        with open(save_full_path, 'wb') as file:
            file.write(response.content)
        return {"message": "Image saved successfully", "filename": save_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#获取生成的图片
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

#删除生成的图片
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
UPLOAD_DIRECTORY = "../input"
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
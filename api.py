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
from pydub import AudioSegment
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

#文生图
class TextToImageModel(BaseModel):
    prompt: str
    selectedFileName: str
    queuesize: int
    batchsize:int
@app.post("/generate_img", tags=["perfume bottle"])
async def generate_img(data:TextToImageModel):
    logger.info(f"批次为：{data.queuesize}")
    # logger.info(await process_generateimg(data,batch_size))
    return await process_generateimg(data,data.queuesize)

#获取模型文件列表
@app.get("/get_file_list", response_class=JSONResponse)
async def get_file_list():
    #模型的存放路径
    directory_path = "../models/checkpoints"
    
    if not os.path.exists(directory_path):
        return {"detail": f"Directory {directory_path} not found"}

    try:
        # 获取文件列表
        files = os.listdir(directory_path)
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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


if __name__ == '__main__':    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# cd /root/autodl-tmp/ComfyUI/demo
# 运行命令：uvicorn api:app --reload
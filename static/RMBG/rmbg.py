import os
import cv2
import glob
from PIL import Image
import torch
from torchvision import transforms
from transformers import AutoModelForImageSegmentation
from moviepy import *
from tqdm import tqdm
import imageio
import numpy as np
import argparse

# ========================
# 1. RMBG-2.0 模型初始化
# ========================
print("加载 RMBG-2.0 模型...")
model = AutoModelForImageSegmentation.from_pretrained('briaai/RMBG-2.0', trust_remote_code=True)
torch.set_float32_matmul_precision('highest')
model.to('cuda')
model.eval()

# 定义图像预处理
image_size = (1024, 1024)
transform_image = transforms.Compose([
    transforms.Resize(image_size),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# ========================
# 2. 视频与输出设置
# ========================
parser = argparse.ArgumentParser(description="Remove background from video.")
parser.add_argument('--videoname', type=str, required=True, help='Name of the input video file (without extension)')
parser.add_argument('--bashpath', type=str, default="", help='Base path for output files')
args = parser.parse_args()

bashpath = args.bashpath
video_path = os.path.join(bashpath, f"{args.videoname}.mp4")  # 输入视频
frames_dir = os.path.join(bashpath, f"{args.videoname}_frames")  # 输出序列帧（PNG）目录
output_video = os.path.join(bashpath, f"{args.videoname}.webm")  # 输出 WebM 文件名
audio_output = os.path.join(bashpath, f"{args.videoname}.mp3")  # 输出音频文件名

os.makedirs(frames_dir, exist_ok=True)

# ========================
# 3. 提取音频
# ========================
def extract_audio(video_path, audio_path):
    # 加载视频文件
    video_clip = VideoFileClip(video_path)
    # 提取音频
    audio_clip = video_clip.audio
    # 将音频写入MP3文件
    audio_clip.write_audiofile(audio_path, codec='libmp3lame')
    # 关闭音频和视频剪辑
    audio_clip.close()
    video_clip.close()

# 使用示例
extract_audio(video_path, audio_output)
print(f"音频提取完成，输出文件：{audio_output}")

# ========================
# 4. 视频处理
# ========================
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print(f"视频帧率: {fps}, 总帧数: {total_frames}")

frame_idx = 0
with tqdm(total=total_frames, desc="处理帧") as pbar:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 将 OpenCV BGR 转为 PIL(RGB)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)
        original_size = pil_img.size

        # 预处理 -> 模型推理
        input_tensor = transform_image(pil_img).unsqueeze(0).to('cuda')
        with torch.no_grad():
            preds = model(input_tensor)[-1].sigmoid().cpu()
        pred = preds[0].squeeze()

        # 将预测 mask 转为 PIL，缩放回原图大小
        mask_pil = transforms.ToPILImage()(pred)
        mask_resized = mask_pil.resize(original_size)

        # 为原图添加 alpha 通道
        pil_img.putalpha(mask_resized)

        # 保存 PNG 帧（带透明通道）
        frame_filename = os.path.join(frames_dir, f"frame_{frame_idx:05d}.png")
        pil_img.save(frame_filename)

        frame_idx += 1
        pbar.update(1)

cap.release()
print("所有帧处理完成！")

# ========================
# 5. 使用 MoviePy 合成带透明背景的 WebM
# ========================
frame_files = sorted(glob.glob(os.path.join(frames_dir, "frame_*.png")))
print("生成视频中，请稍候...")

clip = ImageSequenceClip(frame_files, fps=fps)

# 加载提取的音频文件
audio_clip = AudioFileClip(audio_output)

# 合并音频
clip = clip.with_audio(audio_clip)

# 使用 VP9 + alpha 通道编码
clip.write_videofile(
    output_video,
    codec="libvpx-vp9",           # VP9 编码
    audio_codec="libvorbis",      # Vorbis 音频
    fps=fps,
    # 指定像素格式为 yuva420p（yuv + alpha）
    ffmpeg_params=["-pix_fmt", "yuva420p"],
)

print(f"视频合成完成，输出文件：{output_video}")

# ========================
# 6. 将处理后的帧转换为 GIF
# ========================
gif_output = os.path.join(bashpath, f"{args.videoname}.gif")
frame_files = sorted(glob.glob(os.path.join(frames_dir, "frame_*.png")))

# 读取所有帧并保持透明通道
frames = []
for frame_file in frame_files:
    frame = Image.open(frame_file).convert("RGBA")
    frames.append(np.array(frame))

# 使用 imageio 保存 GIF，保持透明通道，并使用 Floyd-Steinberg 误差扩散算法
imageio.mimsave(gif_output, frames, 'GIF', duration=1/24, palettesize=256, disposal=2, quantizer='nq')
print(f"GIF 文件生成完成，输出文件：{gif_output}")

# ========================
# 7. 删除 frames_dir 文件夹
# ========================
import shutil
shutil.rmtree(frames_dir)
print(f"已删除文件夹：{frames_dir}")
os.remove(audio_output)
print(f"已删除文件：{audio_output}")
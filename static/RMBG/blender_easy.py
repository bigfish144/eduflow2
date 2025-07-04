from moviepy import *
import cv2
foreground_video_path = 'output.webm'
background_image_path = 'background.png'

# 加载前景视频和背景图片
foreground_clip = VideoFileClip(foreground_video_path)
background_clip = ImageClip(background_image_path).with_duration(foreground_clip.duration)
cap = cv2.VideoCapture(foreground_video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
# 获取前景视频的透明通道（mask）
mask = foreground_clip.mask

# 合成视频，确保背景色设置为透明
final_clip = CompositeVideoClip([background_clip, foreground_clip.with_mask(mask)], size=(1920, 1080), bg_color=None)

# 写入输出文件，使用 VP9 编码和 yuva420p 像素格式
final_clip.write_videofile(
    'output_video.webm',
    codec="libvpx-vp9",           # VP9 编码
    audio_codec="libvorbis",      # Vorbis 音频
    fps=fps,
    # 指定像素格式为 yuva420p（yuv + alpha）
    ffmpeg_params=["-pix_fmt", "yuva420p"],
)
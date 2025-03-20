from moviepy import *

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
video_path = 'input.mp4'  # 替换为你的视频文件路径
audio_path = 'test.mp3'  # 替换为你想要保存的音频文件路径
extract_audio(video_path, audio_path)
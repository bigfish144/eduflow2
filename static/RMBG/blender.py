from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip
import os

# 设置文件路径
gif_file = 'outgif.gif'  # 替换为您的GIF文件路径
audio_file = 'extracted_audio.mp3'  # 替换为您的音频文件路径
background_image = 'background.png'  # 替换为您的背景图片路径

# 加载GIF文件
gif_clip = VideoFileClip(gif_file, has_mask=True).set_fps(24)

# 加载音频文件
audio_clip = AudioFileClip(audio_file)

# 设置视频持续时间与音频一致
gif_clip = gif_clip.set_duration(audio_clip.duration)

# 加载背景图片，并设置为视频大小
background = ImageClip(background_image).resize((1920, 1080))

# 将背景设置为视频的持续时间
background = background.set_duration(gif_clip.duration)

# 将背景和GIF合成，确保透明背景
final_clip = CompositeVideoClip([background, gif_clip.set_position('center')], size=gif_clip.size)

# 设置音频
final_clip = final_clip.set_audio(audio_clip)

# 输出最终视频
final_clip.write_videofile('output_video.mp4', codec='libx264', fps=24)

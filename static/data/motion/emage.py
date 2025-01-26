from gradio_client import Client, handle_file

# 初始化客户端
client = Client("H-Liu1997/EMAGE")

# 调用 API，传入所需的参数
result = client.predict(
    audio=handle_file('/root/autodl-tmp/ComfyUI/demo/static/data/motion/2.flac'),  # 输入音频文件的 URL
    model_type="EMAGE (Full body + Face)",  # 选择模型类型，可能的值有 "DisCo (Upper only)", "CaMN (Upper only)", "EMAGE (Full body + Face)"
    render_mesh=True,  # 是否渲染网格模型
    render_face=False,  # 是否渲染2D人脸标志
    render_mesh_face=False,  # 是否渲染网格人脸模型
    api_name="/inference_app"  # API 名称
)

# 打印返回结果
print(result)
import shutil
import os
# 目标文件夹
output_dir = '/root/autodl-tmp/ComfyUI/demo/motion'

# 如果目标文件夹不存在，创建它
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 处理视频文件并重命名
for idx, item in enumerate(result[:-1]):  # 不处理最后的 .npz 文件
    if item is None:  # 跳过 None 的条目
        continue

    video_path = item.get('video')  # 使用 .get() 确保安全访问
    if video_path:  # 确保 video_path 存在
        new_video_name = f"video_output_{idx + 1}.mp4"
        new_video_path = os.path.join(output_dir, new_video_name)

        # 移动文件并重命名
        shutil.move(video_path, new_video_path)
        print(f"Moved video: {video_path} to {new_video_path}")

# 处理 .npz 文件
npz_file = result[-1]
if npz_file:  # 确保 npz 文件路径存在
    new_npz_name = "motion_output.npz"
    new_npz_path = os.path.join(output_dir, new_npz_name)

    # 移动 .npz 文件
    shutil.move(npz_file, new_npz_path)
    print(f"Moved .npz file: {npz_file} to {new_npz_path}")
import json
import base64
def load_json_template(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)
# 打开图片文件并读取其二进制内容，进行Base64编码，然后解码为UTF-8字符串
def image_to_base64(filename):
    image_path = f"./output/{filename}"    
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return encoded_string
#test

import os
import imageio
import glob
from pathlib import Path
from PIL import Image
import re
def create_webp_from_pngs(input_folder, output_path, fps=24):
    # 获取文件夹中所有 PNG 文件的路径
    png_files = sorted(glob.glob(os.path.join(input_folder, '*.png')))
    if not png_files:
        print(f"No PNG files found in {input_folder}")
        return
    # 读取所有 PNG 文件
    images = []
    for png_file in png_files:
        images.append(imageio.imread(png_file))
    # 将最后一帧重复添加 fps * 3 次
    if images:
        last_frame = images[-1]
        images.extend([last_frame] * (fps * 3))
    # 创建 WebP 文件
    imageio.mimsave(output_path, images, fps=fps, format='WEBP')
    print(f"WebP created successfully at {output_path}")


def numerical_sort(value):
    # 提取文件名中的数字部分用于排序
    numbers = re.findall(r'\d+', value.name)
    return int(numbers[0]) if numbers else float('inf')

def create_webp_with_alpha(input_folder, output_path, fps=24):
    """
    将指定文件夹中的 PNG 图像序列转换为支持透明通道的 WebP 动画。
    
    :param input_folder: 包含 PNG 帧的文件夹路径
    :param output_path: 输出 WebP 路径（例如：output.webp）
    :param fps: 每秒帧数
    """
    png_files = sorted(Path(input_folder).glob("*.png"), key=numerical_sort)  # ✅ 添加数字排序
    if not png_files:
        print(f"⚠️ 没有在 {input_folder} 中找到任何 PNG 文件")
        return

    images = []
    for png_file in png_files:
        try:
            img = Image.open(png_file)
            images.append(img)
        except Exception as e:
            print(f"❌ 无法读取文件 {png_file}: {e}")

    if not images:
        print("⚠️ 没有成功读取任何图像，WebP 创建失败")
        return

    duration = int(1000 / fps)

    try:
        images[0].save(
            output_path,
            save_all=True,
            append_images=images[1:],
            duration=duration,
            loop=0,
            disposal=2,
            format="webp"
        )
        print(f"✅ WebP 成功创建（保留透明通道）：{output_path}")
    except Exception as e:
        print(f"❌ 创建 WebP 失败: {e}")

if __name__ == "__main__":
    input_folder = "/root/autodl-tmp/ComfyUI/demo/static/images/FOFO/posegen"
    output_path = "/root/autodl-tmp/ComfyUI/demo/static/images/FOFO/posegen.webp"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    create_webp_with_alpha(input_folder, output_path, fps=30)
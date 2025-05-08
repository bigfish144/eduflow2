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

if __name__ == "__main__":
    input_folder = "/root/autodl-tmp/ComfyUI/demo/static/images/FOFO/bound"  # 输入文件夹路径
    output_path = "/root/autodl-tmp/ComfyUI/demo/static/images/FOFO/bound.webp"  # 输出 WebP 文件路径
    create_webp_from_pngs(input_folder, output_path, fps=24)
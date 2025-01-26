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


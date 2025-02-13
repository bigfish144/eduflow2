#!/bin/bash

# 激活虚拟环境
source /root/autodl-tmp/py39/bin/activate
cd ../../PantoMatrix
# 接收参数
audio_input="../ComfyUI/demo/static/data/audio/$1"
save_folder="../ComfyUI/demo/static/data/motion-pre"

# 运行 Python 脚本，传递参数

python /root/autodl-tmp/PantoMatrix/test_camn_audio.py --visualization --nopytorch3d --audio_input $audio_input --save_folder $save_folder

# 退出虚拟环境
deactivate
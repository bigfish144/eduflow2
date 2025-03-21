#!/bin/bash
# 激活虚拟环境
source /root/autodl-tmp/rmbg/bin/activate
# 接收参数
videoname=$1
bashpath=$2
python /root/autodl-tmp/ComfyUI/demo/static/RMBG/rmbg.py --videoname $videoname --bashpath $bashpath
deactivate
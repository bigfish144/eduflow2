#!/bin/bash

# 激活虚拟环境
source /root/autodl-tmp/rmbg/bin/activate
cd RMBG
# 接收参数
python rmbg.py

deactivate
from gradio_client import Client, handle_file

client = Client("H-Liu1997/EMAGE")
audiopath = "./static/data/audio/"+ fileName +".flac"
logger.info("默认生成动作:"+audiopath)
try:
    result = client.predict(
        audio=handle_file(audiopath),  # 输入音频文件的 URL
        model_type="CaMN (Upper only)",  # 选择模型类型，可能的值有 "DisCo (Upper only)", "CaMN (Upper only)", "EMAGE (Full body + Face)"
        render_mesh=True,  # 是否渲染网格模型
        render_face=False,  # 是否渲染2D人脸标志
        render_mesh_face=False,  # 是否渲染网格人脸模型
        api_name="/inference_app"  # API 名称
    )
    print(result)
    # logger.info(f"Prediction result: {result}")
    output_dir = './static/data/motion-pre'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # 处理视频文件并重命名
    for item in result:
        if isinstance(item, dict) and 'video' in item:
            video_path = item['video']
            if video_path:
                basename = os.path.basename(video_path)
                if basename == "camn_output_2dbody_audio.mp4":
                    os.remove(video_path)
                    logger.info(f"Deleted video: {video_path}")
                elif basename == "camn_output.mp4":
                    new_video_name = fileName + ".mp4"
                    new_video_path = os.path.join(output_dir, new_video_name)
                    shutil.move(video_path, new_video_path)
                    logger.info(f"Renamed video: {video_path} to {new_video_path}")
    
    # 处理 .npz 文件
    for item in result:
        if isinstance(item, str) and item.endswith('.npz'):
            npz_file = item
            if npz_file:
                os.remove(npz_file)
                logger.info(f"Deleted .npz file: {npz_file}")
    
    return {"outputname": fileName + ".mp4"}
except Exception as e:
    logger.error(f"Error in process_defaultmotion: {e}")
    raise HTTPException(status_code=500, detail=str(e))
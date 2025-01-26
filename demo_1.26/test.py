import asyncio
import websockets
import json
import uuid
client_id = str(uuid.uuid4())
async def test_websocket():
    # 连接到 WebSocket 服务器
    uri = "ws://127.0.0.1:8188/ws?clientId=test_client_id"
    async with websockets.connect(uri) as websocket:
        # 发送请求以获取队列状态
        await websocket.send(json.dumps({"type": "get_queue_status"}))
        
        # 接收服务器的响应
        response = await websocket.recv()
        print(f"Received: {response}")

# 运行测试
asyncio.run(test_websocket())

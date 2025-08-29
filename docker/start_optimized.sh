#!/bin/bash

echo "=== MinerU 显存优化启动脚本 ==="

# 检查GPU状态
echo "检查GPU显存状态..."
nvidia-smi --query-gpu=index,name,memory.total,memory.free --format=csv,noheader,nounits

# 设置环境变量
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
export CUDA_LAUNCH_BLOCKING=1
export MINERU_VIRTUAL_VRAM_SIZE=8
export MINERU_DEVICE_MODE=cuda

echo "设置显存优化环境变量..."

# 启动SGLang服务器（显存优化模式）
echo "启动SGLang服务器（显存优化模式）..."
docker run -d \
    --name mineru-sglang-optimized \
    --gpus '"device=0"' \
    -p 30000:30000 \
    -e MINERU_MODEL_SOURCE=local \
    -e MINERU_VIRTUAL_VRAM_SIZE=8 \
    -e MINERU_DEVICE_MODE=cuda \
    -e PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128 \
    -e CUDA_LAUNCH_BLOCKING=1 \
    --ulimit memlock=-1 \
    --ulimit stack=67108864 \
    --ipc=host \
    mineru-sglang:latest \
    mineru-sglang-server \
        --host 0.0.0.0 \
        --port 30000 \
        --mem-fraction-static 0.4 \
        --load-in-4bit \
        --max-model-len 2048 \
        --disable-log-stats \
        --disable-log-requests

echo "SGLang服务器已启动，端口: 30000"

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo "检查服务状态..."
docker ps | grep mineru
nvidia-smi --query-gpu=index,memory.used,memory.free --format=csv,noheader,nounits

echo "=== 启动完成 ==="
echo "SGLang服务器: http://localhost:30000"
echo "使用以下命令查看日志: docker logs -f mineru-sglang-optimized"
echo "使用以下命令停止服务: docker stop mineru-sglang-optimized"

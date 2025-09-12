#!/bin/bash

echo "=== MinerU Gradio Web界面 显存优化启动脚本 ==="

# 检查Docker镜像是否存在
if ! docker images | grep -q "mineru-sglang.*latest"; then
    echo "❌ 未找到mineru-sglang:latest镜像"
    echo "请先运行构建脚本: ./build_image.sh"
    exit 1
fi

echo "✅ 找到mineru-sglang:latest镜像"

# 检查当前显存状态
echo "检查当前GPU显存状态..."
nvidia-smi --query-gpu=index,name,memory.used,memory.free --format=csv,noheader,nounits

# 停止现有服务
echo "停止现有MinerU服务..."
docker stop $(docker ps -q --filter "name=mineru") 2>/dev/null || true
docker rm $(docker ps -aq --filter "name=mineru") 2>/dev/null || true

# 清理显存
echo "清理GPU显存..."
sudo nvidia-smi --gpu-reset 2>/dev/null || echo "无法重置GPU，继续启动..."

# 等待显存清理
sleep 5

# 显示清理后的显存状态
echo "清理后的显存状态..."
nvidia-smi --query-gpu=index,name,memory.used,memory.free --format=csv,noheader,nounits

# 启动显存优化的Gradio界面（直接启动，不依赖SGLang服务器）
echo "启动显存优化的Gradio界面..."

# 创建必要的目录
mkdir -p ./models ./logs ./uploads

docker run -d \
    --name mineru \
    --gpus '"device=0"' \
    -p 7860:7860 \
    -e MINERU_MODEL_SOURCE=local \
    -e MINERU_VIRTUAL_VRAM_SIZE=8 \
    -e MINERU_DEVICE_MODE=cuda \
    -e PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128 \
    -e CUDA_LAUNCH_BLOCKING=1 \
    --ulimit memlock=-1 \
    --ulimit stack=67108864 \
    --ipc=host \
    -v ./models:/app/models:ro \
    -v ./logs:/app/logs \
    -v ./uploads:/app/uploads \
    --memory=12g \
    mineru-sglang:latest \
    mineru-gradio \
        --server-name 0.0.0.0 \
        --server-port 7860 \
        --enable-sglang-engine true

# 等待Gradio启动
echo "等待Gradio界面启动..."
sleep 10

# 检查服务状态
echo "检查所有服务状态..."
docker ps | grep mineru

# 显示最终显存状态
echo "启动后的显存状态..."
nvidia-smi --query-gpu=index,name,memory.used,memory.free --format=csv,noheader,nounits

echo ""
echo "=== 启动完成 ==="
echo "Gradio Web界面: http://localhost:7860"
echo ""
echo "=== 管理命令 ==="
echo "查看Gradio日志: docker logs -f mineru"
echo "停止服务: docker stop mineru"
echo "重启服务: docker restart mineru"
echo ""
echo "=== 显存监控 ==="
echo "实时监控: watch -n 1 nvidia-smi"
echo "进程监控: nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv"

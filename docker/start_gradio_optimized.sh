#!/bin/bash

echo "=== MinerU Gradio 显存优化启动脚本 ==="

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

# 启动显存优化的SGLang服务器
echo "启动显存优化的SGLang服务器..."
docker-compose -f docker-compose-gradio-optimized.yaml --profile sglang-server up -d

# 等待SGLang服务器启动
echo "等待SGLang服务器启动..."
sleep 15

# 检查SGLang服务器状态
echo "检查SGLang服务器状态..."
docker logs mineru-sglang-server-optimized --tail 10

# 启动显存优化的Gradio界面
echo "启动显存优化的Gradio界面..."
docker-compose -f docker-compose-gradio-optimized.yaml --profile gradio up -d

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
echo "SGLang服务器: http://localhost:30000"
echo "Gradio界面: http://localhost:7860"
echo ""
echo "=== 管理命令 ==="
echo "查看日志: docker logs -f mineru-gradio-optimized"
echo "停止服务: docker-compose -f docker-compose-gradio-optimized.yaml down"
echo "重启服务: docker-compose -f docker-compose-gradio-optimized.yaml restart"
echo ""
echo "=== 显存监控 ==="
echo "实时监控: watch -n 1 nvidia-smi"
echo "进程监控: nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv"

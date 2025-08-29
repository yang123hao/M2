#!/bin/bash

echo "=== MinerU Docker 开发环境启动脚本 ==="

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker服务"
    exit 1
fi

# 检查镜像是否存在
if ! docker images | grep -q "mineru-sglang"; then
    echo "❌ mineru-sglang镜像不存在，请先构建镜像"
    echo "运行: docker build -t mineru-sglang:latest -f Dockerfile ."
    exit 1
fi

echo "✅ Docker环境检查通过"

# 创建必要的目录
mkdir -p output logs
mkdir -p ~/.cache/huggingface ~/.cache/modelscope ~/.cache/pip

echo "📁 创建必要的目录结构"

# 显示开发选项
echo ""
echo "=== 开发环境选项 ==="
echo "1. 启动开发容器 (交互式开发)"
echo "2. 启动Gradio开发服务 (自动运行)"
echo "3. 启动完整开发环境 (容器+服务)"
echo "4. 进入现有开发容器"
echo "5. 停止开发环境"
echo "6. 退出"

read -p "请选择 (1-6): " choice

case $choice in
    1)
        echo "🚀 启动开发容器..."
        docker run -it --gpus all \
            --name mineru-dev \
            -p 7700:7700 \
            -p 30000:30000 \
            -p 8200:8200 \
            -v $(pwd)/..:/workspace \
            -v ~/.cache/huggingface:/root/.cache/huggingface \
            -v ~/.cache/modelscope:/root/.cache/modelscope \
            -v ~/.cache/pip:/root/.cache/pip \
            -v $(pwd)/output:/workspace/output \
            -v $(pwd)/logs:/workspace/logs \
            --workdir /workspace \
            --ipc=host \
            mineru-sglang:latest \
            /bin/bash
        ;;
    2)
        echo "🚀 启动Gradio开发服务..."
        docker-compose -f docker-compose-dev.yaml --profile gradio-dev up -d
        echo "✅ Gradio开发服务已启动"
        echo "访问地址: http://localhost:7700"
        echo "查看日志: docker logs -f mineru-gradio-dev"
        ;;
    3)
        echo "🚀 启动完整开发环境..."
        docker-compose -f docker-compose-dev.yaml --profile dev up -d
        echo "✅ 开发环境已启动"
        echo "进入容器: docker exec -it mineru-dev bash"
        echo "启动Gradio: docker exec -it mineru-dev python -m mineru.cli.gradio_app --server-port 7700"
        ;;
    4)
        if docker ps | grep -q "mineru-dev"; then
            echo "🔧 进入现有开发容器..."
            docker exec -it mineru-dev bash
        else
            echo "❌ 开发容器未运行，请先启动"
        fi
        ;;
    5)
        echo "🛑 停止开发环境..."
        docker-compose -f docker-compose-dev.yaml down
        docker stop mineru-dev mineru-gradio-dev 2>/dev/null || true
        docker rm mineru-dev mineru-gradio-dev 2>/dev/null || true
        echo "✅ 开发环境已停止"
        ;;
    6)
        echo "👋 退出"
        exit 0
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "=== 开发环境管理命令 ==="
echo "查看容器状态: docker ps | grep mineru"
echo "查看日志: docker logs -f [容器名]"
echo "进入容器: docker exec -it [容器名] bash"
echo "停止服务: docker-compose -f docker-compose-dev.yaml down"
echo "重启服务: docker-compose -f docker-compose-dev.yaml restart"

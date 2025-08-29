#!/bin/bash

echo "=== MinerU 本地启动脚本 ==="

# 检查Python版本
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python版本过低，需要Python 3.10+，当前版本: $python_version"
    exit 1
fi

echo "✅ Python版本检查通过: $python_version"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 升级pip
echo "⬆️  升级pip..."
pip install --upgrade pip

# 安装依赖
echo "📚 安装项目依赖..."
pip install -r requirements.txt

# 检查CUDA环境
if command -v nvidia-smi &> /dev/null; then
    echo "🎮 检测到NVIDIA GPU，检查CUDA环境..."
    nvidia-smi --query-gpu=index,name,memory.total,memory.free --format=csv,noheader,nounits
    
    # 设置显存优化环境变量
    export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
    export CUDA_LAUNCH_BLOCKING=1
    export MINERU_VIRTUAL_VRAM_SIZE=8
    export MINERU_DEVICE_MODE=cuda
    
    echo "✅ CUDA环境配置完成"
else
    echo "⚠️  未检测到NVIDIA GPU，将使用CPU模式"
    export MINERU_DEVICE_MODE=cpu
fi

# 设置模型源
export MINERU_MODEL_SOURCE=huggingface

echo ""
echo "=== 启动选项 ==="
echo "1. 启动Gradio Web界面 (推荐)"
echo "2. 启动SGLang服务器"
echo "3. 启动API服务"
echo "4. 启动CLI工具"
echo "5. 退出"

read -p "请选择启动方式 (1-5): " choice

case $choice in
    1)
        echo "🚀 启动Gradio Web界面..."
        echo "访问地址: http://localhost:7700"
        python -m mineru.cli.gradio_app \
            --server-name 0.0.0.0 \
            --server-port 7700 \
            --dp-size 1
        ;;
    2)
        echo "🚀 启动SGLang服务器..."
        echo "服务地址: http://localhost:30000"
        python -m mineru.cli.vlm_sglang_server \
            --host 0.0.0.0 \
            --port 30000 \
            --mem-fraction-static 0.4 \
            --load-in-4bit \
            --max-model-len 2048
        ;;
    3)
        echo "🚀 启动API服务..."
        echo "API地址: http://localhost:8200"
        python -m mineru.cli.fast_api \
            --host 0.0.0.0 \
            --port 8200
        ;;
    4)
        echo "🚀 启动CLI工具..."
        echo "使用示例: mineru -p input.pdf -o output_dir"
        echo "输入 'exit' 退出CLI模式"
        bash
        ;;
    5)
        echo "👋 退出启动脚本"
        exit 0
        ;;
    *)
        echo "❌ 无效选择，退出"
        exit 1
        ;;
esac

# MinerU 本地安装和启动指南

## 🚀 快速开始

### 1. 环境要求
- Python 3.10+
- 8GB+ 可用内存
- NVIDIA GPU (推荐，用于加速)

### 2. 一键安装和启动
```bash
# 给脚本执行权限
chmod +x start_local.sh

# 运行启动脚本
./start_local.sh
```

脚本会自动：
- 检查Python版本
- 创建虚拟环境
- 安装依赖包
- 配置CUDA环境
- 提供启动选项

## 📦 手动安装步骤

### 步骤1: 创建虚拟环境
```bash
python3 -m venv venv
source venv/bin/activate
```

### 步骤2: 安装依赖
```bash
# 升级pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 或者安装项目本身（开发模式）
pip install -e .
```

### 步骤3: 启动服务

#### 启动Gradio Web界面（推荐）
```bash
python -m mineru.cli.gradio_app \
    --server-name 0.0.0.0 \
    --server-port 7700 \
    --dp-size 1
```

#### 启动SGLang服务器
```bash
python -m mineru.cli.vlm_sglang_server \
    --host 0.0.0.0 \
    --port 30000 \
    --mem-fraction-static 0.4 \
    --load-in-4bit \
    --max-model-len 2048
```

#### 启动API服务
```bash
python -m mineru.cli.fast_api \
    --host 0.0.0.0 \
    --port 8200
```

#### 使用CLI工具
```bash
# 处理单个PDF
mineru -p input.pdf -o output_dir

# 处理目录
mineru -p input_dir/ -o output_dir/
```

## 🔧 显存优化配置

### 环境变量设置
```bash
# 显存优化
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
export CUDA_LAUNCH_BLOCKING=1
export MINERU_VIRTUAL_VRAM_SIZE=8
export MINERU_DEVICE_MODE=cuda

# 模型源
export MINERU_MODEL_SOURCE=huggingface
```

### 启动参数优化
```bash
# SGLang服务器优化参数
--mem-fraction-static 0.4      # 限制KV缓存
--load-in-4bit                 # 4位量化
--max-model-len 2048           # 限制序列长度
--disable-log-stats            # 禁用统计日志
```

## 🌐 访问地址

启动成功后，可以通过以下地址访问：

- **Gradio Web界面**: http://localhost:7700
- **SGLang服务器**: http://localhost:30000
- **API服务**: http://localhost:8200

## 📊 显存使用监控

### 实时监控
```bash
# 监控GPU状态
watch -n 1 nvidia-smi

# 监控进程显存使用
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
```

### 使用监控脚本
```bash
# 运行显存监控工具
python monitor_and_optimize.py
```

## 🆘 常见问题

### 1. 依赖安装失败
```bash
# 尝试使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 2. CUDA版本不兼容
```bash
# 检查CUDA版本
nvidia-smi
nvcc --version

# 安装对应版本的PyTorch
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 3. 显存不足
```bash
# 使用更激进的优化参数
--mem-fraction-static 0.2
--load-in-4bit
--max-model-len 1024
```

### 4. 端口被占用
```bash
# 查看端口占用
netstat -tlnp | grep :7700

# 使用其他端口
--server-port 7701
```

## 📁 项目结构

```
MinerU/
├── mineru/                 # 核心代码
├── requirements.txt        # 依赖列表
├── start_local.sh         # 启动脚本
├── monitor_and_optimize.py # 显存监控
└── README_本地安装.md     # 本文件
```

## 🔗 相关链接

- [项目主页](https://mineru.net/)
- [官方文档](https://opendatalab.github.io/MinerU/)
- [GitHub仓库](https://github.com/opendatalab/MinerU)

---

**提示**: 首次启动可能需要下载模型文件，请确保网络连接正常。

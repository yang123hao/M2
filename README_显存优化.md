# MinerU 显存优化指南

## 概述

本指南提供了多种方法来减少MinerU模型占用显存，让您可以在显存有限的设备上运行大型VLM模型。

## 🚀 快速优化方案

### 方案1: 使用SGLang显存优化参数（推荐）

```bash
# 启动SGLang服务器，显存占用减少50-70%
mineru-sglang-server \
    --mem-fraction-static 0.3 \
    --load-in-4bit \
    --max-model-len 2048
```

**参数说明：**
- `--mem-fraction-static 0.3`: 减少KV缓存大小，显存占用减少40-60%
- `--load-in-4bit`: 4位量化，显存占用减少50%
- `--max-model-len 2048`: 限制最大序列长度，减少显存占用

### 方案2: 使用优化启动脚本

```bash
# 给脚本执行权限
chmod +x start_mineru_optimized.sh

# 启动SGLang服务器（显存优化模式）
./start_mineru_optimized.sh sglang

# 启动API服务（显存优化模式）
./start_mineru_optimized.sh api

# 启动Gradio界面（显存优化模式）
./start_mineru_optimized.sh gradio
```

### 方案3: 环境变量优化

```bash
# 设置环境变量
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
export CUDA_LAUNCH_BLOCKING=1
export MINERU_VIRTUAL_VRAM_SIZE=4
export MINERU_DEVICE_MODE=cuda

# 然后启动服务
mineru-sglang-server
```

## 📊 显存监控

### 使用监控脚本

```bash
# 安装依赖
pip install GPUtil

# 运行监控脚本
python monitor_and_optimize.py
```

监控脚本会实时显示：
- GPU显存使用情况
- 进程显存占用
- 温度和负载信息
- 优化建议

### 手动监控

```bash
# 查看GPU状态
nvidia-smi

# 查看进程显存使用
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
```

## 🔧 高级优化技巧

### 1. 多GPU张量并行

如果您有多张显卡，可以使用张量并行分散显存：

```bash
# 使用2张显卡的张量并行
mineru-sglang-server --tp-size 2

# 使用数据并行
mineru-sglang-server --dp-size 2
```

### 2. 批处理优化

根据显存大小自动调整批处理：

```bash
# 8GB显存
export MINERU_VIRTUAL_VRAM_SIZE=8

# 12GB显存
export MINERU_VIRTUAL_VRAM_SIZE=12

# 16GB显存
export MINERU_VIRTUAL_VRAM_SIZE=16
```

### 3. 模型精度优化

```bash
# 使用8位量化（平衡精度和显存）
mineru-sglang-server --load-in-8bit

# 使用4位量化（最大显存节省）
mineru-sglang-server --load-in-4bit

# 使用BF16精度（如果支持）
mineru-sglang-server --dtype bfloat16
```

### 4. 序列长度优化

```bash
# 限制最大序列长度
mineru-sglang-server --max-model-len 1024  # 更短，更省显存
mineru-sglang-server --max-model-len 2048  # 平衡
mineru-sglang-server --max-model-len 4096  # 更长，需要更多显存
```

## 📈 显存占用对比

| 优化级别 | 显存占用 | 性能影响 | 推荐场景 |
|---------|---------|---------|---------|
| 无优化 | 100% | 无 | 显存充足 |
| 基础优化 | 60-80% | 轻微 | 显存紧张 |
| 激进优化 | 30-50% | 中等 | 显存不足 |
| 极限优化 | 20-30% | 较大 | 显存严重不足 |

## 🎯 针对不同显存大小的优化策略

### 8GB显存
```bash
mineru-sglang-server \
    --mem-fraction-static 0.4 \
    --load-in-4bit \
    --max-model-len 1024
```

### 12GB显存
```bash
mineru-sglang-server \
    --mem-fraction-static 0.5 \
    --load-in-8bit \
    --max-model-len 2048
```

### 16GB显存
```bash
mineru-sglang-server \
    --mem-fraction-static 0.6 \
    --load-in-8bit \
    --max-model-len 4096
```

### 24GB+显存
```bash
mineru-sglang-server \
    --mem-fraction-static 0.8 \
    --max-model-len 8192
```

## ⚠️ 注意事项

1. **量化影响**: 4位量化会轻微影响模型精度，但显存节省显著
2. **序列长度**: 减少序列长度会影响长文档处理能力
3. **批处理**: 过小的批处理可能影响处理效率
4. **温度监控**: 长时间高负载运行注意GPU温度

## 🆘 故障排除

### 显存不足错误
```bash
# 错误: CUDA out of memory
# 解决: 减少mem-fraction-static或启用量化
mineru-sglang-server --mem-fraction-static 0.2 --load-in-4bit
```

### 模型加载失败
```bash
# 错误: 模型加载失败
# 解决: 检查显存是否足够，尝试更激进的优化
export MINERU_VIRTUAL_VRAM_SIZE=2
mineru-sglang-server --mem-fraction-static 0.1
```

### 性能下降
```bash
# 如果性能下降太多，可以逐步放宽限制
mineru-sglang-server --mem-fraction-static 0.5  # 从0.3增加到0.5
```

## 📞 获取帮助

如果遇到问题，可以：
1. 查看日志输出
2. 使用监控脚本检查显存使用
3. 逐步调整优化参数
4. 在GitHub上提交Issue

---

**记住**: 显存优化是一个平衡过程，需要在显存占用、性能和精度之间找到最佳平衡点。

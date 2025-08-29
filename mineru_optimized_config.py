#!/usr/bin/env python3
"""
MinerU 显存优化配置
用于减少模型占用显存
"""

import os
import torch

def setup_memory_optimization():
    """设置显存优化配置"""
    
    # 1. 设置环境变量
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'
    os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
    
    # 2. 设置设备
    if torch.cuda.is_available():
        # 选择显存最小的GPU
        gpu_memory = []
        for i in range(torch.cuda.device_count()):
            memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
            gpu_memory.append((i, memory))
        
        # 选择显存最小的GPU
        selected_gpu = min(gpu_memory, key=lambda x: x[1])[0]
        os.environ['CUDA_VISIBLE_DEVICES'] = str(selected_gpu)
        
        # 设置显存分配策略
        torch.cuda.set_per_process_memory_fraction(0.8)  # 限制显存使用为80%
        
        print(f"选择GPU {selected_gpu}，显存: {gpu_memory[selected_gpu][1]:.1f}GB")
    
    # 3. 设置模型优化参数
    os.environ['MINERU_VIRTUAL_VRAM_SIZE'] = '4'  # 限制单进程显存使用为4GB
    os.environ['MINERU_DEVICE_MODE'] = 'cuda'
    
    # 4. 启用内存优化
    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True

def get_optimized_sglang_args():
    """获取优化的SGLang启动参数"""
    return [
        '--mem-fraction-static', '0.3',        # 减少KV缓存
        '--load-in-4bit',                      # 4位量化
        '--max-model-len', '2048',             # 限制最大序列长度
        '--disable-log-stats',                 # 禁用统计日志
        '--disable-log-requests',              # 禁用请求日志
    ]

def get_optimized_pipeline_args():
    """获取优化的Pipeline后端参数"""
    return {
        'device_mode': 'cuda',
        'virtual_vram': 4,                     # 4GB显存限制
        'batch_ratio': 1,                      # 最小批处理比例
        'formula_enable': False,               # 禁用公式识别（节省显存）
        'table_enable': True,                  # 保留表格识别
    }

if __name__ == "__main__":
    setup_memory_optimization()
    print("显存优化配置已设置完成")
    print(f"优化后的SGLang参数: {' '.join(get_optimized_sglang_args())}")
    print(f"优化后的Pipeline参数: {get_optimized_pipeline_args()}")

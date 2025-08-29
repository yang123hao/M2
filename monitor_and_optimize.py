#!/usr/bin/env python3
"""
MinerU 显存监控和优化脚本
实时监控显存使用情况并提供优化建议
"""

import os
import time
import psutil
import subprocess
import threading
from typing import Dict, List, Optional

try:
    import torch
    import GPUtil
except ImportError:
    print("请安装必要的依赖: pip install torch GPUtil")
    exit(1)

class VRAMMonitor:
    """显存监控器"""
    
    def __init__(self):
        self.monitoring = False
        self.monitor_thread = None
        
    def get_gpu_info(self) -> List[Dict]:
        """获取GPU信息"""
        try:
            gpus = GPUtil.getGPUs()
            gpu_info = []
            
            for gpu in gpus:
                gpu_info.append({
                    'id': gpu.id,
                    'name': gpu.name,
                    'memory_total': gpu.memoryTotal,
                    'memory_used': gpu.memoryUsed,
                    'memory_free': gpu.memoryFree,
                    'memory_util': gpu.memoryUtil * 100,
                    'temperature': gpu.temperature,
                    'load': gpu.load * 100 if gpu.load else 0
                })
            
            return gpu_info
        except Exception as e:
            print(f"获取GPU信息失败: {e}")
            return []
    
    def get_process_memory(self) -> List[Dict]:
        """获取进程显存使用情况"""
        try:
            # 使用nvidia-smi获取进程显存使用
            result = subprocess.run(
                ['nvidia-smi', '--query-compute-apps=pid,process_name,used_memory', '--format=csv,noheader,nounits'],
                capture_output=True, text=True
            )
            
            processes = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(', ')
                    if len(parts) >= 3:
                        processes.append({
                            'pid': int(parts[0]),
                            'name': parts[1],
                            'memory_mb': int(parts[2])
                        })
            
            return processes
        except Exception as e:
            print(f"获取进程显存信息失败: {e}")
            return []
    
    def start_monitoring(self, interval: int = 5):
        """开始监控"""
        if self.monitoring:
            print("监控已在运行中...")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print(f"开始监控显存使用情况，间隔: {interval}秒")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("监控已停止")
    
    def _monitor_loop(self, interval: int):
        """监控循环"""
        while self.monitoring:
            self._print_status()
            time.sleep(interval)
    
    def _print_status(self):
        """打印状态信息"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("=" * 60)
        print("MinerU 显存监控面板")
        print("=" * 60)
        
        # GPU信息
        gpu_info = self.get_gpu_info()
        if gpu_info:
            print("\n📊 GPU状态:")
            for gpu in gpu_info:
                memory_used_gb = gpu['memory_used'] / 1024
                memory_total_gb = gpu['memory_total'] / 1024
                memory_percent = (gpu['memory_used'] / gpu['memory_total']) * 100
                
                print(f"  GPU {gpu['id']}: {gpu['name']}")
                print(f"    显存: {memory_used_gb:.1f}GB / {memory_total_gb:.1f}GB ({memory_percent:.1f}%)")
                print(f"    温度: {gpu['temperature']}°C, 负载: {gpu['load']:.1f}%")
                
                # 显存使用建议
                if memory_percent > 90:
                    print(f"    ⚠️  显存使用率过高！建议优化")
                elif memory_percent > 80:
                    print(f"    ⚠️  显存使用率较高，注意监控")
                elif memory_percent > 60:
                    print(f"    ✅ 显存使用正常")
                else:
                    print(f"    ✅ 显存使用率较低，可以增加负载")
        
        # 进程信息
        processes = self.get_process_memory()
        if processes:
            print("\n🔍 进程显存使用:")
            total_memory = 0
            for proc in processes:
                memory_gb = proc['memory_mb'] / 1024
                total_memory += proc['memory_mb']
                print(f"  {proc['name']} (PID: {proc['pid']}): {memory_gb:.2f}GB")
            
            print(f"\n总显存使用: {total_memory/1024:.2f}GB")
        
        # 优化建议
        print("\n💡 显存优化建议:")
        print("  1. 使用 --mem-fraction-static 0.3 减少KV缓存")
        print("  2. 启用 --load-in-4bit 4位量化")
        print("  3. 限制 --max-model-len 2048 序列长度")
        print("  4. 使用 --tp-size 2 张量并行（多卡）")
        print("  5. 设置 MINERU_VIRTUAL_VRAM_SIZE=4 限制显存")
        
        print("\n按 Ctrl+C 停止监控")
        print("=" * 60)

def main():
    """主函数"""
    monitor = VRAMMonitor()
    
    try:
        print("MinerU 显存监控工具")
        print("按 Enter 开始监控，按 Ctrl+C 退出")
        input()
        
        monitor.start_monitoring(interval=3)
        
        # 保持主线程运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n正在退出...")
        monitor.stop_monitoring()
    except Exception as e:
        print(f"发生错误: {e}")
        monitor.stop_monitoring()

if __name__ == "__main__":
    main()

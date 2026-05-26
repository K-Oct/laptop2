"""
详细的 SEGD 文件结构分析
"""

import struct
import os

def hex_dump(data, offset=0, length=256):
    """打印十六进制转储"""
    for i in range(0, min(length, len(data)), 16):
        hex_part = ' '.join(f'{b:02x}' for b in data[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
        print(f"{offset+i:04x}:  {hex_part:<48}  {ascii_part}")


filename = '00000001.segd'
file_size = os.path.getsize(filename)

print(f"文件: {filename}")
print(f"大小: {file_size} 字节 ({file_size/1024/1024:.2f} MB)")
print("\n" + "="*80)

with open(filename, 'rb') as f:
    # 读取前 4KB
    data = f.read(4096)
    
    print("\n前 512 字节的十六进制转储:")
    print("-"*80)
    hex_dump(data, 0, 512)
    
    print("\n\n可能的参数解析:")
    print("-"*80)
    
    # 检查关键位置
    print("\n位置 0-15 (可能是文件头):")
    for i in range(0, 16, 2):
        be = struct.unpack('>H', data[i:i+2])[0]
        le = struct.unpack('<H', data[i:i+2])[0]
        print(f"  [{i:2d}] BE: {be:6d} (0x{be:04x})  |  LE: {le:6d} (0x{le:04x})")
    
    print("\n位置 16-63 (头部续):")
    for i in range(16, 64, 2):
        be = struct.unpack('>H', data[i:i+2])[0]
        le = struct.unpack('<H', data[i:i+2])[0]
        print(f"  [{i:2d}] BE: {be:6d} (0x{be:04x})  |  LE: {le:6d} (0x{le:04x})")
    
    # 分析可能的数据段
    print("\n\n检查块结构（假设2048字节块）:")
    print("-"*80)
    
    f.seek(0)
    for block_idx in range(3):  # 检查前3个块
        block_data = f.read(2048)
        if len(block_data) < 2048:
            break
        
        print(f"\n块 {block_idx} (位置: {block_idx*2048}):")
        
        # 统计信息
        zero_count = sum(1 for b in block_data if b == 0)
        non_zero = 2048 - zero_count
        
        print(f"  零字节数: {zero_count}/2048 ({zero_count*100/2048:.1f}%)")
        print(f"  非零字节数: {non_zero}/2048 ({non_zero*100/2048:.1f}%)")
        
        # 检查首字节
        print(f"  首字节: 0x{block_data[0]:02x}")
        
        # 查找第一个非零字节
        for i, b in enumerate(block_data):
            if b != 0:
                print(f"  第一个非零字节在位置: {i} (0x{b:02x})")
                # 显示该位置周围的数据
                start = max(0, i-8)
                end = min(len(block_data), i+16)
                print(f"    上下文: {' '.join(f'{block_data[j]:02x}' for j in range(start, end))}")
                break
    
    print("\n\n尝试识别采样率和通道数:")
    print("-"*80)
    
    # 位置 10-11 看起来像 9250，这可能是采样率
    sr_val = struct.unpack('>H', data[10:12])[0]
    print(f"位置 10-11 (BE): {sr_val} Hz（可能是采样率）")
    
    # 文件大小提示
    print(f"\n文件结构推理:")
    print(f"  总大小: {file_size} 字节")
    print(f"  如果采样率是 9250 Hz:")
    
    # 假设去掉头部后
    for head_size in [2048, 4096, 6400, 8192]:
        remaining = file_size - head_size
        print(f"    头部 {head_size} 字节，剩余 {remaining} 字节")
        
        # 假设每个样本是 2 字节
        num_samples = remaining // 2
        print(f"      如果每样本 2 字节: {num_samples} 样本 ({num_samples/9250:.2f} 秒)")
        
        # 假设是多个通道
        for channels in [1, 2, 4, 8, 16, 32, 64, 128]:
            if num_samples % channels == 0:
                samples_per_channel = num_samples // channels
                print(f"      {channels} 通道: 每通道 {samples_per_channel} 样本 ({samples_per_channel/9250:.2f} 秒)")

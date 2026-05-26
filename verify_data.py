"""
验证 SEGD 数据质量和格式
"""

import sys
sys.path.insert(0, '.')

from main import SEGDReader
import numpy as np

filename = '00000001.segd'
reader = SEGDReader(filename)
reader.read()

data = reader.get_traces_array()

print(f"\n数据统计:")
print(f"  形状: {data.shape}")
print(f"  数据类型: {data.dtype}")
print(f"  最小值: {np.min(data)}")
print(f"  最大值: {np.max(data)}")
print(f"  平均值: {np.mean(data):.2f}")
print(f"  标准差: {np.std(data):.2f}")
print(f"  零值个数: {np.sum(data == 0)}")
print(f"  零值比例: {np.sum(data == 0) / len(data) * 100:.2f}%")

# 检查前100个样本
print(f"\n前 100 个样本的值:")
print(f"  {data[0][:100]}")

# 尝试不同的字节序解释
print(f"\n尝试 Little-Endian 16-bit 有符号整数:")
with open(filename, 'rb') as f:
    f.seek(4096)
    raw_data = f.read(200000)  # 读取 200KB
    data_le = np.frombuffer(raw_data, dtype='<i2')
    print(f"  前 50 个值: {data_le[:50]}")
    print(f"  最小值: {np.min(data_le[:1000])}")
    print(f"  最大值: {np.max(data_le[:1000])}")

print(f"\n尝试 Big-Endian 无符号整数:")
with open(filename, 'rb') as f:
    f.seek(4096)
    raw_data = f.read(200000)
    data_be_u = np.frombuffer(raw_data, dtype='>u2')
    print(f"  前 50 个值: {data_be_u[:50]}")
    print(f"  最小值: {np.min(data_be_u[:1000])}")
    print(f"  最大值: {np.max(data_be_u[:1000])}")

print(f"\n尝试 Little-Endian 无符号整数:")
with open(filename, 'rb') as f:
    f.seek(4096)
    raw_data = f.read(200000)
    data_le_u = np.frombuffer(raw_data, dtype='<u2')
    print(f"  前 50 个值: {data_le_u[:50]}")
    print(f"  最小值: {np.min(data_le_u[:1000])}")
    print(f"  最大值: {np.max(data_le_u[:1000])}")

print(f"\n尝试 Big-Endian 32-bit 有符号整数:")
with open(filename, 'rb') as f:
    f.seek(4096)
    raw_data = f.read(200000)
    data_be_32 = np.frombuffer(raw_data, dtype='>i4')
    print(f"  前 50 个值: {data_be_32[:50]}")
    print(f"  最小值: {np.min(data_be_32[:1000])}")
    print(f"  最大值: {np.max(data_be_32[:1000])}")

# 分析数据的零值分布
print(f"\n检查零值分布:")
samples_per_chunk = len(data) // 20
for i in range(20):
    chunk = data[i*samples_per_chunk:(i+1)*samples_per_chunk]
    zero_ratio = np.sum(chunk == 0) / len(chunk) * 100
    min_val = np.min(chunk)
    max_val = np.max(chunk)
    print(f"  块 {i+1:2d}: 零值 {zero_ratio:5.1f}% | 范围 [{min_val:7d}, {max_val:7d}]")

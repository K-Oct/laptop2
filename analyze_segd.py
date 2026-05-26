import os
import struct

filename = '00000001.segd'
file_size = os.path.getsize(filename)
print(f'文件大小: {file_size} 字节 ({file_size/1024/1024:.2f} MB)')

with open(filename, 'rb') as f:
    # 读取第一个 2KB（通常 SEGD 块大小）
    data = f.read(2048)
    
    print(f'\n前 2048 字节的统计:')
    print(f'全零字节: {data.count(bytes([0]))}')
    print(f'全FF字节: {data.count(bytes([255]))}')
    
    # 检查各种标记
    print(f'\n可能的标记:')
    print(f'首字节: {data[0]:02x}')
    print(f'前4字节: {" ".join(f"{b:02x}" for b in data[:4])}')
    
    # 检查可能的采样率位置
    print(f'\n尝试解析参数（Big-Endian）:')
    for i in range(0, 64, 2):
        val = struct.unpack('>H', data[i:i+2])[0]
        if 0 < val < 10000:
            print(f'  位置 {i:3d}: {val:5d} (Hz/可能是采样率)')
    
    print(f'\n尝试解析参数（Little-Endian）:')
    for i in range(0, 64, 2):
        val = struct.unpack('<H', data[i:i+2])[0]
        if 0 < val < 10000:
            print(f'  位置 {i:3d}: {val:5d} (Hz/可能是采样率)')

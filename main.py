"""
SEGD 地震记录文件读取、处理和可视化
支持：2通道交错 16-bit Big-Endian 数据
"""

import os
import struct
import numpy as np
from scipy import signal
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import warnings

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 尝试导入 ObsPy
try:
    from obspy import read as obspy_read
    OBSPY_AVAILABLE = True
except ImportError:
    OBSPY_AVAILABLE = False
    warnings.warn("ObsPy not available, using custom SEGD reader")


class SEGDReader:
    """SEGD 文件自定义读取器 - 支持 2通道交错 16-bit Big-Endian"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.header_bytes = None
        self.traces_data = []       # List[np.ndarray], 每个通道一条
        self.traces_header = []
        self.sample_rate = 9250      # 从诊断确认
        self.num_channels = 2        # 诊断确认：2通道交错
        self.num_samples = 0
        self.data_offset = 4096      # 诊断确认：数据从偏移4096开始
        
    def read(self) -> bool:
        try:
            file_size = os.path.getsize(self.filename)
            
            with open(self.filename, 'rb') as f:
                # 读取头
                self.header_bytes = f.read(self.data_offset)
                self._parse_header()
                
                # 读取数据
                f.seek(self.data_offset)
                raw_data = f.read(file_size - self.data_offset)
            
            if len(raw_data) == 0:
                print(f"  ✗ 无数据")
                return False
            
            # 解析为 16-bit Big-Endian 有符号整数
            samples = np.frombuffer(raw_data, dtype='>i2')
            total_samples = len(samples)
            
            # 2通道交错分离: 偶数位置=Ch0, 奇数位置=Ch1
            # 确保偶数个样本
            if total_samples % 2 != 0:
                samples = samples[:-1]
                total_samples -= 1
            
            # 分离通道
            ch0 = samples[0::2].copy()  # 偶数索引
            ch1 = samples[1::2].copy()  # 奇数索引
            
            self.num_samples = len(ch0)
            
            self.traces_data = [ch0, ch1]
            self.traces_header = [
                {'channel': 0, 'label': 'Ch0 (辅助/参考)'},
                {'channel': 1, 'label': 'Ch1 (地震信号)'}
            ]
            
            # 统计信息
            print(f"✓ 成功读取 {Path(self.filename).name}")
            print(f"  - 通道数: {self.num_channels} (交错存储)")
            print(f"  - 每通道样本数: {self.num_samples:,}")
            print(f"  - 采样率: {self.sample_rate} Hz")
            print(f"  - 时长: {self.num_samples / self.sample_rate:.2f} 秒")
            print(f"  - Ch0: 范围 [{np.min(ch0):+d}, {np.max(ch0):+d}], 均值 {np.mean(ch0):.0f}")
            print(f"  - Ch1: 范围 [{np.min(ch1):+d}, {np.max(ch1):+d}], 均值 {np.mean(ch1):.0f}")
            
            return True
            
        except Exception as e:
            print(f"✗ 读取失败: {Path(self.filename).name}")
            print(f"  错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _parse_header(self):
        """从文件头解析采样率（双字节序验证）"""
        if len(self.header_bytes) < 12:
            return
        
        sr_be = struct.unpack('>H', self.header_bytes[10:12])[0]
        sr_le = struct.unpack('<H', self.header_bytes[10:12])[0]
        
        # 验证合理性
        for sr, bo in [(sr_be, 'BE'), (sr_le, 'LE')]:
            if 100 <= sr <= 50000:
                self.sample_rate = sr
                print(f"  - 检测到采样率: {sr} Hz ({bo})")
                return
        
        print(f"  - 使用默认采样率: {self.sample_rate} Hz")
    
    def get_traces_array(self) -> np.ndarray:
        """返回 (num_channels, num_samples) 数组"""
        if not self.traces_data:
            return np.array([])
        return np.array(self.traces_data)
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            'filename': str(Path(self.filename).name),
            'num_channels': self.num_channels,
            'num_samples': self.num_samples,
            'sample_rate': self.sample_rate,
            'duration': self.num_samples / self.sample_rate if self.sample_rate else 0,
            'traces_header': self.traces_header,
            'data_offset': self.data_offset,
            'ch0_stats': {
                'min': int(np.min(self.traces_data[0])),
                'max': int(np.max(self.traces_data[0])),
                'mean': float(np.mean(self.traces_data[0])),
                'std': float(np.std(self.traces_data[0])),
            },
            'ch1_stats': {
                'min': int(np.min(self.traces_data[1])),
                'max': int(np.max(self.traces_data[1])),
                'mean': float(np.mean(self.traces_data[1])),
                'std': float(np.std(self.traces_data[1])),
            }
        }


class SEGDVisualizer:
    """SEGD 数据可视化器 - 多面板综合视图"""
    
    @staticmethod
    def plot_comprehensive(data: np.ndarray, metadata: Dict, 
                           filename: str = None, save_path: str = None):
        """
        综合可视化：波形截面 + 时间序列 + 频谱
        
        Args:
            data: (num_channels, num_samples)
            metadata: 元数据
            filename: 文件名
            save_path: 保存路径
        """
        if data.size == 0:
            print("  无数据可绘制")
            return
        
        num_channels, num_samples = data.shape
        sample_rate = metadata.get('sample_rate', 9250)
        duration = num_samples / sample_rate
        
        # 创建 2x3 布局
        fig = plt.figure(figsize=(18, 12))
        
        # ===== 面板1: 地震记录截面图 (wiggle) =====
        # 只显示前 5 秒数据以看清波形
        display_secs = min(5.0, duration)
        display_samples = int(display_secs * sample_rate)
        
        ax1 = fig.add_subplot(2, 2, 1)
        time_seg = np.arange(display_samples) / sample_rate
        
        for i in range(num_channels):
            seg = data[i, :display_samples].astype(np.float64)
            seg_max = np.max(np.abs(seg))
            if seg_max > 0:
                seg = seg / seg_max * 0.4
            
            y_base = num_channels - 1 - i  # 反转使 Ch0 在上
            ax1.fill_between(time_seg, y_base, y_base + seg,
                            where=(seg >= 0), color='black', alpha=0.6, linewidth=0)
            ax1.fill_between(time_seg, y_base, y_base + seg,
                            where=(seg < 0), color='red', alpha=0.3, linewidth=0)
            ax1.plot(time_seg, y_base + seg, 'k-', linewidth=0.3)
        
        ax1.set_xlabel('Time (s)', fontsize=11)
        ax1.set_ylabel('Channel', fontsize=11)
        ax1.set_title(f'Wiggle Trace (first {display_secs}s) - {filename}', fontsize=12, fontweight='bold')
        ax1.set_yticks([1, 0])
        ax1.set_yticklabels(['Ch1 (Seismic)', 'Ch0 (Aux)'])
        ax1.set_ylim(-0.6, num_channels - 0.4)
        ax1.grid(True, alpha=0.3)
        
        # ===== 面板2: Ch1 完整时间序列 (地震信号) =====
        ax2 = fig.add_subplot(2, 2, 2)
        ch1_data = data[1].astype(np.float64)
        time_full = np.arange(num_samples) / sample_rate
        
        # 降采样以加速绘制
        if num_samples > 50000:
            step = num_samples // 50000
            idx = np.arange(0, num_samples, step)
            ax2.plot(time_full[idx], ch1_data[idx], 'b-', linewidth=0.3, alpha=0.7)
        else:
            ax2.plot(time_full, ch1_data, 'b-', linewidth=0.3, alpha=0.7)
        
        ax2.set_xlabel('Time (s)', fontsize=11)
        ax2.set_ylabel('Amplitude', fontsize=11)
        ax2.set_title(f'Ch1 Full Time Series ({duration:.1f}s)', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        # ===== 面板3: Ch1 放大前2秒 =====
        ax3 = fig.add_subplot(2, 2, 3)
        zoom_secs = min(2.0, duration)
        zoom_samples = int(zoom_secs * sample_rate)
        time_zoom = np.arange(zoom_samples) / sample_rate
        
        ax3.plot(time_zoom, ch1_data[:zoom_samples], 'k-', linewidth=0.5)
        ax3.fill_between(time_zoom, 0, ch1_data[:zoom_samples],
                         where=(ch1_data[:zoom_samples] >= 0), 
                         color='blue', alpha=0.3)
        ax3.fill_between(time_zoom, 0, ch1_data[:zoom_samples],
                         where=(ch1_data[:zoom_samples] < 0), 
                         color='red', alpha=0.3)
        
        ax3.set_xlabel('Time (s)', fontsize=11)
        ax3.set_ylabel('Amplitude', fontsize=11)
        ax3.set_title(f'Ch1 Zoom (first {zoom_secs}s)', fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        
        # ===== 面板4: 频谱分析 (FFT) =====
        ax4 = fig.add_subplot(2, 2, 4)
        
        for ch_idx in range(num_channels):
            ch_data = data[ch_idx].astype(np.float64)
            # 计算 PSD
            f, psd = signal.welch(ch_data, fs=sample_rate, 
                                  nperseg=min(8192, num_samples//4),
                                  scaling='density')
            # 只显示 0-500 Hz
            mask = f <= 500
            label = f'Ch{ch_idx}'
            color = 'orange' if ch_idx == 0 else 'blue'
            ax4.semilogy(f[mask], psd[mask], color=color, linewidth=1, 
                        alpha=0.8, label=label)
        
        ax4.set_xlabel('Frequency (Hz)', fontsize=11)
        ax4.set_ylabel('Power Spectral Density', fontsize=11)
        ax4.set_title('Power Spectrum (Welch PSD)', fontsize=12, fontweight='bold')
        ax4.legend(loc='upper right')
        ax4.grid(True, alpha=0.3, which='both')
        
        # 添加元数据文本框
        info = (
            f"File: {filename}\n"
            f"Sample Rate: {sample_rate} Hz\n"
            f"Duration: {duration:.1f}s\n"
            f"Channels: {num_channels}\n"
            f"Samples: {num_samples:,}/ch"
        )
        fig.text(0.02, 0.02, info, fontsize=9, family='monospace',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8),
                verticalalignment='bottom')
        
        plt.tight_layout(rect=[0, 0.08, 1, 1])
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"  ✓ 已保存: {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    @staticmethod
    def print_metadata(metadata: Dict):
        """打印元数据信息"""
        print("\n" + "="*70)
        print("  元数据摘要")
        print("="*70)
        print(f"  文件名:     {metadata.get('filename', 'N/A')}")
        print(f"  通道数:     {metadata.get('num_channels', 'N/A')}")
        print(f"  每通道样本: {metadata.get('num_samples', 0):,}")
        print(f"  采样率:     {metadata.get('sample_rate', 'N/A')} Hz")
        print(f"  时长:       {metadata.get('duration', 0):.1f} 秒")
        
        for key in ['ch0_stats', 'ch1_stats']:
            if key in metadata:
                s = metadata[key]
                print(f"  {key}: 范围 [{s['min']:+d}, {s['max']:+d}], "
                      f"均值={s['mean']:.0f}, 标准差={s['std']:.0f}")
        print("="*70)


def main():
    """主程序入口"""
    work_dir = Path(__file__).parent
    output_dir = work_dir / 'output'
    output_dir.mkdir(exist_ok=True)
    
    print("="*70)
    print("  SEGD 地震记录读取与可视化系统 v2.0")
    print("  格式: 2-Channel Interleaved, 16-bit Big-Endian")
    print("="*70)
    print(f"  工作目录: {work_dir}")
    print(f"  输出目录: {output_dir}\n")
    
    # 查找 SEGD 文件
    segd_files = sorted(work_dir.glob('*.segd'))
    print(f"✓ 找到 {len(segd_files)} 个 SEGD 文件\n")
    
    if not segd_files:
        print("未找到 SEGD 文件！")
        return
    
    visualizer = SEGDVisualizer()
    
    # 逐个处理
    for i, file_path in enumerate(segd_files, 1):
        filename = file_path.name
        print(f"[{i}/{len(segd_files)}] 处理: {filename}")
        print("-" * 50)
        
        # 检查文件是否可读
        if not os.access(str(file_path), os.R_OK):
            print(f"  ✗ 无法读取文件: {filename}")
            continue
        
        # 读取
        reader = SEGDReader(str(file_path))
        if not reader.read():
            continue
        
        data = reader.get_traces_array()
        metadata = reader.get_metadata()
        
        # 打印元数据
        visualizer.print_metadata(metadata)
        
        # 生成综合图表
        base_name = file_path.stem
        save_path = str(output_dir / f"{base_name}_comprehensive.png")
        visualizer.plot_comprehensive(data, metadata, filename, save_path)
        
        print()
    
    print("="*70)
    print(f"  ✓ 处理完成！图表保存到: {output_dir}")
    print("="*70)


if __name__ == '__main__':
    main()

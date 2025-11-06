#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将better_test.csv转换为Python列表格式
"""

import csv
from collections import defaultdict

def convert_csv_to_python_format(csv_file):
    """将CSV格式转换为Python列表格式"""
    
    # 符号映射：数字 -> 字母
    symbol_map = {'0': 'a', '1': 'b', '2': 'c'}
    
    # 存储每个trace的事件
    traces = defaultdict(list)
    
    # 读取CSV文件
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trace_id = row['id']
            symbol = symbol_map[row['symb']]
            duration = float(row['attr/f:duration'])
            
            traces[trace_id].append((symbol, duration))
    
    return traces

def main():
    # 转换数据
    traces = convert_csv_to_python_format('better_test.csv')
    
    print("# 🔄 CSV数据转换结果\n")
    
    # 方案1：所有序列作为正例
    print("## 方案1：所有序列作为正例")
    print("positive_samples = [")
    for trace_id, events in sorted(traces.items()):
        print(f"    {events},  # {trace_id}")
    print("]\n")
    print("negative_samples = []\n")
    
    # 方案2：根据时间区域分为正负例
    print("## 方案2：根据时间区域分为正负例")
    print("# 正例：早期时间模式 (1-3秒)")
    early_traces = []
    late_traces = []
    
    for trace_id, events in sorted(traces.items()):
        max_time = max(time for _, time in events)
        if max_time <= 4.0:  # 早期时间模式
            early_traces.append(events)
        else:  # 晚期时间模式
            late_traces.append(events)
    
    print("positive_samples = [")
    for events in early_traces:
        print(f"    {events},")
    print("]\n")
    
    print("# 负例：晚期时间模式 (5秒以上)")
    print("negative_samples = [")
    for events in late_traces:
        print(f"    {events},")
    print("]\n")
    
    # 方案3：根据序列长度分类
    print("## 方案3：根据序列特征分类")
    print("# 正例：多样化符号序列")
    print("# 负例：重复符号序列")
    
    diverse_traces = []
    repetitive_traces = []
    
    for trace_id, events in sorted(traces.items()):
        symbols = [symbol for symbol, _ in events]
        unique_symbols = len(set(symbols))
        
        if unique_symbols >= 3:  # 包含3种不同符号
            diverse_traces.append(events)
        else:  # 符号种类较少或重复
            repetitive_traces.append(events)
    
    print("positive_samples = [")
    for events in diverse_traces:
        print(f"    {events},")
    print("]\n")
    
    print("negative_samples = [")
    for events in repetitive_traces:
        print(f"    {events},")
    print("]\n")
    
    # 详细数据分析
    print("## 📊 数据分析")
    for trace_id, events in sorted(traces.items()):
        symbols = [symbol for symbol, _ in events]
        times = [time for _, time in events]
        print(f"{trace_id}: 符号={symbols}, 时间范围={min(times):.1f}-{max(times):.1f}秒")

if __name__ == "__main__":
    main() 
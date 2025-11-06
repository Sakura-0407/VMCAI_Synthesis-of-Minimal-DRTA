# 使用FlexFringe生成DRTA (Deterministic Real-time Timed Automaton) 指南

## 概述

FlexFringe是一个强大的自动机学习工具，支持从带时间戳的样本数据生成DRTA。本指南将展示如何处理带时间信息的数据来生成定时自动机。

## 数据格式

### CSV格式要求

FlexFringe支持CSV格式的输入数据，对于DRTA生成，需要以下列：

1. **timestamp**: 时间戳列，可命名为`timestamp`或`timestamp:time`
2. **id**: 轨迹标识符
3. **symb**: 符号/事件名称
4. **attr/f:duration**: 符号属性（如持续时间），使用`attr/f:`前缀表示浮点数属性
5. **tattr/f:deadline**: 轨迹属性（如截止时间），使用`tattr/f:`前缀表示浮点数属性

### 示例数据格式

```csv
timestamp:time, id, symb, attr/f:duration, tattr/f:deadline
0.0, trace1, start, 0.0, 10.0
1.5, trace1, event_a, 1.5, 10.0
3.2, trace1, event_b, 1.7, 10.0
5.8, trace1, end, 2.6, 10.0
0.0, trace2, start, 0.0, 8.0
2.1, trace2, event_a, 2.1, 8.0
2.9, trace2, event_c, 0.8, 8.0
4.5, trace2, end, 1.6, 8.0
```

## 配置文件

### RTI (Real-Time Inference) 配置

使用`ini/rti.ini`配置文件来生成实时自动机：

```ini
[default]
heuristic-name = rtiplus
data-name = rtiplus_data
state_count = 0
symbol_count = 0
satdfabound = 2000
largestblue = 1
sinkson = 0
sinkcount = 10
confidence_bound = 0.99
extend = 0
finalred =0
finalprob = 0
```

## 运行命令

### 基本命令

```bash
# 使用RTI配置处理时间数据
.\build\Release\flexfringe.exe --ini ini\rti.ini sample_timed_data.csv

# 指定输出文件名
.\build\Release\flexfringe.exe --ini ini\rti.ini --outputfile my_drta sample_timed_data.csv

# 使用特定启发式函数
.\build\Release\flexfringe.exe --heuristic-name rtiplus sample_timed_data.csv
```

### 高级参数

```bash
# 开启调试模式
.\build\Release\flexfringe.exe --ini ini\rti.ini --debug true sample_timed_data.csv

# 自定义置信度
.\build\Release\flexfringe.exe --heuristic-name rtiplus --confidence_bound 0.95 sample_timed_data.csv

# 设置状态和符号计数阈值
.\build\Release\flexfringe.exe --heuristic-name rtiplus --state_count 10 --symbol_count 5 sample_timed_data.csv
```

## 输出文件

运行成功后，FlexFringe会生成以下文件：

1. **`.ff.init.dot`**: 初始前缀树的DOT格式
2. **`.ff.init.json`**: 初始前缀树的JSON格式
3. **`.ff.final.dot`**: 最终DRTA的DOT格式
4. **`.ff.final.json`**: 最终DRTA的JSON格式

### DOT文件可视化

可以使用Graphviz将DOT文件转换为图像：

```bash
dot -Tpng sample_timed_data.csv.ff.final.dot -o drta.png
```

## 列类型说明

### 基本列类型
- `id`: 轨迹标识符
- `symb`: 符号名称  
- `type`: 符号类型
- `eval`: 评估标签

### 属性列类型
- `attr/f:name`: 符号浮点数属性
- `attr/d:name`: 符号离散属性
- `attr/s:name`: 符号可分割属性
- `attr/t:name`: 符号目标属性

### 轨迹属性列类型
- `tattr/f:name`: 轨迹浮点数属性
- `tattr/d:name`: 轨迹离散属性
- `tattr/s:name`: 轨迹可分割属性
- `tattr/t:name`: 轨迹目标属性

## 常见用例

### 1. 系统执行轨迹建模
对系统的执行序列进行建模，包含事件时间戳和持续时间。

### 2. 实时系统行为分析
分析实时系统的时间约束和截止时间要求。

### 3. 性能模型学习
从性能数据中学习系统的时间行为模式。

## 故障排除

### 常见问题

1. **"No data type found"**: 检查CSV头部格式是否正确
2. **解析错误**: 确保CSV文件格式符合要求，特别是属性列的语法
3. **没有生成输出文件**: 检查数据是否足够进行状态合并

### 调试建议

1. 使用`--debug true`参数获得详细输出
2. 检查`flexfringe.log`日志文件
3. 从简单的数据集开始测试
4. 验证CSV头部解析是否正确

## 高级功能

### 滑动窗口处理
```bash
.\build\Release\flexfringe.exe --slidingwindow true --swsize 5 --swstride 2 data.csv
```

### 概率建模
```bash
.\build\Release\flexfringe.exe --heuristic-name alergia --finalprob true data.csv
```

### SAT求解器
```bash
.\build\Release\flexfringe.exe --mode satsolver --satgreedy true data.csv
```

这个指南提供了使用FlexFringe从带时间的样本数据生成DRTA的完整流程。根据具体需求，可以调整参数和配置以获得最佳结果。 
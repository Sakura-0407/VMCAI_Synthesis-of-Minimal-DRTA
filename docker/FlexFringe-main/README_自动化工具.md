# DRTA自动化工具使用说明

## 概述

本项目提供了完整的DRTA (Deterministic Real-Time Automata) 自动化工具集，包括：
1. 时间序列数据自动生成
2. DRTA模型学习
3. 结果统计分析
4. 文件整理和报告生成

## 工具清单

### 1. 数据生成工具

#### `generate_simple_data.ps1`
- **功能**: 生成abbadingo格式的带时间属性数据
- **用法**: 
```powershell
.\generate_simple_data.ps1 -NumSamples 50 -AlphabetSize 4
```
- **参数**:
  - `NumSamples`: 样本数量 (默认: 50)
  - `AlphabetSize`: 字母表大小 (默认: 4) 
  - `MinLength`: 最小序列长度 (默认: 2)
  - `MaxLength`: 最大序列长度 (默认: 10)
  - `MinTime`: 最小时间值 (默认: 0.5)
  - `MaxTime`: 最大时间值 (默认: 3.0)
  - `OutputFile`: 输出文件名前缀

#### 生成的数据格式
```
50 4 1
1 5 0:1.2 1:0.8 2:1.5 1:0.7 3:2.1
1 3 0:0.9 2:1.3 3:1.8
0 4 2:2.1 1:1.4 0:0.9 3:1.7
```
- 第一行: `样本数 字母表大小 属性数`
- 后续行: `标签 长度 符号:时间 符号:时间 ...`

### 2. 统计分析工具

#### `drta_statistics.ps1`
- **功能**: 自动分析DRTA结果，生成统计报告
- **用法**:
```powershell
.\drta_statistics.ps1 -OutputPrefix "timed_samples_50_drta" -InputFile "timed_samples_50.dat"
```
- **功能**:
  - 自动统计状态数量
  - 提取运行时间信息
  - 创建标准化文件夹结构
  - 生成详细统计报告

### 3. 完整自动化流程

#### `simple_auto_drta.ps1`
- **功能**: 一键完成从数据生成到结果分析的完整流程
- **用法**:
```powershell
.\simple_auto_drta.ps1 -NumSamples 30 -ProjectName "my_experiment"
```

## 工作流程示例

### 手动执行步骤

1. **生成数据**:
```powershell
.\generate_simple_data.ps1 -NumSamples 50 -AlphabetSize 4 -OutputFile "experiment1"
```

2. **运行DRTA学习**:
```powershell
.\build\Release\flexfringe.exe --ini ini\rti.ini --outputfile experiment1_drta experiment1.csv
```

3. **分析结果**:
```powershell
.\drta_statistics.ps1 -OutputPrefix "experiment1_drta" -InputFile "experiment1.dat"
```

### 自动化执行

```powershell
.\simple_auto_drta.ps1 -NumSamples 50 -AlphabetSize 4 -ProjectName "experiment1"
```

## 输出文件结构

```
DRTA_Results_[项目名]/
├── Input_Data/
│   ├── [项目名].dat          # Abbadingo格式输入
│   └── [项目名].csv          # CSV格式输入  
├── Output_Files/
│   └── [项目名]_drta.json    # DRTA模型JSON
└── Visualizations/
    ├── [项目名]_drta.dot     # Graphviz DOT文件
    ├── [项目名]_drta.png     # PNG图像
    └── [项目名]_drta.svg     # SVG图像
```

## 数据格式支持

### Abbadingo格式
```
50 4 1
1 5 0:1.2 1:0.8 2:1.5 1:0.7 3:2.1
```

### CSV格式  
```
id,symb,attr/f:duration
trace1,0,1.2
trace1,1,0.8
trace1,2,1.5
```

## 性能参考

基于50样本的测试结果：
- **数据生成**: < 1秒
- **DRTA学习**: ~0.022秒
- **状态数量**: 通常30-40个状态
- **文件大小**: 
  - 输入数据: ~1KB
  - DOT文件: ~3KB  
  - PNG图像: ~50KB

## 故障排除

### 常见问题

1. **执行策略错误**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

2. **FlexFringe无法运行**:
   - 确保已编译: `cmake --build build --config Release`
   - 检查路径: `.\build\Release\flexfringe.exe --help`

3. **Graphviz错误**:
   - 确保已安装Graphviz
   - 添加到PATH环境变量

### 数据格式错误

如果FlexFringe报告解析错误：
1. 检查数据文件编码 (使用ASCII)
2. 验证格式: 每行符号:时间对格式正确
3. 确保头部信息匹配实际数据

## 自定义和扩展

### 修改数据生成模式

编辑`generate_simple_data.ps1`中的`Generate-Sequence`函数：

```powershell
function Generate-Sequence {
    param([int]$Length, [int]$AlphSize)
    # 添加自定义模式
    # 例如: 特定的时间分布、符号序列模式等
}
```

### 添加新的统计指标

在`drta_statistics.ps1`中添加自定义分析：

```powershell
# 例如: 计算转移概率分布
# 分析状态深度
# 计算模型复杂度指标
```

## 最佳实践

1. **批量实验**: 使用不同参数运行多次，比较结果
2. **结果验证**: 检查生成的可视化文件确认模型合理性  
3. **性能监控**: 记录不同数据规模下的运行时间
4. **数据备份**: 保存原始数据和配置文件

## 技术细节

- **算法**: RTI+ (Real-Time Interface Plus)
- **文件格式**: 支持abbadingo和CSV
- **可视化**: 使用Graphviz生成DOT/PNG/SVG
- **平台**: Windows PowerShell
- **依赖**: FlexFringe, Graphviz

---

📝 **说明**: 此工具集简化了DRTA研究的数据准备和分析流程，特别适合批量实验和快速原型开发。 
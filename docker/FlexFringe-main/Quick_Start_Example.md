# 🚀 DRTA统计脚本快速开始

## 简单示例演示

假设您刚刚使用FlexFringe完成了一次DRTA学习，现在想要统计结果和整理文件。

### 🔍 运行前检查
确保以下文件存在：
```
FlexFringe-main/
├── your_output_prefix.final.dot     (必需)
├── your_output_prefix.final.json    (会自动移动)
├── your_output_prefix.final.png     (会自动移动)
├── your_output_prefix.final.svg     (会自动移动)
├── your_output_prefix.init.dot      (会自动移动)
├── your_output_prefix.init.json     (会自动移动)
├── flexfringe.log                   (可选，用于时间统计)
└── drta_statistics.ps1              (统计脚本)
```

### 📋 一键执行示例

#### 基本用法：
```powershell
# 最简单的使用方法
.\drta_statistics.ps1 -OutputPrefix "timed_samples_50_drta"
```

#### 完整用法：
```powershell
# 包含输入文件和自定义文件夹名
.\drta_statistics.ps1 -OutputPrefix "timed_samples_50_drta" -InputFile "timed_samples_50.csv" -ResultFolder "MyAnalysis"
```

### 📊 期望输出

运行成功后，您将看到：

```
🚀 开始DRTA统计和文件整理...
📊 统计DRTA状态数...
   ✅ 发现 36 个状态
⏱️ 分析运行时间...
   ✅ 运行时间分析完成
📁 创建文件夹结构...
   ✅ 文件夹结构创建完成
📦 整理输出文件...
   ✅ 文件整理完成
📋 生成统计报告...
   ✅ 统计报告已保存到: timed_samples_50_drta_Results\DRTA_Statistics_Report.md

🎉 DRTA统计分析完成！

📊 关键统计数据:
   - 状态数: 36
   - 根状态样本: 50
   - 运行时间: 0.022 秒

📁 结果文件夹: timed_samples_50_drta_Results
📄 详细报告: timed_samples_50_drta_Results\DRTA_Statistics_Report.md
```

### 📁 生成的文件结构

```
timed_samples_50_drta_Results/
├── 📄 DRTA_Statistics_Report.md    (详细统计报告)
├── 📂 Input_Data/
│   └── timed_samples_50.csv        (原始输入文件)
├── 📂 Output_Files/
│   ├── timed_samples_50_drta.final.json
│   └── timed_samples_50_drta.init.json
└── 📂 Visualizations/
    ├── timed_samples_50_drta.final.dot
    ├── timed_samples_50_drta.init.dot
    ├── timed_samples_50_drta.final.png
    └── timed_samples_50_drta.final.svg
```

### 💡 下一步操作

1. **查看统计报告**：
   ```powershell
   notepad "timed_samples_50_drta_Results\DRTA_Statistics_Report.md"
   ```

2. **查看可视化图像**：
   ```powershell
   start "timed_samples_50_drta_Results\Visualizations\timed_samples_50_drta.final.png"
   ```

3. **分析JSON数据**：
   ```powershell
   Get-Content "timed_samples_50_drta_Results\Output_Files\timed_samples_50_drta.final.json" | ConvertFrom-Json
   ```

---
**提示**：如果您有多个实验要分析，可以批量处理：

```powershell
# 批量处理多个实验
$experiments = @("exp1_drta", "exp2_drta", "exp3_drta")
foreach ($exp in $experiments) {
    if (Test-Path "${exp}.final.dot") {
        .\drta_statistics.ps1 -OutputPrefix $exp
        Write-Host "完成处理: $exp" -ForegroundColor Green
    }
}
```
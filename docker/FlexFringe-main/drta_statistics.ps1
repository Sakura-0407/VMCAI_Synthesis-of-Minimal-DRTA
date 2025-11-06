# DRTA统计和文件整理自动化脚本
# 作者: AI Assistant
# 用途: 自动统计FlexFringe DRTA结果并整理输出文件

param(
    [Parameter(Mandatory=$true)]
    [string]$OutputPrefix,  # 输出文件前缀 (如: timed_samples_50_drta)
    
    [Parameter(Mandatory=$false)]
    [string]$InputFile = "",  # 原始输入文件
    
    [Parameter(Mandatory=$false)]
    [string]$ResultFolder = ""  # 结果文件夹名称，默认为 {OutputPrefix}_Results
)

# 设置默认值
if ($ResultFolder -eq "") {
    $ResultFolder = "${OutputPrefix}_Results"
}

Write-Host "🚀 开始DRTA统计和文件整理..." -ForegroundColor Green

# 1. 检查必要文件是否存在
$finalDotFile = "${OutputPrefix}.final.dot"
$logFile = "flexfringe.log"

if (-not (Test-Path $finalDotFile)) {
    Write-Error "错误: 找不到文件 $finalDotFile"
    exit 1
}

if (-not (Test-Path $logFile)) {
    Write-Warning "警告: 找不到日志文件 $logFile，将跳过运行时间统计"
}

# 2. 统计状态数
Write-Host "📊 统计DRTA状态数..." -ForegroundColor Yellow
$stateLines = Get-Content $finalDotFile | Select-String "^\s*\d+\s*\["
$stateCount = $stateLines.Count
$stateNumbers = @()
foreach ($line in $stateLines) {
    if ($line -match "^\s*(\d+)\s*\[") {
        $stateNumbers += [int]$Matches[1]
    }
}
$stateNumbers = $stateNumbers | Sort-Object

Write-Host "   ✅ 发现 $stateCount 个状态" -ForegroundColor Green

# 3. 分析主要状态
$rootStateInfo = Get-Content $finalDotFile | Select-String "0 \[ label=.*#(\d+)"
$mainEndStateInfo = Get-Content $finalDotFile | Select-String "29 \[ label=.*#(\d+)"

$rootSamples = 0
$mainEndSamples = 0

if ($rootStateInfo -match "#(\d+)") {
    $rootSamples = [int]$Matches[1]
}

if ($mainEndStateInfo -match "#(\d+)") {
    $mainEndSamples = [int]$Matches[1]
}

# 4. 提取运行时间信息
$startTime = ""
$endTime = ""
$totalTime = ""
$aptaTime = ""

if (Test-Path $logFile) {
    Write-Host "⏱️ 分析运行时间..." -ForegroundColor Yellow
    $logContent = Get-Content $logFile
    
    # 查找最后一次运行的时间信息
    $lastRun = $logContent | Select-String "Starting flexfringe run" | Select-Object -Last 1
    if ($lastRun) {
        $runIndex = [array]::IndexOf($logContent, $lastRun.Line)
        $runSection = $logContent[$runIndex..($logContent.Length-1)]
        
        $startMatch = $runSection | Select-String "(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}).*Starting flexfringe run" | Select-Object -First 1
        $endMatch = $runSection | Select-String "(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}).*Ending flexfringe run" | Select-Object -First 1
        $aptaMatch = $runSection | Select-String "\(\s*(\d+\.\d+)s\).*Creating APTA" | Select-Object -First 1
        
        if ($startMatch -and $startMatch.Line -match "(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})") {
            $startTime = $Matches[1]
        }
        
        if ($endMatch -and $endMatch.Line -match "(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})") {
            $endTime = $Matches[1]
        }
        
        if ($aptaMatch -and $aptaMatch.Line -match "\(\s*(\d+\.\d+)s\)") {
            $aptaTime = $Matches[1]
        }
        
        # 计算总时间
        if ($startTime -and $endTime) {
            $start = [datetime]::ParseExact($startTime, "yyyy-MM-dd HH:mm:ss.fff", $null)
            $end = [datetime]::ParseExact($endTime, "yyyy-MM-dd HH:mm:ss.fff", $null)
            $duration = $end - $start
            $totalTime = "{0:F3}" -f $duration.TotalSeconds
        }
    }
    
    Write-Host "   ✅ 运行时间分析完成" -ForegroundColor Green
}

# 5. 创建结果文件夹结构
Write-Host "📁 创建文件夹结构..." -ForegroundColor Yellow

$folders = @("$ResultFolder", "$ResultFolder\Input_Data", "$ResultFolder\Output_Files", "$ResultFolder\Visualizations")
foreach ($folder in $folders) {
    if (-not (Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder | Out-Null
    }
}

Write-Host "   ✅ 文件夹结构创建完成" -ForegroundColor Green

# 6. 移动文件
Write-Host "📦 整理输出文件..." -ForegroundColor Yellow

# 移动输入文件
if ($InputFile -and (Test-Path $InputFile)) {
    Move-Item $InputFile "$ResultFolder\Input_Data\" -Force
}

# 移动JSON文件
$jsonFiles = Get-ChildItem "${OutputPrefix}.*.json" -ErrorAction SilentlyContinue
foreach ($file in $jsonFiles) {
    Move-Item $file.FullName "$ResultFolder\Output_Files\" -Force
}

# 移动可视化文件
$vizFiles = Get-ChildItem "${OutputPrefix}.*.dot", "${OutputPrefix}.*.png", "${OutputPrefix}.*.svg" -ErrorAction SilentlyContinue
foreach ($file in $vizFiles) {
    Move-Item $file.FullName "$ResultFolder\Visualizations\" -Force
}

Write-Host "   ✅ 文件整理完成" -ForegroundColor Green

# 7. 生成统计报告
Write-Host "📋 生成统计报告..." -ForegroundColor Yellow

$currentDate = Get-Date -Format "yyyy年M月d日 HH:mm"
$stateListStr = ($stateNumbers -join ", ")

$reportContent = @"
# DRTA 统计报告
## FlexFringe 自动机学习结果

### 📊 基本信息
- **分析时间**: $currentDate
- **算法**: RTI+ (Real-Time Interface Plus)
- **输出前缀**: $OutputPrefix
- **结果文件夹**: $ResultFolder

### 🔢 DRTA结构统计
- **总状态数**: **$stateCount** 个状态
- **状态编号**: $stateListStr
- **根状态样本数**: $rootSamples
- **主要终止状态样本数**: $mainEndSamples

### ⏱️ 运行性能统计
"@

if ($startTime) {
    $reportContent += @"
- **开始时间**: $startTime
- **结束时间**: $endTime
- **总运行时间**: $totalTime 秒
- **APTA创建时间**: $aptaTime 秒
"@
} else {
    $reportContent += @"
- **运行时间**: 无法从日志文件中提取
"@
}

$reportContent += @"

### 📁 输出文件结构
``````
$ResultFolder/
├── Input_Data/           (输入数据文件)
├── Output_Files/         (JSON格式输出)
└── Visualizations/       (图形可视化文件)
``````

### 📈 文件统计
"@

# 统计各文件夹中的文件
$inputFiles = Get-ChildItem "$ResultFolder\Input_Data" -ErrorAction SilentlyContinue
$outputFiles = Get-ChildItem "$ResultFolder\Output_Files" -ErrorAction SilentlyContinue
$vizFiles = Get-ChildItem "$ResultFolder\Visualizations" -ErrorAction SilentlyContinue

$reportContent += @"
- **输入文件**: $($inputFiles.Count) 个
- **输出文件**: $($outputFiles.Count) 个
- **可视化文件**: $($vizFiles.Count) 个

### 💡 分析总结
- **状态压缩效率**: 有效将复杂序列压缩为 $stateCount 个关键状态
- **主要模式识别**: $([math]::Round($mainEndSamples / $rootSamples * 100, 1))% 的样本收敛到主要终止状态
"@

if ($totalTime) {
    $samplesPerSecond = [math]::Round($rootSamples / [double]$totalTime, 0)
    $reportContent += @"
- **处理效率**: $samplesPerSecond 样本/秒
"@
}

$reportContent += @"

---
*报告由自动化脚本生成于: $currentDate*
*脚本版本: DRTA Statistics v1.0*
"@

# 保存报告
$reportPath = "$ResultFolder\DRTA_Statistics_Report.md"
$reportContent | Out-File -FilePath $reportPath -Encoding UTF8

Write-Host "   ✅ 统计报告已保存到: $reportPath" -ForegroundColor Green

# 8. 显示最终结果
Write-Host ""
Write-Host "🎉 DRTA统计分析完成！" -ForegroundColor Green
Write-Host ""
Write-Host "📊 关键统计数据:" -ForegroundColor Cyan
Write-Host "   - 状态数: $stateCount" -ForegroundColor White
Write-Host "   - 根状态样本: $rootSamples" -ForegroundColor White
if ($totalTime) {
    Write-Host "   - 运行时间: $totalTime 秒" -ForegroundColor White
}
Write-Host ""
Write-Host "📁 结果文件夹: $ResultFolder" -ForegroundColor Cyan
Write-Host "📄 详细报告: $reportPath" -ForegroundColor Cyan
Write-Host ""

# 显示文件夹结构
Write-Host "🗂️ 文件夹结构:" -ForegroundColor Cyan
try {
    tree $ResultFolder /F
} catch {
    Get-ChildItem $ResultFolder -Recurse | Format-Table Name, Length, LastWriteTime
} 
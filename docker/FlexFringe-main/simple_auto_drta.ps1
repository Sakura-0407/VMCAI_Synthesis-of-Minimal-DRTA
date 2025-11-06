# 简化版DRTA自动化流程
param(
    [int]$NumSamples = 30,
    [int]$AlphabetSize = 4,
    [string]$ProjectName = "simple_test"
)

Write-Host "开始DRTA自动化流程..." -ForegroundColor Green
Write-Host "项目: $ProjectName, 样本: $NumSamples" -ForegroundColor Cyan

# 步骤1: 生成数据
Write-Host "`n1. 生成数据..." -ForegroundColor Yellow

function Generate-Sequence {
    param([int]$Length, [int]$AlphSize)
    $sequence = @()
    for ($i = 0; $i -lt $Length; $i++) {
        $symbol = Get-Random -Minimum 0 -Maximum $AlphSize
        $time = [math]::Round((Get-Random -Minimum 0.0 -Maximum 1.0) * 2.5 + 0.5, 1)
        $sequence += "${symbol}:${time}"
    }
    return $sequence
}

$data = @()
$data += "$NumSamples $AlphabetSize 1"

$positiveCount = [math]::Round($NumSamples * 0.8)
$negativeCount = $NumSamples - $positiveCount

# 生成正例
for ($i = 0; $i -lt $positiveCount; $i++) {
    $length = Get-Random -Minimum 2 -Maximum 8
    $sequence = Generate-Sequence -Length $length -AlphSize $AlphabetSize
    $line = "1 $length " + ($sequence -join " ")
    $data += $line
}

# 生成负例
for ($i = 0; $i -lt $negativeCount; $i++) {
    $length = Get-Random -Minimum 2 -Maximum 8
    $sequence = Generate-Sequence -Length $length -AlphSize $AlphabetSize
    $line = "0 $length " + ($sequence -join " ")
    $data += $line
}

# 保存数据
$dataFile = "${ProjectName}.dat"
$data | Out-File -FilePath $dataFile -Encoding ASCII
Write-Host "  数据保存: $dataFile" -ForegroundColor Green

# 步骤2: 生成CSV格式
Write-Host "`n2. 生成CSV..." -ForegroundColor Yellow

$csvData = @()
$csvData += "id,symb,attr/f:duration"

$traceId = 1
foreach ($line in $data[1..($data.Length-1)]) {
    $parts = $line.Split(' ')
    $length = [int]$parts[1]
    
    for ($i = 2; $i -lt (2 + $length); $i++) {
        $symbolTime = $parts[$i].Split(':')
        $symbol = $symbolTime[0]
        $time = $symbolTime[1]
        $csvData += "trace${traceId},${symbol},${time}"
    }
    $traceId++
}

$csvFile = "${ProjectName}.csv"
$csvData | Out-File -FilePath $csvFile -Encoding UTF8
Write-Host "  CSV保存: $csvFile" -ForegroundColor Green

# 步骤3: 运行DRTA
Write-Host "`n3. 运行DRTA学习..." -ForegroundColor Yellow

$startTime = Get-Date
$drtaOutput = "${ProjectName}_drta"

Write-Host "  尝试CSV格式..." -ForegroundColor Cyan
$result = & .\build\Release\flexfringe.exe --ini ini\rti.ini --outputfile $drtaOutput $csvFile 2>&1
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host "  CSV失败，尝试Abbadingo格式..." -ForegroundColor Yellow
    $result = & .\build\Release\flexfringe.exe --ini ini\rti.ini --outputfile $drtaOutput $dataFile 2>&1
    $exitCode = $LASTEXITCODE
}

if ($exitCode -eq 0) {
    $endTime = Get-Date
    $elapsed = ($endTime - $startTime).TotalSeconds
    Write-Host "  DRTA学习成功！用时: $([math]::Round($elapsed, 3))秒" -ForegroundColor Green
} else {
    Write-Host "  DRTA学习失败！" -ForegroundColor Red
    Write-Host "  错误: $result" -ForegroundColor Red
    exit
}

# 步骤4: 统计结果
Write-Host "`n4. 统计分析..." -ForegroundColor Yellow

$outputFiles = Get-ChildItem -Path . -Name "${drtaOutput}*"
Write-Host "  输出文件:" -ForegroundColor Cyan
$outputFiles | ForEach-Object { Write-Host "    $_" }

$stateCount = 0
$dotFile = "${drtaOutput}.dot"
if (Test-Path $dotFile) {
    $dotContent = Get-Content $dotFile
    $stateLines = $dotContent | Where-Object { $_ -match '^\s*\d+\s*\[' }
    $stateCount = $stateLines.Count
    Write-Host "  状态数量: $stateCount" -ForegroundColor Green
}

# 步骤5: 整理文件
Write-Host "`n5. 整理文件..." -ForegroundColor Yellow

$outputDir = "DRTA_Results_${ProjectName}"
if (Test-Path $outputDir) { Remove-Item $outputDir -Recurse -Force }

New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
New-Item -ItemType Directory -Path "$outputDir\Input_Data" -Force | Out-Null
New-Item -ItemType Directory -Path "$outputDir\Output_Files" -Force | Out-Null
New-Item -ItemType Directory -Path "$outputDir\Visualizations" -Force | Out-Null

Move-Item $dataFile "$outputDir\Input_Data\" -Force
Move-Item $csvFile "$outputDir\Input_Data\" -Force

Get-ChildItem -Path . -Name "${drtaOutput}*" | ForEach-Object {
    $file = $_
    if ($file -match '\.(json)$') {
        Move-Item $file "$outputDir\Output_Files\" -Force
    } elseif ($file -match '\.(dot|png|svg)$') {
        Move-Item $file "$outputDir\Visualizations\" -Force
    }
}

Write-Host "  文件整理完成: $outputDir" -ForegroundColor Green

# 生成简单报告
$reportFile = "$outputDir\report.txt"
$report = "DRTA结果报告`n" +
"项目: $ProjectName`n" +
"时间: $(Get-Date)`n" +
"样本数: $NumSamples`n" +
"状态数: $stateCount`n" +
"运行时间: $([math]::Round($elapsed, 3))秒"

$report | Out-File -FilePath $reportFile -Encoding UTF8

Write-Host "`n完成！" -ForegroundColor Green
Write-Host "结果目录: $outputDir" -ForegroundColor Yellow
Write-Host "状态数量: $stateCount" -ForegroundColor Yellow
Write-Host "运行时间: $([math]::Round($elapsed, 3))秒" -ForegroundColor Yellow 
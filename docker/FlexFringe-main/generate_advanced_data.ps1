# 高级时间数据生成脚本 - 简化版
param(
    [Parameter(Mandatory=$true)]
    [int]$NumSamples,
    
    [Parameter(Mandatory=$true)] 
    [int]$AlphabetSize,
    
    [int]$MinLength = 2,
    [int]$MaxLength = 10,
    [double]$MinTime = 0.5,
    [double]$MaxTime = 3.0,
    [double]$PositiveRatio = 0.8,
    [string]$OutputFile = "",
    [switch]$GenerateCSV
)

Write-Host "🎲 开始生成高级时间数据..." -ForegroundColor Green

# 设置默认输出文件名
if ($OutputFile -eq "") {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $OutputFile = "advanced_data_${NumSamples}samples_${timestamp}"
}

Write-Host "📊 数据生成参数:" -ForegroundColor Cyan
Write-Host "   - 样本数量: $NumSamples" -ForegroundColor White
Write-Host "   - 字母表大小: $AlphabetSize" -ForegroundColor White
Write-Host "   - 序列长度: $MinLength - $MaxLength" -ForegroundColor White
Write-Host "   - 时间属性范围: $MinTime - $MaxTime" -ForegroundColor White
Write-Host "   - 正例比例: $([math]::Round($PositiveRatio * 100, 1))%" -ForegroundColor White

# 生成序列函数
function Generate-Sequence {
    param([int]$Length, [int]$AlphSize, [double]$MinT, [double]$MaxT)
    
    $sequence = @()
    for ($i = 0; $i -lt $Length; $i++) {
        $symbol = Get-Random -Minimum 0 -Maximum $AlphSize
        $time = [math]::Round((Get-Random -Minimum 0.0 -Maximum 1.0) * ($MaxT - $MinT) + $MinT, 1)
        $sequence += "${symbol}:${time}"
    }
    return $sequence
}

# 模式化序列生成
function Generate-PatternedSequence {
    param([int]$Length, [int]$AlphSize, [double]$MinT, [double]$MaxT)
    
    $patterns = @("increasing", "repeating", "bounded")
    $pattern = $patterns[(Get-Random -Minimum 0 -Maximum $patterns.Length)]
    
    $sequence = @()
    for ($i = 0; $i -lt $Length; $i++) {
        switch ($pattern) {
            "increasing" { $symbol = $i % $AlphSize }
            "repeating" { $symbol = ($i % 3) % $AlphSize }
            "bounded" { 
                if ($i -eq 0) { $symbol = 0 }
                elseif ($i -eq $Length - 1) { $symbol = $AlphSize - 1 }
                else { $symbol = Get-Random -Minimum 1 -Maximum ($AlphSize - 1) }
            }
        }
        
        $time = [math]::Round((Get-Random -Minimum 0.0 -Maximum 1.0) * ($MaxT - $MinT) + $MinT, 1)
        $sequence += "${symbol}:${time}"
    }
    return $sequence
}

Write-Host "🔄 生成数据中..." -ForegroundColor Yellow

# 生成数据
$data = @()
$header = "$NumSamples $AlphabetSize 1"
$data += $header

$positiveCount = [math]::Round($NumSamples * $PositiveRatio)
$negativeCount = $NumSamples - $positiveCount

Write-Host "   - 正例数量: $positiveCount" -ForegroundColor Green
Write-Host "   - 负例数量: $negativeCount" -ForegroundColor Red

# 生成正例
for ($i = 0; $i -lt $positiveCount; $i++) {
    $length = Get-Random -Minimum $MinLength -Maximum ($MaxLength + 1)
    
    # 60% 概率使用模式化序列
    if ((Get-Random -Minimum 0.0 -Maximum 1.0) -lt 0.6) {
        $sequence = Generate-PatternedSequence -Length $length -AlphSize $AlphabetSize -MinT $MinTime -MaxT $MaxTime
    } else {
        $sequence = Generate-Sequence -Length $length -AlphSize $AlphabetSize -MinT $MinTime -MaxT $MaxTime
    }
    
    $line = "1 $length " + ($sequence -join " ")
    $data += $line
}

# 生成负例
for ($i = 0; $i -lt $negativeCount; $i++) {
    $length = Get-Random -Minimum $MinLength -Maximum ($MaxLength + 1)
    $sequence = Generate-Sequence -Length $length -AlphSize $AlphabetSize -MinT $MinTime -MaxT $MaxTime
    
    $line = "0 $length " + ($sequence -join " ")
    $data += $line
}

# 保存abbadingo格式
$datFile = "${OutputFile}.dat"
$data | Out-File -FilePath $datFile -Encoding ASCII
Write-Host "   ✅ 已保存: $datFile" -ForegroundColor Green

# 生成CSV格式
if ($GenerateCSV) {
    Write-Host "📄 生成CSV格式..." -ForegroundColor Yellow
    
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
    
    $csvFile = "${OutputFile}.csv"
    $csvData | Out-File -FilePath $csvFile -Encoding UTF8
    Write-Host "   ✅ 已保存: $csvFile" -ForegroundColor Green
}

# 生成统计信息
Write-Host ""
Write-Host "📈 数据统计:" -ForegroundColor Cyan

$totalSymbols = 0
$totalTime = 0.0
$sequenceLengths = @()

foreach ($line in $data[1..($data.Length-1)]) {
    $parts = $line.Split(' ')
    $length = [int]$parts[1]
    $sequenceLengths += $length
    $totalSymbols += $length
    
    for ($i = 2; $i -lt (2 + $length); $i++) {
        $time = [double]($parts[$i].Split(':')[1])
        $totalTime += $time
    }
}

$avgLength = [math]::Round(($sequenceLengths | Measure-Object -Average).Average, 2)
$avgTime = [math]::Round($totalTime / $totalSymbols, 2)

Write-Host "   - 总符号数: $totalSymbols" -ForegroundColor White
Write-Host "   - 平均序列长度: $avgLength" -ForegroundColor White
Write-Host "   - 平均时间属性: $avgTime" -ForegroundColor White

# 符号分布统计
$symbolCounts = @{}
for ($i = 0; $i -lt $AlphabetSize; $i++) { $symbolCounts[$i] = 0 }

foreach ($line in $data[1..($data.Length-1)]) {
    $parts = $line.Split(' ')
    $length = [int]$parts[1]
    
    for ($i = 2; $i -lt (2 + $length); $i++) {
        $symbol = [int]($parts[$i].Split(':')[0])
        $symbolCounts[$symbol]++
    }
}

Write-Host ""
Write-Host "🔢 符号分布:" -ForegroundColor Cyan
for ($i = 0; $i -lt $AlphabetSize; $i++) {
    $percentage = [math]::Round($symbolCounts[$i] / $totalSymbols * 100, 1)
    Write-Host "   - 符号 $i : $($symbolCounts[$i]) 次 ($percentage%)" -ForegroundColor White
}

Write-Host ""
Write-Host "🎉 数据生成完成！" -ForegroundColor Green
Write-Host ""
Write-Host "📁 生成的文件:" -ForegroundColor Cyan
Write-Host "   - 数据文件: $datFile" -ForegroundColor White
if ($GenerateCSV) {
    Write-Host "   - CSV文件: $csvFile" -ForegroundColor White
}

Write-Host ""
Write-Host "🚀 下一步建议:" -ForegroundColor Cyan
$drtaOutput = "${OutputFile}_drta"
Write-Host "   FlexFringe: 运行flexfringe处理数据" -ForegroundColor Yellow
Write-Host "   统计分析: 运行drta_statistics.ps1分析结果" -ForegroundColor Yellow 
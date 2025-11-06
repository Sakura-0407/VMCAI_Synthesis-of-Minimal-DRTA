# Simple timed data generator for DRTA
param(
    [int]$NumSamples = 50,
    [int]$AlphabetSize = 4,
    [int]$MinLength = 2,
    [int]$MaxLength = 10,
    [double]$MinTime = 0.5,
    [double]$MaxTime = 3.0,
    [string]$OutputFile = "generated_data",
    [switch]$GenerateCSV
)

Write-Host "Generating timed data..." -ForegroundColor Green
Write-Host "Samples: $NumSamples, Alphabet: $AlphabetSize, Length: $MinLength-$MaxLength" -ForegroundColor White

# Generate random sequence
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

# Create data
$data = @()
$data += "$NumSamples $AlphabetSize 1"

# Generate positive samples (80%)
$positiveCount = [math]::Round($NumSamples * 0.8)
for ($i = 0; $i -lt $positiveCount; $i++) {
    $length = Get-Random -Minimum $MinLength -Maximum ($MaxLength + 1)
    $sequence = Generate-Sequence -Length $length -AlphSize $AlphabetSize -MinT $MinTime -MaxT $MaxTime
    $line = "1 $length " + ($sequence -join " ")
    $data += $line
}

# Generate negative samples (20%)
$negativeCount = $NumSamples - $positiveCount
for ($i = 0; $i -lt $negativeCount; $i++) {
    $length = Get-Random -Minimum $MinLength -Maximum ($MaxLength + 1)
    $sequence = Generate-Sequence -Length $length -AlphSize $AlphabetSize -MinT $MinTime -MaxT $MaxTime
    $line = "0 $length " + ($sequence -join " ")
    $data += $line
}

# Save abbadingo format
$datFile = "${OutputFile}.dat"
$data | Out-File -FilePath $datFile -Encoding ASCII
Write-Host "Saved: $datFile" -ForegroundColor Green

# Generate CSV if requested
if ($GenerateCSV) {
    Write-Host "Generating CSV format..." -ForegroundColor Yellow
    
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
    Write-Host "Saved: $csvFile" -ForegroundColor Green
}

Write-Host "Generation complete!" -ForegroundColor Green
Write-Host "Positive samples: $positiveCount, Negative: $negativeCount" -ForegroundColor White

# Show statistics
$totalSymbols = 0
foreach ($line in $data[1..($data.Length-1)]) {
    $parts = $line.Split(' ')
    $length = [int]$parts[1]
    $totalSymbols += $length
}

Write-Host "Total symbols: $totalSymbols" -ForegroundColor Cyan

# Show first few lines
Write-Host "`nFirst 3 data lines:" -ForegroundColor Cyan
$data[1..3] | ForEach-Object { Write-Host "  $_" -ForegroundColor White }

Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Run FlexFringe: flexfringe.exe --ini ini\rti.ini --outputfile ${OutputFile}_drta $datFile"
Write-Host "2. Analyze results: drta_statistics.ps1 -OutputPrefix ${OutputFile}_drta -InputFile $datFile" 
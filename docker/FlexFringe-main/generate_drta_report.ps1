# DRTA Analysis Report Generator
# Automatically generates analysis reports for DRTA results
# Author: FlexFringe Analysis Tool
# Usage: .\generate_drta_report.ps1 -OutputPrefix "model_name" -InputFile "data.csv"

param(
    [Parameter(Mandatory=$true)]
    [string]$OutputPrefix,
    
    [Parameter(Mandatory=$true)]
    [string]$InputFile,
    
    [string]$ResultFolder = "",
    [string]$ReportName = ""
)

Write-Host "Generating DRTA Analysis Report..." -ForegroundColor Green

# Set default values
if ($ReportName -eq "") {
    $ReportName = "${OutputPrefix}_Analysis_Report"
}

if ($ResultFolder -eq "") {
    $ResultFolder = "DRTA_Results_${OutputPrefix}"
}

$currentDate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$reportFile = "${ResultFolder}\${ReportName}.md"

# Extract key metrics
Write-Host "Extracting metrics..." -ForegroundColor Yellow

# 1. Count states from DOT file with detailed analysis
$dotFile = "${OutputPrefix}.final.dot"
$stateCount = 0
$finalStates = 0
$transitions = 0
$dotAnalysis = @{
    "TotalStates" = 0
    "FinalStates" = 0
    "Transitions" = 0
    "MaxStateNumber" = 0
    "StateNumbers" = @()
}

if (Test-Path $dotFile) {
    Write-Host "  Analyzing DOT file structure..." -ForegroundColor Gray
    $dotContent = Get-Content $dotFile
    
    # Count states (nodes with label attribute)
    $stateLines = $dotContent | Select-String "^\s*\d+\s*\[\s*label="
    $stateCount = $stateLines.Count
    $dotAnalysis.TotalStates = $stateCount
    
    # Debug output
    Write-Host "    Found $stateCount state definitions in DOT file" -ForegroundColor Gray
    
    # Extract state numbers and find max
    $stateNumbers = @()
    foreach ($line in $stateLines) {
        if ($line -match "^\s*(\d+)\s*\[\s*label=") {
            $stateNumbers += [int]$matches[1]
        }
    }
    $dotAnalysis.StateNumbers = $stateNumbers
    if ($stateNumbers.Count -gt 0) {
        $dotAnalysis.MaxStateNumber = ($stateNumbers | Measure-Object -Maximum).Maximum
    }
    
    # Count final states (states marked with "fin:")
    $finalStateLines = $dotContent | Select-String "fin:"
    $finalStates = $finalStateLines.Count
    $dotAnalysis.FinalStates = $finalStates
    
    # Count transitions (edges)
    $transitionLines = $dotContent | Select-String "^\s*\d+\s*->\s*\d+"
    $transitions = $transitionLines.Count
    $dotAnalysis.Transitions = $transitions
    
    Write-Host "    States: $stateCount, Final States: $finalStates, Transitions: $transitions" -ForegroundColor Gray
}

# 2. Extract runtime from log with multiple patterns
$logFile = "flexfringe.log"
$runtime = "Unknown"
$runtimeDetails = @{
    "TotalRuntime" = "Unknown"
    "LearningTime" = "Unknown"
    "APTACreationTime" = "Unknown"
    "StartTime" = "Unknown"
    "EndTime" = "Unknown"
}

if (Test-Path $logFile) {
    Write-Host "  Analyzing FlexFringe log..." -ForegroundColor Gray
    $logContent = Get-Content $logFile | Select-Object -Last 100
    
    # Find the most recent complete run
    $runLines = @()
    $inCurrentRun = $false
    
    for ($i = $logContent.Count - 1; $i -ge 0; $i--) {
        $line = $logContent[$i]
        if ($line -match "Ending flexfringe run normally") {
            $inCurrentRun = $true
            $runLines += $line
        } elseif ($line -match "Starting flexfringe run" -and $inCurrentRun) {
            $runLines += $line
            break
        } elseif ($inCurrentRun) {
            $runLines += $line
        }
    }
    
    # Reverse to get chronological order
    [array]::Reverse($runLines)
    
    # Extract timing information
    foreach ($line in $runLines) {
        # Total runtime at end
        if ($line -match "\(\s*([0-9.]+)s\).*Ending flexfringe run normally") {
            $runtime = $matches[1] + " seconds"
            $runtimeDetails.TotalRuntime = $matches[1] + "s"
        }
        
        # APTA creation time
        if ($line -match "\(\s*([0-9.]+)s\).*Creating APTA") {
            $runtimeDetails.APTACreationTime = $matches[1] + "s"
        }
        
        # Greedy mode start time
        if ($line -match "\(\s*([0-9.]+)s\).*Greedy mode selected") {
            $runtimeDetails.LearningTime = $matches[1] + "s (start)"
        }
        
        # Extract timestamps
        if ($line -match "(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}).*Starting flexfringe") {
            $runtimeDetails.StartTime = $matches[1]
        }
        if ($line -match "(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}).*Ending flexfringe") {
            $runtimeDetails.EndTime = $matches[1]
        }
    }
    
    Write-Host "    Runtime: $runtime" -ForegroundColor Gray
}

# 3. Get file sizes
$jsonFile = "${OutputPrefix}.final.json"
$jsonSize = "Unknown"
if (Test-Path $jsonFile) {
    $size = (Get-Item $jsonFile).Length
    $jsonSize = "{0:N0} bytes ({1:N1} KB)" -f $size, ($size/1KB)
}

$dotSize = "Unknown" 
if (Test-Path $dotFile) {
    $size = (Get-Item $dotFile).Length
    $dotSize = "{0:N0} bytes ({1:N1} KB)" -f $size, ($size/1KB)
}

# 4. Analyze input data
$inputSamples = "Unknown"
$inputSymbols = "Unknown"
$inputFormat = "Unknown"

if (Test-Path $InputFile) {
    $inputFormat = if ($InputFile -match "\.csv$") { "CSV" } else { "Abbadingo" }
    
    if ($inputFormat -eq "CSV") {
        $lines = Get-Content $InputFile
        # Count unique trace IDs (sequences)
        $traceIds = @()
        foreach ($line in $lines[1..($lines.Count-1)]) {
            if ($line -match "^([^,]+),") {
                $traceId = $matches[1]
                if ($traceIds -notcontains $traceId) {
                    $traceIds += $traceId
                }
            }
        }
        $inputSamples = $traceIds.Count
        
        # Extract unique symbols
        $symbols = @()
        foreach ($line in $lines[1..($lines.Count-1)]) {
            if ($line -match "^[^,]+,(\d+),") {
                $symbols += $matches[1]
            }
        }
        $inputSymbols = ($symbols | Sort-Object -Unique).Count
    } else {
        # Abbadingo format
        $firstLine = (Get-Content $InputFile -TotalCount 1).Split(' ')
        if ($firstLine.Count -ge 2) {
            $inputSamples = $firstLine[0]
            $inputSymbols = $firstLine[1]
        }
    }
}

# 5. Calculate performance metrics
$statesPerSample = "N/A"
if ($stateCount -gt 0 -and $inputSamples -ne "Unknown" -and $inputSamples -gt 0) {
    $ratio = [math]::Round($stateCount / [int]$inputSamples, 2)
    $statesPerSample = "$ratio states/sample"
}

$runtimeMs = "Unknown"
if ($runtime -ne "Unknown" -and $runtime -match "([0-9.]+) seconds") {
    $seconds = [double]$matches[1]
    $runtimeMs = "{0:N0} ms" -f ($seconds * 1000)
}

# Generate report
Write-Host "Generating report: $reportFile" -ForegroundColor Yellow

$reportContent = @"
# DRTA Analysis Report

**Generated on**: $currentDate  
**Algorithm**: RTI+ (Real-Time Interface Plus)  
**Input File**: $InputFile  
**Output Prefix**: $OutputPrefix  

## Performance Summary

| Metric | Value |
|--------|-------|
| **States Count** | $stateCount |
| **Final States** | $finalStates |
| **Transitions** | $transitions |
| **Max State ID** | $($dotAnalysis.MaxStateNumber) |
| **Learning Time** | $runtime ($runtimeMs) |
| **Input Samples** | $inputSamples |
| **Symbol Alphabet Size** | $inputSymbols |
| **States per Sample** | $statesPerSample |
| **Transitions per State** | $(if($stateCount -gt 0){[math]::Round($transitions / $stateCount, 2)}else{"N/A"}) |
| **Model Complexity** | $(if($stateCount -gt 500){"High"}elseif($stateCount -gt 100){"Medium"}else{"Low"}) |

## Input Data Analysis

- **File Format**: $inputFormat
- **Data File**: ``$InputFile``
- **Sample Count**: $inputSamples sequences
- **Alphabet Size**: $inputSymbols unique symbols
- **Parsing Status**: $(if(Test-Path $InputFile){"SUCCESS"}else{"FILE NOT FOUND"})

## Generated Files

### Model Files
- **JSON Model**: ``${OutputPrefix}.final.json`` ($jsonSize)
- **DOT Graph**: ``${OutputPrefix}.final.dot`` ($dotSize)

### Visualizations
- **PNG Image**: ``${OutputPrefix}.final.png``
- **SVG Vector**: ``${OutputPrefix}.final.svg``

## Learning Process

- **Algorithm**: RTI+ (Real-Time Interface Plus)
- **Execution Time**: $runtime
- **APTA Creation**: $($runtimeDetails.APTACreationTime)
- **Learning Start**: $($runtimeDetails.LearningTime)
- **Start Time**: $($runtimeDetails.StartTime)
- **End Time**: $($runtimeDetails.EndTime)
- **Convergence**: $(if($runtime -ne "Unknown"){"SUCCESSFUL"}else{"CHECK LOGS"})
- **Final State Count**: $stateCount states ($finalStates final states)
- **Transition Count**: $transitions transitions
- **Memory Usage**: $jsonSize (JSON model)

## Quality Assessment

### Performance Indicators
- **Speed**: $(if($runtimeMs -match "(\d+) ms" -and [int]$matches[1] -lt 1000){"FAST (<1s)"}elseif($runtimeMs -match "(\d+) ms" -and [int]$matches[1] -lt 5000){"MODERATE (1-5s)"}else{"SLOW (>5s)"})
- **Model Size**: $(if($stateCount -lt 50){"COMPACT"}elseif($stateCount -lt 200){"MEDIUM"}else{"LARGE"})
- **Efficiency**: $(if($statesPerSample -match "([0-9.]+)" -and [double]$matches[1] -lt 2.0){"EFFICIENT"}elseif($statesPerSample -match "([0-9.]+)" -and [double]$matches[1] -lt 5.0){"ACCEPTABLE"}else{"MAY BE OVERFITTING"})
- **Connectivity**: $(if($transitions -gt 0 -and $stateCount -gt 0){$ratio = [math]::Round($transitions / $stateCount, 2); if($ratio -gt 3){"WELL CONNECTED ($ratio avg)"}elseif($ratio -gt 1.5){"MODERATE ($ratio avg)"}else{"SPARSE ($ratio avg)"}}else{"N/A"})
- **Finalization**: $(if($finalStates -gt 0 -and $stateCount -gt 0){$ratio = [math]::Round(($finalStates / $stateCount) * 100, 1); if($ratio -gt 50){"HIGH ($ratio%)"}elseif($ratio -gt 20){"MODERATE ($ratio%)"}else{"LOW ($ratio%)"}}else{"N/A"})

### Recommendations
$(if($stateCount -gt 500){
"- **High State Count**: Consider increasing merge thresholds
- **Optimization**: Try different evaluation parameters
- **Validation**: Test on independent dataset"
}elseif($stateCount -lt 20){
"- **Compact Model**: Good for visualization and interpretation
- **Validation**: Verify model captures sufficient complexity
- **Usage**: Suitable for real-time applications"
}else{
"- **Balanced Model**: Good trade-off between complexity and interpretability
- **Next Steps**: Validate on test data
- **Application**: Ready for deployment"
})

## DRTA Structure Analysis

### State Distribution
- **Total States**: $stateCount
- **Final States**: $finalStates ($(if($stateCount -gt 0){[math]::Round(($finalStates / $stateCount) * 100, 1)}else{0})%)
- **Non-Final States**: $($stateCount - $finalStates)
- **State ID Range**: 0 to $($dotAnalysis.MaxStateNumber)
- **Average Outgoing Transitions**: $(if($stateCount -gt 0){[math]::Round($transitions / $stateCount, 2)}else{"N/A"})

### Complexity Metrics
- **States per Input Sample**: $(if($inputSamples -ne "Unknown" -and [int]$inputSamples -gt 0){[math]::Round($stateCount / [int]$inputSamples, 3)}else{"N/A"})
- **Transitions per Input Sample**: $(if($inputSamples -ne "Unknown" -and [int]$inputSamples -gt 0){[math]::Round($transitions / [int]$inputSamples, 3)}else{"N/A"})
- **Model Density**: $(if($stateCount -gt 1){[math]::Round($transitions / ($stateCount * ($stateCount - 1)) * 100, 2)}else{0})% (of possible transitions)
- **Branching Factor**: $(if($stateCount -gt 0){[math]::Round($transitions / $stateCount, 2)}else{"N/A"})

## Technical Details

### Algorithm Configuration
- **Heuristic**: RTI+ with real-time constraints
- **Merge Strategy**: Greedy state merging
- **Convergence**: Automatic termination when no more merges possible
- **Output Format**: JSON + DOT + Visualizations

### File Specifications
- **Model Format**: JSON with full state transition information
- **Graph Format**: Graphviz DOT for visualization
- **Image Output**: PNG (raster) and SVG (vector) formats
- **Encoding**: UTF-8 for text files, binary for images

## Command Reference

### Learning Command
``````
.\build\Release\flexfringe.exe --ini ini\rti.ini --outputfile $OutputPrefix $InputFile
``````

### Visualization Commands
``````
dot -Tpng ${OutputPrefix}.final.dot -o ${OutputPrefix}.final.png
dot -Tsvg ${OutputPrefix}.final.dot -o ${OutputPrefix}.final.svg
``````

### Analysis Command
``````
.\generate_drta_report.ps1 -OutputPrefix "$OutputPrefix" -InputFile "$InputFile"
``````

---

**Report Generated**: $currentDate  
**FlexFringe Version**: Latest  
**System**: Windows PowerShell  
**Status**: $(if($stateCount -gt 0){"ANALYSIS COMPLETE"}else{"INCOMPLETE - CHECK SOURCE FILES"})

"@

# Ensure result folder exists
if (!(Test-Path $ResultFolder)) {
    New-Item -ItemType Directory -Path $ResultFolder -Force | Out-Null
}

# Write report
$reportContent | Out-File -FilePath $reportFile -Encoding UTF8

Write-Host ""
Write-Host "Analysis Report Generated Successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Key Results:" -ForegroundColor Cyan
Write-Host "   - States: $stateCount" -ForegroundColor White
Write-Host "   - Runtime: $runtime" -ForegroundColor White
Write-Host "   - Input Samples: $inputSamples" -ForegroundColor White
Write-Host "   - Alphabet Size: $inputSymbols" -ForegroundColor White
Write-Host ""
Write-Host "Report saved to: $reportFile" -ForegroundColor Yellow
Write-Host ""

# Also output key metrics for easy parsing
$metricsFile = "${ResultFolder}\metrics.txt"
$metricsContent = @"
STATES=$stateCount
FINAL_STATES=$finalStates
TRANSITIONS=$transitions
MAX_STATE_ID=$($dotAnalysis.MaxStateNumber)
RUNTIME=$runtime
RUNTIME_MS=$runtimeMs
APTA_TIME=$($runtimeDetails.APTACreationTime)
START_TIME=$($runtimeDetails.StartTime)
END_TIME=$($runtimeDetails.EndTime)
SAMPLES=$inputSamples
ALPHABET_SIZE=$inputSymbols
STATES_PER_SAMPLE=$statesPerSample
TRANSITIONS_PER_STATE=$(if($stateCount -gt 0){[math]::Round($transitions / $stateCount, 2)}else{"N/A"})
JSON_SIZE=$jsonSize
DOT_SIZE=$dotSize
TIMESTAMP=$currentDate
"@

$metricsContent | Out-File -FilePath $metricsFile -Encoding ASCII

Write-Host "Metrics saved to: $metricsFile" -ForegroundColor Yellow 
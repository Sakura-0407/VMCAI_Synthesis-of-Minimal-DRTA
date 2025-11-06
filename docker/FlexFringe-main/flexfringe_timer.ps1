# FlexFringe Automatic Runner and Timer Script
# Usage: .\flexfringe_timer.ps1 <input_file_path>
# Example: .\flexfringe_timer.ps1 ".\timed_data\timed_data.csv"

param([string]$file)

if (-not $file) {
    Write-Host "Usage: .\flexfringe_timer.ps1 <input_file_path>"
    exit 1
}

if (-not (Test-Path $file)) {
    Write-Host "Error: Input file '$file' not found"
    exit 1
}

# Record start time
$start = Get-Date

# Run FlexFringe (using RTI algorithm)
.\build\Release\flexfringe.exe --ini ini\rti.ini $file > $null

# Record end time
$end = Get-Date
$time = [math]::Round(($end - $start).TotalMilliseconds, 2)

# Count states in generated automaton
$dotFile = "$file.ff.final.dot"
if (Test-Path $dotFile) {
    $states = (Get-Content $dotFile | Select-String "^\s*\d+\s*\[").Count
} else {
    $states = "N/A"
}

# Output results
Write-Host "Execution Time: $time ms"
Write-Host "Number of States: $states" 
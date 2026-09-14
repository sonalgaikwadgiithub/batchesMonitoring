# Wrapper used by the scheduler (and safe to run by hand).
# Usage: .\run_check.ps1            -> query + send mail
#        .\run_check.ps1 -DryRun    -> query + print report, no mail

param([switch]$DryRun)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Virtual environment missing. Run: py -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
}

$logFile = Join-Path $PSScriptRoot ("logs\batch_status_{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))

$arguments = @("src\batch_monitor\main.py", "--log-file", $logFile)
if ($DryRun) { $arguments += "--dry-run" }

& $python @arguments
$code = $LASTEXITCODE

switch ($code) {
    0 { Write-Host "All batches healthy; report sent." }
    1 { Write-Host "Failures found; alert email sent." }
    default { Write-Warning "Job error (exit $code). See $logFile" }
}

exit $code

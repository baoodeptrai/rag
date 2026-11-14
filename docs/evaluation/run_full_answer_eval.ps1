$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$python = Join-Path $repoRoot 'backend\.venv\Scripts\python.exe'
$runner = Join-Path $repoRoot 'backend\rag_project\run_answer_quality_eval.py'
$runId = 'answer_quality_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
$output = Join-Path $PSScriptRoot "results\runs\$runId\answer_quality_100.csv"

if (-not (Test-Path -LiteralPath $python)) {
  throw "Python environment not found at $python. Create backend/.venv first."
}

'RUN' | & $python `
  $runner `
  --timeout 150 `
  --delay 0.1 `
  --output $output

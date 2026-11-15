$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$python = Join-Path $backend ".venv\Scripts\python.exe"
$rawDir = Join-Path $backend "data\raw"
$backendEnv = Join-Path $backend ".env"
if (Test-Path -LiteralPath $backendEnv) {
  $rawDirSetting = Get-Content -LiteralPath $backendEnv | Where-Object { $_ -match '^\s*RAG_RAW_DIR\s*=' } | Select-Object -Last 1
  if ($rawDirSetting -match '^\s*RAG_RAW_DIR\s*=\s*(.+?)\s*$') {
    $configuredRawDir = $Matches[1].Trim('"').Trim("'")
    if ($configuredRawDir) {
      $rawDir = if ([System.IO.Path]::IsPathRooted($configuredRawDir)) { $configuredRawDir } else { Join-Path $backend $configuredRawDir }
    }
  }
}
$processedDir = Join-Path $backend "data\processed"
$manifestPath = Join-Path $processedDir ".source-manifest"
$embeddingModel = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
if (Test-Path -LiteralPath $backendEnv) {
  $embeddingSetting = Get-Content -LiteralPath $backendEnv | Where-Object { $_ -match '^\s*EMBEDDING_MODEL\s*=' } | Select-Object -Last 1
  if ($embeddingSetting -match '^\s*EMBEDDING_MODEL\s*=\s*(.+?)\s*$') {
    $configuredEmbedding = $Matches[1].Trim('"').Trim("'")
    if ($configuredEmbedding) { $embeddingModel = $configuredEmbedding }
  }
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "Không tìm thấy Python. Hãy cài Python 3.11+ rồi chạy lại start.ps1."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "Không tìm thấy npm. Hãy cài Node.js rồi chạy lại start.ps1."
}
$tempDir = Join-Path $backend ".setup-temp"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
$env:TEMP = $tempDir
$env:TMP = $tempDir
# Keep Vietnamese output from Python query smoke checks printable on Windows.
$env:PYTHONIOENCODING = "utf-8"

if (-not (Test-Path $python)) {
  python -m venv (Join-Path $backend ".venv")
  if ($LASTEXITCODE -ne 0) { throw "Không tạo được môi trường Python trong backend/.venv." }
}

$dependencyCheck = & $python -c "import fastapi, pymupdf, docx, rank_bm25, qdrant_client, sentence_transformers" 2>&1
if ($LASTEXITCODE -ne 0) {
  Write-Host "Đang cài thư viện Backend/RAG lần đầu..."
  & $python -m pip install -r (Join-Path $backend "requirements.txt") 2>&1 | ForEach-Object { Write-Host $_ }
  $installExitCode = $LASTEXITCODE
  if ($installExitCode -ne 0) { throw "Cài thư viện chưa xong. Kiểm tra mạng rồi chạy lại .\start.ps1." }
}

$sourceFiles = @(Get-ChildItem -LiteralPath $rawDir -File -Recurse -ErrorAction SilentlyContinue |
  Where-Object { $_.Extension -in ".pdf", ".docx" } |
  Sort-Object FullName)

if ($sourceFiles.Count -gt 0) {
  $manifest = ($sourceFiles | ForEach-Object {
    $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
    '{0}|{1}' -f $_.FullName, $hash
  }) -join "`n"
  $oldManifest = if (Test-Path $manifestPath) { Get-Content -LiteralPath $manifestPath -Raw } else { "" }
  $indexPath = Join-Path $processedDir "bm25.pkl"
  $indexMetadataPath = Join-Path $processedDir "index_metadata.json"
  $activeEmbeddingModel = ""
  if (Test-Path -LiteralPath $indexMetadataPath) {
    try { $activeEmbeddingModel = (Get-Content -LiteralPath $indexMetadataPath -Raw | ConvertFrom-Json).embedding_model }
    catch { $activeEmbeddingModel = "__invalid_index_metadata__" }
  }
  $embeddingModelChanged = $activeEmbeddingModel -ne $embeddingModel
  if ($manifest -ne $oldManifest -or -not (Test-Path $indexPath) -or $embeddingModelChanged) {
    Write-Host "Tài liệu mới hoặc đã thay đổi; đang lập chỉ mục..."
    Push-Location $backend
    $previousErrorActionPreference = $ErrorActionPreference
    try {
      # Python libraries may write warnings to stderr; in Windows PowerShell 5.1
      # ErrorActionPreference=Stop can incorrectly turn those warnings into failures.
      $ErrorActionPreference = "Continue"
      & $python -m rag_project.pipeline 2>&1 | ForEach-Object { Write-Host $_ }
      $pipelineExitCode = $LASTEXITCODE
    }
    finally { Pop-Location }
    $ErrorActionPreference = $previousErrorActionPreference
    if ($pipelineExitCode -ne 0 -or -not (Test-Path $indexPath)) {
      throw "Lập chỉ mục chưa hoàn tất. Xem lỗi phía trên, sửa tài liệu/cấu hình rồi chạy lại."
    }
    Set-Content -LiteralPath $manifestPath -Value $manifest -NoNewline
  } else {
    Write-Host "Chỉ mục đã cập nhật; bỏ qua bước lập chỉ mục."
  }
} else {
  $oldManifest = if (Test-Path $manifestPath) { Get-Content -LiteralPath $manifestPath -Raw } else { $null }
  $indexPath = Join-Path $processedDir "bm25.pkl"
  $qdrantPath = Join-Path $backend "data\qdrant"
  $hasStaleCorpus = ($null -ne $oldManifest -and $oldManifest.Trim()) -or
    ($null -eq $oldManifest -and ((Test-Path $indexPath) -or (Test-Path $qdrantPath)))
  if ($hasStaleCorpus) {
    Write-Host "Kho tài liệu đã trống; đang xóa chunks và chỉ mục cũ..."
    Push-Location $backend
    $previousErrorActionPreference = $ErrorActionPreference
    try {
      $ErrorActionPreference = "Continue"
      & $python -m rag_project.pipeline 2>&1 | ForEach-Object { Write-Host $_ }
      $pipelineExitCode = $LASTEXITCODE
    }
    finally { Pop-Location }
    $ErrorActionPreference = $previousErrorActionPreference
    if ($pipelineExitCode -ne 0) { throw "Không xóa được chỉ mục cũ. Xem lỗi phía trên rồi chạy lại." }
    Set-Content -LiteralPath $manifestPath -Value "" -NoNewline
  } else {
    Write-Host "Chưa có PDF/DOCX trong backend/data/raw; API sẽ báo chưa có căn cứ."
  }
  if ($null -eq $oldManifest) { Set-Content -LiteralPath $manifestPath -Value "" -NoNewline }
}

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
  Write-Host "Đang cài thư viện Frontend lần đầu..."
  Push-Location $frontend
  try { npm install 2>&1 | ForEach-Object { Write-Host $_ } }
  finally { Pop-Location }
  $npmExitCode = $LASTEXITCODE
  if ($npmExitCode -ne 0) { throw "Cài thư viện Frontend chưa xong. Kiểm tra mạng rồi chạy lại .\start.ps1." }
}

function Test-LocalPort([int] $port) {
  $client = [System.Net.Sockets.TcpClient]::new()
  try {
    $attempt = $client.BeginConnect("127.0.0.1", $port, $null, $null)
    if (-not $attempt.AsyncWaitHandle.WaitOne(300)) { return $false }
    $client.EndConnect($attempt)
    return $true
  } catch {
    return $false
  } finally {
    $client.Dispose()
  }
}

if (Test-LocalPort 8000) {
  Write-Host "Backend đã chạy ở http://127.0.0.1:8000"
} else {
  $apiScript = Join-Path $backend "start-api.ps1"
  Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit -ExecutionPolicy Bypass -File `"$apiScript`"" -WorkingDirectory $backend -WindowStyle Normal
}

if (Test-LocalPort 5173) {
  Write-Host "Frontend đã chạy ở http://localhost:5173"
} else {
  $uiScript = Join-Path $frontend "start-ui.ps1"
  Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit -ExecutionPolicy Bypass -File `"$uiScript`"" -WorkingDirectory $frontend -WindowStyle Normal
}

Write-Host "Đã mở ứng dụng. Truy cập http://localhost:5173 (API: http://127.0.0.1:8000/docs)."

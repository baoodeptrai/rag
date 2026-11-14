$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'

'RUN' | & 'D:\40 cái\TV4_RAG\backend\.venv\Scripts\python.exe' `
  'D:\40 cái\TV4_RAG\backend\rag_project\run_answer_quality_eval.py' `
  --timeout 150 `
  --delay 0.1 `
  --output 'D:\40 cái\TV4_RAG\docs\evaluation\results\runs\full_answer_quality_20261114_valid2\answer_quality_100.csv'

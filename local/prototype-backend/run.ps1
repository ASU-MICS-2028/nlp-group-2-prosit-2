# Starts the prototype backend on http://localhost:8001 (this laptop only; /local/ is git-ignored).
# The OpenAI key is read from the ORIGINAL prototype's .env at start-up, so no key file lives in this repo.
# Note: this prototype uses OpenAI (paid). The team project uses agent/llm.py (Gemini free tier) instead.

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# The key file: PROTOTYPE_ENV_FILE if set, otherwise coding_agent\.env next to this repo's folder
# (this script is in <repo>\local\prototype-backend, so three folders up is the parent of the repo)
$envFile = if ($env:PROTOTYPE_ENV_FILE) { $env:PROTOTYPE_ENV_FILE } else { Join-Path $PSScriptRoot '..\..\..\coding_agent\.env' }
if (-not (Test-Path $envFile)) {
    Write-Error "No .env found at $envFile. Put OPENAI_API_KEY there first."
}

# Copy each NAME=value line into this process's environment only (gone when the window closes)
foreach ($line in Get-Content $envFile) {
    if ($line -match '^\s*([A-Z_]+)\s*=\s*(.*)\s*$') {
        Set-Item -Path "Env:$($Matches[1])" -Value $Matches[2].Trim('"')
    }
}

# Let the Vite dev server (port 5173) call this backend; the prototype only allowed port 3000
$env:CORS_ORIGINS = 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000'

New-Item -ItemType Directory -Force data, generated | Out-Null
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8001

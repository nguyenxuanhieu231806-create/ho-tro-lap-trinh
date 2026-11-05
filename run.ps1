param([ValidateRange(1,65535)][int]$Port = 8000, [switch]$NoBrowser, [switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$browserJob = $null
$result = 1
Push-Location $PSScriptRoot
try {
    if (!(Test-Path -LiteralPath $pythonExe)) {
        Write-Host 'Creating .venv (Python 3.11+ required)...'
        if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv .venv }
        elseif (Get-Command python -ErrorAction SilentlyContinue) { & python -m venv .venv }
        else { throw 'Install Python 3.11+ from python.org, then retry.' }
        if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv.' }
    }
    & $pythonExe -B -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ is required.' }
    # Direct invocation avoids Activate.ps1 execution-policy restrictions.
    $env:VIRTUAL_ENV = Split-Path (Split-Path $pythonExe)
    $env:PATH = (Split-Path $pythonExe) + ';' + $env:PATH
    $env:PYTHONUTF8 = '1'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    & $pythonExe -B -c "import importlib.util, sys; sys.exit(not all(importlib.util.find_spec(n) for n in ('fastapi','uvicorn','pydantic','dotenv')))"
    if ($LASTEXITCODE -ne 0) {
        & $pythonExe -m ensurepip --upgrade
        if ($LASTEXITCODE -ne 0) { throw 'Could not initialize pip.' }
        & $pythonExe -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw 'Installation failed. Check Internet connectivity.' }
    }
    if (!$CheckOnly) {
        $probe = New-Object System.Net.Sockets.TcpListener([Net.IPAddress]::Any, $Port)
        try { $probe.Start() } catch { throw "Port $Port is busy. Stop the old server or use -Port 8001." }
        finally { $probe.Stop() }
    }
    $checkOllama = @'
import asyncio, sys
from ai_core import OllamaTutor
async def check():
    tutor = OllamaTutor()
    try:
        await tutor._request('GET', '/api/version', timeout=5)
    except Exception:
        sys.exit(2 if tutor.base_url in ('http://localhost:11434', 'http://127.0.0.1:11434') else 3)
asyncio.run(check())
'@
    $checkOllama | & $pythonExe -B -X utf8 -
    $ollamaStatus = $LASTEXITCODE
    if ($ollamaStatus -eq 2) {
        $command = Get-Command ollama -ErrorAction SilentlyContinue
        $ollamaExe = if ($command) { $command.Source } else { Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe' }
        if (!(Test-Path -LiteralPath $ollamaExe)) { throw 'Install Ollama from ollama.com/download, then retry.' }
        Write-Host 'Starting Ollama in the background...'
        $previousHost = $env:OLLAMA_HOST
        try {
            $env:OLLAMA_HOST = '127.0.0.1:11434'
            Start-Process -FilePath $ollamaExe -ArgumentList 'serve' -WindowStyle Hidden | Out-Null
        } finally { $env:OLLAMA_HOST = $previousHost }
        for ($attempt = 0; $attempt -lt 15; $attempt++) {
            Start-Sleep -Seconds 1
            $checkOllama | & $pythonExe -B -X utf8 -
            if ($LASTEXITCODE -eq 0) { break }
        }
        if ($LASTEXITCODE -ne 0) { throw 'Ollama did not start. Check port 11434.' }
    } elseif ($ollamaStatus -ne 0) { throw 'Configured Ollama server is unreachable. Check OLLAMA_BASE_URL.' }
    Write-Host 'Checking and loading the installed model (first load may take time)...'
    @'
import asyncio, sys
from ai_core import OllamaTutor, sanitize_user_error
async def check():
    try:
        state = await OllamaTutor().warmup()
        print(state['message'])
        print('Model:', state.get('model', ''))
        sys.exit(0 if state['ready'] else 1)
    except Exception as exc:
        print(sanitize_user_error(exc))
        sys.exit(1)
asyncio.run(check())
'@ | & $pythonExe -B -X utf8 -
    if ($LASTEXITCODE -ne 0) { throw 'Model not ready. Use ollama list / ollama pull qwen2.5-coder:7b, then retry.' }
    if ($CheckOnly) { $result = 0; Write-Host 'Preflight OK.' }
    else {
        $localUrl = "http://127.0.0.1:$Port"
        Write-Host "Local:  $localUrl"
        try {
            Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
                Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254.*' -and $_.AddressState -eq 'Preferred' } |
                ForEach-Object { Write-Host "LAN:    http://$($_.IPAddress):$Port" }
        } catch { Write-Host 'Use ipconfig to find the Wi-Fi/Ethernet IPv4 address.' }
        Write-Host "Health: $localUrl/api/health"
        Write-Host 'Ctrl+C stops the web. Ollama stays available.'
        if (!$NoBrowser) {
            $browserJob = Start-Job -ArgumentList $localUrl -ScriptBlock {
                param($url)
                for ($attempt = 0; $attempt -lt 30; $attempt++) {
                    try {
                        $health = Invoke-RestMethod "$url/api/health" -TimeoutSec 8
                        if ($health.ready -and $health.service -eq 'fit-hpuni-programming-web') {
                            Start-Process $url
                            break
                        }
                    } catch {}
                    Start-Sleep -Seconds 1
                }
            }
        }
        & $pythonExe -B -m uvicorn api:app --host 0.0.0.0 --port $Port --workers 1 --proxy-headers --forwarded-allow-ips '127.0.0.1,::1' --timeout-keep-alive 5 --no-access-log
        $result = $LASTEXITCODE
    }
} catch { Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red }
finally {
    if ($browserJob) { Stop-Job $browserJob -ErrorAction SilentlyContinue; Remove-Job $browserJob -Force -ErrorAction SilentlyContinue }
    Pop-Location
}
exit $result


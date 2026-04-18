param(
    [switch]$FrontendOnly,
    [switch]$BackendOnly
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$stateRoot = Join-Path $projectRoot ".launcher-state"
$backendRequirements = Join-Path $projectRoot "backend\requirements.txt"
$backendRoot = Join-Path $projectRoot "backend"
$backendEnvExample = Join-Path $backendRoot ".env.example"
$backendEnvFile = Join-Path $backendRoot ".env"
$backendHealthUrl = "http://127.0.0.1:8000/health"
$backendStamp = Join-Path $stateRoot "backend-requirements.sha256"
$frontendPackageJson = Join-Path $projectRoot "frontend\package.json"
$frontendStamp = Join-Path $stateRoot "frontend-package.sha256"
$venvRoot = Join-Path $projectRoot ".venv"
$venvActivate = Join-Path $projectRoot ".venv\Scripts\Activate.ps1"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$frontendRoot = Join-Path $projectRoot "frontend"
$frontendNodeModules = Join-Path $frontendRoot "node_modules"
$frontendEnvExample = Join-Path $frontendRoot ".env.example"
$frontendEnvLocal = Join-Path $frontendRoot ".env.local"

function Assert-CommandExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CommandName,
        [Parameter(Mandatory = $true)]
        [string]$HelpMessage
    )

    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw $HelpMessage
    }
}

function Get-FileSha256 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return (Get-FileHash -Algorithm SHA256 -Path $Path).Hash
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }
}

function Ensure-BackendReady {
    Assert-CommandExists -CommandName "python" -HelpMessage "Python is not installed or not on PATH."

    if ((-not (Test-Path $backendEnvFile)) -and (Test-Path $backendEnvExample)) {
        Write-Host "Creating backend .env..." -ForegroundColor Yellow
        Copy-Item $backendEnvExample $backendEnvFile
    }

    if (-not (Test-Path $venvPython)) {
        Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
        Invoke-Checked -FilePath "python" -Arguments @("-m", "venv", $venvRoot) -WorkingDirectory $projectRoot
    }

    $currentHash = Get-FileSha256 -Path $backendRequirements
    $shouldInstall = (-not (Test-Path $backendStamp))

    if (-not $shouldInstall) {
        $savedHash = (Get-Content $backendStamp -Raw).Trim()
        if ($savedHash -ne $currentHash) {
            $shouldInstall = $true
        }
    }

    if ($shouldInstall) {
        Write-Host "Installing backend dependencies..." -ForegroundColor Yellow
        Invoke-Checked -FilePath $venvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip") -WorkingDirectory $projectRoot
        Invoke-Checked -FilePath $venvPython -Arguments @("-m", "pip", "install", "-r", $backendRequirements) -WorkingDirectory $projectRoot
        Set-Content -Path $backendStamp -Value $currentHash -NoNewline
    }
}

function Wait-BackendHealth {
    param(
        [int]$TimeoutSeconds = 25
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        Start-Sleep -Milliseconds 750
        try {
            $response = Invoke-RestMethod -Uri $backendHealthUrl -Method Get -TimeoutSec 2
            if ($response.status -eq "ok") {
                return $response
            }
        }
        catch {
        }
    } while ((Get-Date) -lt $deadline)

    throw "Backend did not become ready at $backendHealthUrl. Check the backend PowerShell window for the startup error."
}

function Ensure-FrontendReady {
    Assert-CommandExists -CommandName "npm" -HelpMessage "npm is not installed or not on PATH. Install Node.js first."

    if ((-not (Test-Path $frontendEnvLocal)) -and (Test-Path $frontendEnvExample)) {
        Write-Host "Creating frontend .env.local..." -ForegroundColor Yellow
        Copy-Item $frontendEnvExample $frontendEnvLocal
    }

    $currentHash = Get-FileSha256 -Path $frontendPackageJson
    $shouldInstall = (-not (Test-Path $frontendNodeModules)) -or (-not (Test-Path $frontendStamp))

    if (-not $shouldInstall) {
        $savedHash = (Get-Content $frontendStamp -Raw).Trim()
        if ($savedHash -ne $currentHash) {
            $shouldInstall = $true
        }
    }

    if ($shouldInstall) {
        Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
        Push-Location $frontendRoot
        try {
            & npm install
            if ($LASTEXITCODE -ne 0) {
                throw "npm install failed."
            }
        }
        finally {
            Pop-Location
        }
        Set-Content -Path $frontendStamp -Value $currentHash -NoNewline
    }
}

if (-not (Test-Path $stateRoot)) {
    New-Item -ItemType Directory -Path $stateRoot | Out-Null
}

if (-not $FrontendOnly) {
    Ensure-BackendReady
}

if (-not $BackendOnly) {
    Ensure-FrontendReady
}

$backendCommand = "& '$venvActivate'; Set-Location '$projectRoot'; uvicorn backend.app.main:app --reload"
$frontendCommand = "Set-Location '$frontendRoot'; npm run dev"
$backendProcess = $null

if (-not $FrontendOnly) {
    $backendProcess = Start-Process powershell -PassThru -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        $backendCommand
    ) -WorkingDirectory $projectRoot

    Write-Host "Waiting for backend health..." -ForegroundColor Yellow
    $backendHealth = Wait-BackendHealth
    Write-Host "Backend ready. Active detector: $($backendHealth.detector_active)" -ForegroundColor Green
    if ($backendHealth.detector_warning) {
        Write-Host "Detector warning: $($backendHealth.detector_warning)" -ForegroundColor Yellow
    }
}

if (-not $BackendOnly) {
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        $frontendCommand
    ) -WorkingDirectory $frontendRoot
}

Write-Host ""
Write-Host "Launch started." -ForegroundColor Green

if (-not $FrontendOnly) {
    Write-Host "Backend window: http://127.0.0.1:8000/docs"
}

if (-not $BackendOnly) {
    Write-Host "Frontend window: http://127.0.0.1:3000"
}

<#
.SYNOPSIS
    AMEVA-WoL Environment & Setup Diagnostic Auditor (Windows PowerShell)

.DESCRIPTION
    Performs an A-to-Z audit of OS, Python environment, dependencies, .env file,
    Telegram bot credentials, file permissions, data directory, network connectivity,
    and device registry. Provides heuristic troubleshooting guidance for failed checks.
#>

$ErrorActionPreference = "Continue"

# Reconfigure Output Encoding to UTF-8 for clean emoji and box rendering
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoDir = Split-Path -Parent $ScriptDir
Set-Location $RepoDir

$PassCount = 0
$WarnCount = 0
$FailCount = 0
$HeuristicFixes = [System.Collections.Generic.List[string]]::new()

function Log-Pass ([string]$msg) {
    Write-Host "[PASS] " -ForegroundColor Green -NoNewline
    Write-Host $msg
    $script:PassCount++
}

function Log-Warn ([string]$msg, [string]$fix = "") {
    Write-Host "[WARN] " -ForegroundColor Yellow -NoNewline
    Write-Host $msg
    $script:WarnCount++
    if ($fix) {
        $script:HeuristicFixes.Add("[WARN] $msg`n   -> FIX: $fix")
    }
}

function Log-Fail ([string]$msg, [string]$fix = "") {
    Write-Host "[FAIL] " -ForegroundColor Red -NoNewline
    Write-Host $msg
    $script:FailCount++
    if ($fix) {
        $script:HeuristicFixes.Add("[FAIL] $msg`n   -> FIX: $fix")
    }
}

function Log-Info ([string]$msg) {
    Write-Host "[INFO] " -ForegroundColor Cyan -NoNewline
    Write-Host $msg
}

Write-Host "==============================================================" -ForegroundColor Blue
Write-Host "   AMEVA-WoL Environment & Setup Diagnostic Auditor" -ForegroundColor Blue
Write-Host "==============================================================" -ForegroundColor Blue
Log-Info "Repository Path: $RepoDir"
Log-Info "Audit Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss UTC')"
Write-Host ""

# ------------------------------------------------------------------------------
# 1. System Environment Check
# ------------------------------------------------------------------------------
Write-Host "1. System Environment Check" -ForegroundColor White
$OS = Get-CimInstance Win32_OperatingSystem
Log-Pass "Operating System: $($OS.Caption) ($($OS.OSArchitecture))"

# ------------------------------------------------------------------------------
# 2. System Utilities Check (git, ping)
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "2. System Utilities Check" -ForegroundColor White

if (Get-Command git -ErrorAction SilentlyContinue) {
    $gitVer = (git --version)
    Log-Pass "Git binary available: $gitVer"
} else {
    Log-Fail -msg "Git binary missing" -fix "Install Git for Windows from https://git-scm.com/download/win"
}

if (Get-Command ping -ErrorAction SilentlyContinue) {
    Log-Pass "Ping utility available"
} else {
    Log-Fail -msg "Ping utility missing" -fix "Ensure system ping.exe is present in C:\Windows\System32"
}

# ------------------------------------------------------------------------------
# 3. Python 3.10+ Environment Check
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "3. Python Environment Check" -ForegroundColor White

$PythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
}

if (-not $PythonCmd) {
    Log-Fail -msg "Python executable not found in PATH" -fix "Install Python 3.10+ from https://www.python.org/downloads/ and check 'Add Python to PATH'."
} else {
    $PyVersionStr = & $PythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
    $PyMajor = & $PythonCmd -c "import sys; print(sys.version_info.major)"
    $PyMinor = & $PythonCmd -c "import sys; print(sys.version_info.minor)"

    if ([int]$PyMajor -eq 3 -and [int]$PyMinor -ge 10) {
        Log-Pass "Python version: $PyVersionStr (>= 3.10)"
    } else {
        Log-Fail -msg "Python version is $PyVersionStr (AMEVA-WoL requires Python 3.10+)" -fix "Upgrade Python to version 3.10 or newer."
    }
}

# ------------------------------------------------------------------------------
# 4. Virtual Environment & Dependencies Check
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "4. Virtual Environment and Dependencies Check" -ForegroundColor White

$VenvDir = Join-Path $RepoDir ".venv"
if (Test-Path $VenvDir) {
    Log-Pass "Virtual environment directory (.venv) exists"
    $VenvPy = Join-Path $VenvDir "Scripts\python.exe"
    if (Test-Path $VenvPy) {
        $PythonCmd = $VenvPy
    }
} else {
    Log-Warn -msg "Virtual environment (.venv) not found in repository root" -fix "Create virtual environment: 'python -m venv .venv' and run '.venv\Scripts\activate'."
}

if ($PythonCmd) {
    $env:PYTHONPATH = "src"
    
    # Check python-telegram-bot
    $hasTg = & $PythonCmd -c "import telegram; print('OK')" 2>$null
    if ($hasTg -eq "OK") {
        $tgVer = & $PythonCmd -c "import telegram; print(getattr(telegram, '__version__', 'Unknown'))"
        Log-Pass "python-telegram-bot library installed (v$tgVer)"
    } else {
        Log-Fail -msg "python-telegram-bot library is missing" -fix "Install dependencies: 'pip install -r requirements.txt'."
    }

    # Check python-dotenv
    $hasDotenv = & $PythonCmd -c "import dotenv; print('OK')" 2>$null
    if ($hasDotenv -eq "OK") {
        Log-Pass "python-dotenv library installed"
    } else {
        Log-Fail -msg "python-dotenv library is missing" -fix "Install dependencies: 'pip install -r requirements.txt'."
    }

    # Check ameva_wol package
    $hasPkg = & $PythonCmd -c "import ameva_wol; print('OK')" 2>$null
    if ($hasPkg -eq "OK") {
        Log-Pass "AMEVA-WoL package importable (src/ameva_wol)"
    } else {
        Log-Fail -msg "AMEVA-WoL package failed to import" -fix "Ensure repository files are intact and PYTHONPATH includes 'src'."
    }
}

# ------------------------------------------------------------------------------
# 5. Environment File (.env) Security & Secrets Audit
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "5. .env Configuration Audit" -ForegroundColor White

$EnvFile = Join-Path $RepoDir ".env"
$DataDirCfg = "./data"

if (-not (Test-Path $EnvFile)) {
    Log-Fail -msg ".env file missing in repository root" -fix "Copy example file: 'Copy-Item .env.example .env' and edit secrets."
} else {
    Log-Pass ".env file exists"

    $EnvLines = Get-Content $EnvFile
    $Token = ""
    $UserIds = ""

    foreach ($line in $EnvLines) {
        if ($line -match "^\s*TELEGRAM_BOT_TOKEN\s*=\s*(.*)$") {
            $Token = $matches[1].Trim(" `"'")
        }
        if ($line -match "^\s*ALLOWED_USER_IDS\s*=\s*(.*)$") {
            $UserIds = $matches[1].Trim(" `"'")
        }
        if ($line -match "^\s*DATA_DIR\s*=\s*(.*)$") {
            $DataDirCfg = $matches[1].Trim(" `"'")
        }
    }

    if (-not $Token -or $Token -eq "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_ExampleToken") {
        Log-Fail -msg "TELEGRAM_BOT_TOKEN is missing or using default example value" -fix "Open .env and insert your real Telegram Bot API Token from @BotFather."
    } elseif ($Token -match "^\d{5,12}:[A-Za-z0-9_-]{30,50}$") {
        $Redacted = $Token.Substring(0, [Math]::Min(10, $Token.Length)) + "... [Redacted]"
        Log-Pass "TELEGRAM_BOT_TOKEN format is valid ($Redacted)"
    } else {
        Log-Warn -msg "TELEGRAM_BOT_TOKEN format looks unusual" -fix "Verify your token format obtained from @BotFather."
    }

    if (-not $UserIds -or $UserIds -eq "123456789,987654321") {
        Log-Fail -msg "ALLOWED_USER_IDS is missing or using default example values" -fix "Open .env and insert your real numeric Telegram User ID from @userinfobot."
    } else {
        $ValidUserIds = $true
        $Items = $UserIds.Split(",")
        foreach ($item in $Items) {
            $clean = $item.Trim()
            if ($clean -notmatch "^\d+$") {
                $ValidUserIds = $false
                break
            }
        }
        if ($ValidUserIds) {
            Log-Pass "ALLOWED_USER_IDS configured cleanly ($UserIds)"
        } else {
            Log-Fail -msg "ALLOWED_USER_IDS contains non-numeric values: '$UserIds'" -fix "ALLOWED_USER_IDS must contain comma-separated numbers only (e.g. 123456789)."
        }
    }
}

# ------------------------------------------------------------------------------
# 6. Data Directory & Registry Check
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "6. Persistent Data Directory and Registry Check" -ForegroundColor White

$ResolvedDataDir = [System.IO.Path]::GetFullPath((Join-Path $RepoDir $DataDirCfg))
if (-not (Test-Path $ResolvedDataDir)) {
    New-Item -ItemType Directory -Path $ResolvedDataDir -Force | Out-Null
}

if (Test-Path $ResolvedDataDir) {
    Log-Pass "Data directory exists: $ResolvedDataDir"
} else {
    Log-Fail -msg "Data directory cannot be created: $ResolvedDataDir" -fix "Check folder permissions for $ResolvedDataDir."
}

$LockFile = Join-Path $ResolvedDataDir ".lock"
if (Test-Path $LockFile) {
    Log-Info "Lock file exists ($LockFile)"
} else {
    Log-Pass "No lock conflict detected"
}

$DevicesFile = Join-Path $ResolvedDataDir "devices.json"
if (Test-Path $DevicesFile) {
    try {
        $JsonRaw = Get-Content $DevicesFile -Raw | ConvertFrom-Json
        $DevCount = ($JsonRaw.PSObject.Properties | Measure-Object).Count
        Log-Pass "Device registry (devices.json) exists ($DevCount device(s) registered)"
    } catch {
        Log-Fail -msg "Device registry file (devices.json) contains invalid or corrupt JSON" -fix "Delete or repair $DevicesFile."
    }
} else {
    Log-Info "Device registry (devices.json) not created yet (Will be created on first /add)"
}

# ------------------------------------------------------------------------------
# 7. Network Connectivity Check
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "7. Network Connectivity Check" -ForegroundColor White

$PingTest = Test-Connection -ComputerName "api.telegram.org" -Count 1 -Quiet -ErrorAction SilentlyContinue
if ($PingTest) {
    Log-Pass "Outbound Internet connectivity to Telegram API / DNS: OK"
} else {
    Log-Warn -msg "Failed to ping api.telegram.org" -fix "Check your network or firewall connection to Telegram servers."
}

# ------------------------------------------------------------------------------
# 8. Final Audit Summary & Heuristic Fix Instructions
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "==============================================================" -ForegroundColor Blue
Write-Host "                  AUDIT SUMMARY REPORT                        " -ForegroundColor Blue
Write-Host "==============================================================" -ForegroundColor Blue
Write-Host "  Passed Checks: $PassCount" -ForegroundColor Green
Write-Host "  Warnings:      $WarnCount" -ForegroundColor Yellow
Write-Host "  Failed Checks: $FailCount" -ForegroundColor Red
Write-Host ""

if ($HeuristicFixes.Count -gt 0) {
    Write-Host "HEURISTIC TROUBLESHOOTING AND ACTION REQUIRED:" -ForegroundColor Yellow
    Write-Host "--------------------------------------------------------------"
    foreach ($fix in $HeuristicFixes) {
        Write-Host $fix
        Write-Host ""
    }
    Write-Host "--------------------------------------------------------------"
}

if ($FailCount -eq 0) {
    Write-Host "SYSTEM STATUS: READY TO RUN!" -ForegroundColor Green
    Write-Host "Run default mode:   python -m ameva_wol" -ForegroundColor Cyan
    Write-Host "Run Always-On mode: python -m ameva_wol --always-on 5" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "SYSTEM STATUS: AUDIT FAILED ($FailCount critical error(s))" -ForegroundColor Red
    Write-Host "Please apply the heuristic fixes above before launching AMEVA-WoL."
    exit 1
}

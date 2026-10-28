param(
    [string]$OllamaModel = "qwen2.5vl:3b",
    [switch]$SkipModelDownload,
    [switch]$PullModelOnly
)

$ErrorActionPreference = "Stop"
$ProjectDirectory = $PSScriptRoot
Set-Location $ProjectDirectory

function Test-OllamaApi {
    try {
        $null = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3
        return $true
    }
    catch {
        return $false
    }
}

function Resolve-OllamaExecutable {
    $Candidates = @()
    if ($env:LOCALAPPDATA) {
        $Candidates += Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    }
    if ($env:ProgramFiles) {
        $Candidates += Join-Path $env:ProgramFiles "Ollama\ollama.exe"
    }

    foreach ($Candidate in $Candidates) {
        if (Test-Path -LiteralPath $Candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $Candidate).Path
        }
    }

    foreach ($CommandName in @("ollama.exe", "ollama")) {
        $OllamaCommand = Get-Command $CommandName -ErrorAction SilentlyContinue
        if ($OllamaCommand -and $OllamaCommand.CommandType -eq "Application" -and $OllamaCommand.Source) {
            return $OllamaCommand.Source
        }
    }

    throw "Ollama was not found. Install the Windows Ollama app or add ollama.exe to PATH, then rerun this script."
}

function Invoke-OllamaModelPull([string]$ModelName) {
    $OllamaExe = Resolve-OllamaExecutable
    $PullProcess = Start-Process -FilePath $OllamaExe -ArgumentList @("pull", $ModelName) -PassThru -WindowStyle Hidden
    Write-Host "Ollama pull started; waiting for $ModelName to appear in the local model list."
    for ($Attempt = 0; $Attempt -lt 1800; $Attempt++) {
        if ($PullProcess.HasExited) {
            if ($PullProcess.ExitCode -ne 0) {
                throw "Ollama could not download ${ModelName}; CLI exit code: $($PullProcess.ExitCode)"
            }
            $PullProcess.Refresh()
        }

        try {
            $OllamaTags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
            $InstalledModels = @($OllamaTags.models | ForEach-Object { $_.name })
            if ($InstalledModels -contains $ModelName) { return }
        }
        catch {
            if ($PullProcess.HasExited) { throw "Ollama stopped responding while downloading ${ModelName}." }
        }

        if ($Attempt -gt 0 -and $Attempt % 30 -eq 0) {
            Write-Host "Still downloading $ModelName. Keep this window open."
        }
        Start-Sleep -Seconds 2
    }

    throw "Timed out waiting for Ollama to finish downloading $ModelName. Check network access and rerun this script."
}

if (-not (Test-OllamaApi)) {
    $OllamaExe = Resolve-OllamaExecutable
    Start-Process -FilePath $OllamaExe -ArgumentList "serve" -WindowStyle Hidden
    $OllamaReady = $false
    for ($Attempt = 0; $Attempt -lt 15; $Attempt++) {
        Start-Sleep -Seconds 2
        if (Test-OllamaApi) {
            $OllamaReady = $true
            break
        }
    }
    if (-not $OllamaReady) {
        throw "Ollama did not respond at http://127.0.0.1:11434. Start the Ollama Windows app and rerun this script."
    }
}

$OllamaTags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 10
$InstalledModels = @($OllamaTags.models | ForEach-Object { $_.name })
if ($InstalledModels -notcontains $OllamaModel) {
    if ($SkipModelDownload) {
        Write-Warning "Skipping the missing model download. The assistant UI will start, but AI requests need $OllamaModel installed first."
    }
    else {
        Write-Host "Downloading local vision model $OllamaModel. This may take a while."
        Invoke-OllamaModelPull -ModelName $OllamaModel
        $OllamaTags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 10
        $InstalledModels = @($OllamaTags.models | ForEach-Object { $_.name })
        if ($InstalledModels -notcontains $OllamaModel) {
            throw "Ollama reported success but the model is not listed at http://127.0.0.1:11434/api/tags."
        }
    }
}

if ($PullModelOnly) {
    Write-Host "Ollama model is ready: $OllamaModel"
    exit 0
}

# Keep this setup local to the PowerShell process; preserve the user's .env files.
$env:DEBUG = "True"
$env:USE_HTTPS = "False"
$env:ALLOWED_HOSTS = "127.0.0.1,localhost"
$env:SYAFRA_AGENT_PROVIDER = "ollama"
$env:SYAFRA_AGENT_OLLAMA_URL = "http://127.0.0.1:11434"
$env:SYAFRA_AGENT_OLLAMA_MODEL = $OllamaModel
$env:SYAFRA_AGENT_OLLAMA_TIMEOUT_SECONDS = "300"

$Python312Path = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
$PythonArguments = @()
if (Test-Path $Python312Path) {
    $PythonCommand = $Python312Path
}
else {
    $PythonLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($PythonLauncher) {
        $PythonCommand = $PythonLauncher.Source
        $PythonArguments = @("-3.12")
    }
    else {
        $PythonLauncher = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($PythonLauncher) { $PythonCommand = $PythonLauncher.Source }
    }
}
if (-not $PythonCommand) {
    throw "Python 3 was not found. Install Python 3 for Windows, enable its PATH option, then rerun this script."
}

$VirtualEnvironment = Join-Path $ProjectDirectory ".venv-windows312-local"
$VirtualEnvironmentPython = Join-Path $VirtualEnvironment "Scripts\python.exe"
if (-not (Test-Path $VirtualEnvironmentPython)) {
    if (Test-Path $VirtualEnvironment) {
        throw "An incomplete .venv-windows312-local folder exists. Rename it, then rerun this script."
    }
    $VenvArguments = @($PythonArguments) + @("-m", "venv", $VirtualEnvironment)
    $VenvProcess = Start-Process -FilePath $PythonCommand -ArgumentList $VenvArguments -Wait -PassThru -NoNewWindow
    if ($VenvProcess.ExitCode -ne 0 -or -not (Test-Path $VirtualEnvironmentPython)) {
        throw "Could not create the Windows Python virtual environment."
    }
}

Write-Host "Installing Syafra's Python dependencies..."
$RequirementsFile = Join-Path $ProjectDirectory "requirements.txt"
$PipProcess = Start-Process -FilePath $VirtualEnvironmentPython -ArgumentList @("-m", "pip", "install", "-r", $RequirementsFile) -Wait -PassThru -NoNewWindow
if ($PipProcess.ExitCode -ne 0) {
    throw "Dependency installation failed. Review the pip output and rerun this script."
}

$ManagePy = Join-Path $ProjectDirectory "manage.py"
$CheckProcess = Start-Process -FilePath $VirtualEnvironmentPython -ArgumentList @($ManagePy, "check") -Wait -PassThru -NoNewWindow
if ($CheckProcess.ExitCode -ne 0) {
    throw "Django's configuration check failed. Review the error above before continuing."
}

$DatabaseInfoPath = Join-Path $env:TEMP "syafra-agent-db-info.txt"
$DbInfoCode = "from django.conf import settings; d=settings.DATABASES['default']; print('AGENT_DB|' + str(d.get('ENGINE', '')) + '|' + str(d.get('HOST') or ''))"
$DbInfoArguments = @($ManagePy, "shell", "-c", "`"$DbInfoCode`"", "--verbosity", "0")
$DbInfoProcess = Start-Process -FilePath $VirtualEnvironmentPython -ArgumentList $DbInfoArguments -Wait -PassThru -NoNewWindow -RedirectStandardOutput $DatabaseInfoPath
if ($DbInfoProcess.ExitCode -ne 0) {
    throw "Could not identify the configured database. No migration was run."
}
$DatabaseInfo = @(Get-Content -Path $DatabaseInfoPath | Where-Object { $_ -like "AGENT_DB|*" } | Select-Object -Last 1)
Remove-Item $DatabaseInfoPath -Force -ErrorAction SilentlyContinue
if ($DatabaseInfo.Count -eq 0) {
    throw "Could not identify the configured database. No migration was run."
}
$DatabaseParts = $DatabaseInfo[0].Split("|")
$DatabaseEngine = $DatabaseParts[1]
$DatabaseHost = $DatabaseParts[2]
$RemoteDatabase = $DatabaseHost -and $DatabaseHost -notin @("localhost", "127.0.0.1", "::1")
if ($RemoteDatabase) {
    Write-Host "Configured database host: $DatabaseHost"
    Write-Host "The products migration adds a material field; syafra_agent adds its proposal and private-image tables."
    $MigrationApproval = Read-Host "Type MIGRATE to apply those two migrations to this remote database"
    if ($MigrationApproval -cne "MIGRATE") {
        throw "Migration was not approved. No database changes were made; rerun and type MIGRATE when ready."
    }
    $MigrationTargets = @("products", "syafra_agent")
}
else {
    Write-Host "Applying all pending migrations to the local database."
}

Write-Host "Applying Syafra database migrations..."
if ($RemoteDatabase) {
    foreach ($MigrationTarget in $MigrationTargets) {
        $MigrationArguments = @($ManagePy, "migrate", $MigrationTarget, "--noinput")
        $MigrationProcess = Start-Process -FilePath $VirtualEnvironmentPython -ArgumentList $MigrationArguments -Wait -PassThru -NoNewWindow
        if ($MigrationProcess.ExitCode -ne 0) {
            throw "Database migration failed for $MigrationTarget. Review the error above."
        }
    }
}
else {
    $MigrationArguments = @($ManagePy, "migrate", "--noinput")
    $MigrationProcess = Start-Process -FilePath $VirtualEnvironmentPython -ArgumentList $MigrationArguments -Wait -PassThru -NoNewWindow
    if ($MigrationProcess.ExitCode -ne 0) {
        throw "Database migration failed. Review the error above."
    }
}

if (-not $RemoteDatabase) {
    $SuperuserCode = "from django.contrib.auth import get_user_model; print('AGENT_SUPERUSERS|' + str(get_user_model().objects.filter(is_superuser=True).count()))"
    $SuperuserOutput = & $VirtualEnvironmentPython $ManagePy shell -c $SuperuserCode --verbosity 0
    if ($LASTEXITCODE -ne 0) {
        throw "Could not check for a local Django admin account."
    }
    $SuperuserInfo = @($SuperuserOutput | Where-Object { $_ -like "AGENT_SUPERUSERS|*" } | Select-Object -Last 1)
    if ($SuperuserInfo.Count -eq 0) {
        throw "Could not check for a local Django admin account."
    }
    if ([int]($SuperuserInfo[0].Split("|")[1]) -eq 0) {
        $CreateSuperuser = Read-Host "No local Django superuser exists. Create one now? (y/N)"
        if ($CreateSuperuser -match "^(y|yes)$") {
            & $VirtualEnvironmentPython $ManagePy createsuperuser
            if ($LASTEXITCODE -ne 0) {
                throw "Django superuser creation did not finish successfully."
            }
        }
        else {
            Write-Warning "No local superuser exists yet. Use a staff account with assistant permissions, or run '.\.venv-windows312-local\Scripts\python.exe manage.py createsuperuser' before signing in."
        }
    }
}

# Keep the local Django process aligned with the model checked and pulled above,
# even if an older model value is present in the project .env file.
$env:SYAFRA_AGENT_PROVIDER = "ollama"
$env:SYAFRA_AGENT_OLLAMA_MODEL = $OllamaModel
if (-not $env:SYAFRA_AGENT_OLLAMA_URL) {
    $env:SYAFRA_AGENT_OLLAMA_URL = "http://127.0.0.1:11434"
}

Write-Host "Starting Syafra. Sign in with your existing Django admin account."
Write-Host "Assistant: http://127.0.0.1:8000/admin/ai-assistant/"
& $VirtualEnvironmentPython $ManagePy runserver 127.0.0.1:8000

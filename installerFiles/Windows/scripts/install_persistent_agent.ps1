param(
    [Parameter(Mandatory=$true)]
    [string]$groupUuid,
    
    [Parameter(Mandatory=$true)]
    [string]$serverAddr
)

# Enable error handling
$ErrorActionPreference = "Stop"

# Setup logging
$logPath = "$env:ProgramFiles(x86)\Wegweiser\Logs"
if (-not (Test-Path $logPath)) {
    New-Item -ItemType Directory -Path $logPath -Force | Out-Null
}
$logFile = Join-Path $logPath "agent_install.log"

function Write-Log {
    param($Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $Message" | Out-File -FilePath $logFile -Append
    Write-Host $Message
}

function Test-Admin {
    $currentUser = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

try {
    Write-Log "Starting persistent agent installation..."

    # Check for admin rights
    if (-not (Test-Admin)) {
        throw "This script requires administrator privileges. Please run as administrator."
    }

    # Get script directory
    $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
    $appPath = Split-Path -Parent $scriptPath

    # Create .env file for the agent
    Write-Log "Creating .env file..."
    $envContent = @"
DEVICE_UUID=$groupUuid
SERVER_URL=$serverAddr
"@
    $envContent | Out-File -FilePath "$appPath\Scripts\.env" -Encoding UTF8
    Write-Log ".env file created successfully"

    # Install Python dependencies
    Write-Log "Installing Python dependencies..."
    $pythonPath = "$appPath\Agent\python-weg\python.exe"
    if (-not (Test-Path $pythonPath)) {
        throw "Python executable not found at: $pythonPath"
    }

    # Verify Python installation
    $pythonVersion = & $pythonPath --version 2>&1
    Write-Log "Python version: $pythonVersion"

    # Install required packages
    Write-Log "Installing required packages..."
    $requiredPackages = @("pywin32", "websockets", "typing-extensions", "aiohttp", "python-dotenv")
    foreach ($package in $requiredPackages) {
        Write-Log "Installing $package..."
        $pipResult = & $pythonPath -m pip install $package 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install $package: $pipResult"
        }
    }
    Write-Log "All Python dependencies installed successfully"

    # Check if service already exists
    Write-Log "Checking for existing service..."
    $service = Get-Service -Name "WegweiserAgent" -ErrorAction SilentlyContinue
    if ($service) {
        Write-Log "Service already exists, stopping and removing..."
        Stop-Service -Name "WegweiserAgent" -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        & $pythonPath "$appPath\Scripts\persistent_agent.py" remove
        Start-Sleep -Seconds 2
    }

    # Verify persistent_agent.py exists
    $agentScript = "$appPath\Scripts\persistent_agent.py"
    if (-not (Test-Path $agentScript)) {
        throw "persistent_agent.py not found at: $agentScript"
    }

    # Install the Windows service
    Write-Log "Installing Windows service..."
    $serviceResult = & $pythonPath "$agentScript" install 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install Windows service: $serviceResult"
    }
    Write-Log "Windows service installed successfully"

    # Verify service installation
    $service = Get-Service -Name "WegweiserAgent" -ErrorAction SilentlyContinue
    if (-not $service) {
        throw "Service installation appeared successful but service not found"
    }
    Write-Log "Service verified in Windows services"

    # Configure service recovery
    Write-Log "Configuring service recovery options..."
    $scResult = & sc.exe failure "WegweiserAgent" reset= 86400 actions= restart/60000/restart/60000/restart/60000
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Warning: Failed to configure service recovery options: $scResult"
    } else {
        Write-Log "Service recovery options configured successfully"
    }

    # Start the service
    Write-Log "Starting Windows service..."
    Start-Service -Name "WegweiserAgent"
    Write-Log "Windows service started successfully"

    # Verify service is running
    $service = Get-Service -Name "WegweiserAgent"
    if ($service.Status -ne 'Running') {
        throw "Service failed to start. Current status: $($service.Status)"
    }
    Write-Log "Service is running successfully"

    Write-Log "Persistent agent installation completed successfully"
} catch {
    Write-Log "ERROR: Installation failed: $_"
    Write-Log "Stack Trace: $($_.ScriptStackTrace)"
    throw
} 
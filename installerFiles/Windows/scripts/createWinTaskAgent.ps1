"Executing createWinTaskAgent.ps1" | Out-File -FilePath "$env:temp\createWinTaskAgent-debug.txt"
"Removing previous schedules" | Out-File -FilePath "$env:temp\createWinTaskAgent-debug.txt" -Append

$taskNamePattern = "*Weg*"
$tasks = Get-ScheduledTask | Where-Object { $_.TaskName -like $taskNamePattern }
foreach ($task in $tasks) {
    Unregister-ScheduledTask -TaskName $task.TaskName -Confirm:$false
}

"Determining installation paths" | Out-File -FilePath "$env:temp\createWinTaskAgent-debug.txt" -Append

# Derive {app} and Agent paths based on this script's location so we do not
# rely on a hard-coded "C:\\Program Files (x86)" path.
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$appDir    = Split-Path -Parent $scriptDir
$agentDir  = Join-Path $appDir 'Agent'

$pythonExe = Join-Path $agentDir 'python-weg\python.exe'
$agentEntryScript = Join-Path $agentDir 'run_agent.py'

if (-not (Test-Path $pythonExe)) {
    "Python executable not found at: $pythonExe" | Out-File -FilePath "$env:temp\createWinTaskAgent-debug.txt" -Append
    throw "Python executable not found at: $pythonExe"
}

if (-not (Test-Path $agentEntryScript)) {
    "Agent entry script not found at: $agentEntryScript" | Out-File -FilePath "$env:temp\createWinTaskAgent-debug.txt" -Append
    throw "Agent entry script not found at: $agentEntryScript"
}

"Creating schedule" | Out-File -FilePath "$env:temp\createWinTaskAgent-debug.txt" -Append

# Quote the script path inside the argument so spaces are handled correctly,
# but DO NOT quote the working directory itself (quoted working directories
# cause ERROR_DIRECTORY / 0x8007010B in Task Scheduler).
$agentArgument = '"' + $agentEntryScript + '"'

$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument $agentArgument `
    -WorkingDirectory $agentDir

# Create a trigger that runs every 1 minute
$trigger = New-ScheduledTaskTrigger -Once -At 00:00 -RepetitionInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -Settings $settings -TaskName "Wegweiser Agent Task" -Description "Runs Wegweiser Agent"

"complete" | Out-File -FilePath "$env:temp\createWinTaskAgent-debug.txt" -Append

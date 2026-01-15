param (
    [string]$GroupUUID,
    [string]$serverAddr
)

$exePath = "C:\Program Files (x86)\Wegweiser\Agent\python-weg\python.exe"
$scriptPath = "C:\Program Files (x86)\Wegweiser\Agent\run_agent.py"
$args = @("-g", $GroupUUID, "-s", $serverAddr)

$outputFile = "$env:temp\registerAgent-out.txt"
$errorFile = "$env:temp\registerAgent-error.txt"

# Start the process
write-host "Executing $exePath $scriptPath with GroupUUID=$GroupUUID and serverAddr=$serverAddr"
"Executing $exePath $scriptPath -g $GroupUUID -s $serverAddr" | out-file -filepath "$env:temp\registerAgent-debug.txt"

Start-Process -FilePath $exePath -ArgumentList @($scriptPath) + $args -RedirectStandardOutput $outputFile -RedirectStandardError $errorFile -NoNewWindow -Wait

# Log the result
if ($LASTEXITCODE -eq 0) {
    write-host "Registration successful"
    "Registration successful" | out-file -filepath "$env:temp\registerAgent-debug.txt" -Append
} else {
    write-host "Registration failed with exit code $LASTEXITCODE"
    "Registration failed with exit code $LASTEXITCODE" | out-file -filepath "$env:temp\registerAgent-debug.txt" -Append
}
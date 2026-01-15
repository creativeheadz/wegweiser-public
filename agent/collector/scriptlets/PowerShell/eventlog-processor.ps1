# Advanced Event Log Processor
# This script processes Windows event logs, categorizes events, and outputs a structured summary.

# Function to convert timestamps
function Convert-WindowsTime {
    param([Parameter(Mandatory=$true)][string]$WinDate)
    [datetime]::ParseExact($WinDate.Split('.')[0], "yyyyMMddHHmmss", $null).ToString("yyyy-MM-dd HH:mm:ss")
}

# Function to categorize events
function Get-EventCategory {
    param([string]$LogName, [int]$EventID)
    switch ($LogName) {
        "System" {
            if ($EventID -in 1074, 6005, 6006) { return "System Startup/Shutdown" }
            elseif ($EventID -in 7045, 7040) { return "Service Changes" }
            elseif ($EventID -in 10016) { return "DCOM Errors" }
            elseif ($EventID -in 41, 1001, 6008) { return "System Crashes/Unexpected Shutdowns" }
            else { return "Other System Events" }
        }
        "Application" {
            if ($EventID -in 1000, 1001, 1002) { return "Application Crashes" }
            elseif ($EventID -in 11707, 11708, 11724) { return "Software Installation/Uninstallation" }
            else { return "Other Application Events" }
        }
        "Security" {
            if ($EventID -in 4624, 4625) { return "Logon Events" }
            elseif ($EventID -in 4720, 4722, 4724, 4738) { return "User Account Changes" }
            elseif ($EventID -in 4688) { return "Process Creation" }
            elseif ($EventID -in 4663, 4660, 4656) { return "File System Events" }
            else { return "Other Security Events" }
        }
        default { return "Miscellaneous Events" }
    }
}

# Function to process events from a specific log
function Process-EventLog {
    param([string]$LogName, [int]$Days = 30)
    
    $startDate = (Get-Date).AddDays(-$Days)
    $events = Get-WinEvent -FilterHashtable @{LogName=$LogName; StartTime=$startDate} -ErrorAction SilentlyContinue

    $groupedEvents = $events | Group-Object { Get-EventCategory -LogName $LogName -EventID $_.Id } | 
    ForEach-Object {
        $category = $_.Name
        $topEvents = $_.Group | Group-Object Id | Sort-Object Count -Descending | Select-Object -First 5 | ForEach-Object {
            $event = $_.Group[0]
            @{
                EventID = $event.Id
                Count = $_.Count
                LatestOccurrence = Convert-WindowsTime $event.TimeCreated.ToString("yyyyMMddHHmmss")
                Message = $event.Message.Split([Environment]::NewLine)[0] # First line of message
            }
        }
        @{
            Category = $category
            TotalEvents = $_.Count
            TopEvents = $topEvents
        }
    }

    return @{
        LogName = $LogName
        Categories = $groupedEvents
    }
}

# Main execution
$logNames = @("System", "Application", "Security")
$results = @{}

foreach ($log in $logNames) {
    Write-Host "Processing $log log..."
    $results[$log] = Process-EventLog -LogName $log
}

# Output results to JSON
$outputPath = "EventLogSummary_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$results | ConvertTo-Json -Depth 5 | Out-File $outputPath

Write-Host "Event log summary has been saved to $outputPath"

# Generate HTML report
$htmlReport = @"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Event Log Summary Report</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1, h2, h3 { color: #2c3e50; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .category { background-color: #e6f3ff; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Event Log Summary Report</h1>
    <p>Generated on $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')</p>
"@

foreach ($logName in $logNames) {
    $htmlReport += @"
    <h2>$logName Log</h2>
    <table>
        <tr>
            <th>Category</th>
            <th>Total Events</th>
            <th>Top Event ID</th>
            <th>Count</th>
            <th>Latest Occurrence</th>
            <th>Sample Message</th>
        </tr>
"@

    foreach ($category in $results[$logName].Categories) {
        $htmlReport += @"
        <tr class="category">
            <td>$($category.Category)</td>
            <td>$($category.TotalEvents)</td>
            <td colspan="4"></td>
        </tr>
"@
        foreach ($event in $category.TopEvents) {
            $htmlReport += @"
        <tr>
            <td></td>
            <td></td>
            <td>$($event.EventID)</td>
            <td>$($event.Count)</td>
            <td>$($event.LatestOccurrence)</td>
            <td>$($event.Message)</td>
        </tr>
"@
        }
    }

    $htmlReport += "</table>"
}

$htmlReport += @"
</body>
</html>
"@

$htmlPath = "EventLogSummary_$(Get-Date -Format 'yyyyMMdd_HHmmss').html"
$htmlReport | Out-File $htmlPath

Write-Host "HTML report has been saved to $htmlPath"
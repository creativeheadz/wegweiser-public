# Windows Update Vulnerability Assessment Script

# Function to get Windows Update configuration
function Get-WindowsUpdateConfig {
    $AutoUpdateNotificationLevels = @{
        1 = "Never check for updates"
        2 = "Check for updates but let me choose whether to download and install them"
        3 = "Download updates but let me choose whether to install them"
        4 = "Install updates automatically"
    }

    $updateConfig = Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update" -ErrorAction SilentlyContinue
    
    return @{
        AUOptions = $AutoUpdateNotificationLevels[[int]$updateConfig.AUOptions]
        ScheduledInstallDay = $updateConfig.ScheduledInstallDay
        ScheduledInstallTime = $updateConfig.ScheduledInstallTime
        UseWUServer = $updateConfig.UseWUServer
        WUServer = $updateConfig.WUServer
    }
}

# Function to get last installed update date
function Get-LastInstalledUpdateDate {
    $lastUpdate = Get-HotFix | Sort-Object -Property InstalledOn -Descending | Select-Object -First 1
    return $lastUpdate.InstalledOn
}

# Function to get missing updates
function Get-MissingUpdates {
    $session = New-Object -ComObject Microsoft.Update.Session
    $searcher = $session.CreateUpdateSearcher()
    
    try {
        $searchResult = $searcher.Search("IsInstalled=0 and Type='Software' and IsHidden=0")
    }
    catch {
        return @{Error = "Failed to search for updates: $_"}
    }

    $missingUpdates = $searchResult.Updates | ForEach-Object {
        $severity = switch ($_.MsrcSeverity) {
            "Critical" { 1 }
            "Important" { 2 }
            "Moderate" { 3 }
            "Low" { 4 }
            default { 5 }
        }

        @{
            Title = $_.Title
            KB = $_.KBArticleIDs -join ','
            Severity = $_.MsrcSeverity
            SeverityIndex = $severity
            Categories = $_.Categories | ForEach-Object { $_.Name }
            ReleaseDate = $_.LastDeploymentChangeTime
        }
    }

    return $missingUpdates | Sort-Object -Property SeverityIndex
}

# Main execution
$updateAssessment = @{
    ComputerName = $env:COMPUTERNAME
    OSVersion = (Get-WmiObject Win32_OperatingSystem).Caption
    LastBootUpTime = (Get-WmiObject Win32_OperatingSystem).LastBootUpTime
    LastInstalledUpdateDate = Get-LastInstalledUpdateDate
    UpdateConfig = Get-WindowsUpdateConfig
    MissingUpdates = Get-MissingUpdates
    AssessmentDate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
}

# Calculate days since last update
$daysSinceLastUpdate = (New-TimeSpan -Start $updateAssessment.LastInstalledUpdateDate -End (Get-Date)).Days
$updateAssessment.DaysSinceLastUpdate = $daysSinceLastUpdate

# Perform vulnerability assessment
$criticalUpdates = ($updateAssessment.MissingUpdates | Where-Object { $_.Severity -eq "Critical" }).Count
$importantUpdates = ($updateAssessment.MissingUpdates | Where-Object { $_.Severity -eq "Important" }).Count

$updateAssessment.VulnerabilityAssessment = @{
    Status = if ($criticalUpdates -gt 0) {
        "Critical"
    } elseif ($importantUpdates -gt 0) {
        "Vulnerable"
    } elseif ($daysSinceLastUpdate -gt 30) {
        "Potentially Vulnerable"
    } else {
        "Low Risk"
    }
    Reasoning = @()
}

if ($criticalUpdates -gt 0) {
    $updateAssessment.VulnerabilityAssessment.Reasoning += "There are $criticalUpdates critical updates missing."
}
if ($importantUpdates -gt 0) {
    $updateAssessment.VulnerabilityAssessment.Reasoning += "There are $importantUpdates important updates missing."
}
if ($daysSinceLastUpdate -gt 30) {
    $updateAssessment.VulnerabilityAssessment.Reasoning += "It has been $daysSinceLastUpdate days since the last update was installed."
}
if ($updateAssessment.UpdateConfig.AUOptions -eq "Never check for updates") {
    $updateAssessment.VulnerabilityAssessment.Reasoning += "Automatic updates are disabled."
}

# Output results to JSON
$outputPath = "WindowsUpdateAssessment_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$updateAssessment | ConvertTo-Json -Depth 5 | Out-File $outputPath

Write-Host "Windows Update vulnerability assessment has been saved to $outputPath"
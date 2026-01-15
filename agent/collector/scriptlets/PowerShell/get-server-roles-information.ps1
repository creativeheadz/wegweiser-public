# Function to get Hyper-V details
function Get-HyperVDetails {
    if (Get-Command Get-VM -ErrorAction SilentlyContinue) {
        $vms = Get-VM
        return @{
            VMCount = $vms.Count
            TotalMemory = ($vms | Measure-Object -Property MemoryAssigned -Sum).Sum
            TotalCPU = ($vms | Measure-Object -Property ProcessorCount -Sum).Sum
            RunningVMs = ($vms | Where-Object {$_.State -eq 'Running'}).Count
        }
    }
    return $null
}

# Function to get FTP details
function Get-FTPDetails {
    if (Get-Command Get-WebConfigurationProperty -ErrorAction SilentlyContinue) {
        $ftpSites = Get-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST'  -filter "system.applicationHost/sites/site/ftpServer" -name *
        return @{
            FTPSitesCount = $ftpSites.Count
            AnonymousEnabled = ($ftpSites | Where-Object { $_.ftpServer.security.authentication.anonymousAuthentication.enabled -eq $true }).Count
        }
    }
    return $null
}

# Get installed roles
$roles = Get-WindowsFeature | Where-Object {$_.Installed -eq $true}

# Prepare the result object
$result = @{
    ComputerName = $env:COMPUTERNAME
    OperatingSystem = (Get-CimInstance Win32_OperatingSystem).Caption
    InstalledRoles = @()
    AdditionalInfo = @{}
}

# Process each installed role
foreach ($role in $roles) {
    $roleInfo = @{
        Name = $role.Name
        DisplayName = $role.DisplayName
    }

    # Add role-specific details
    switch ($role.Name) {
        "Hyper-V" {
            $roleInfo.Details = Get-HyperVDetails
        }
        "Web-Ftp-Server" {
            $roleInfo.Details = Get-FTPDetails
        }
        # Add more role-specific detail gatherers here
    }

    $result.InstalledRoles += $roleInfo
}

# Get additional system information
$result.AdditionalInfo = @{
    TotalMemory = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
    ProcessorCount = (Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors
    DiskSpace = Get-CimInstance Win32_LogicalDisk | Where-Object {$_.DriveType -eq 3} | Select-Object DeviceID, @{Name="FreeSpace";Expression={[math]::Round($_.FreeSpace/1GB, 2)}}, @{Name="TotalSpace";Expression={[math]::Round($_.Size/1GB, 2)}}
    NetworkAdapters = Get-NetAdapter | Select-Object Name, InterfaceDescription, MacAddress, LinkSpeed
    InstalledSoftware = Get-CimInstance Win32_Product | Select-Object Name, Version
    RunningServices = Get-Service | Where-Object {$_.Status -eq 'Running'} | Select-Object Name, DisplayName
    ScheduledTasks = Get-ScheduledTask | Where-Object {$_.State -ne 'Disabled'} | Select-Object TaskName, State, LastRunTime, NextRunTime
}

# Generate filename
$dateString = Get-Date -Format "ddMMyyyy"
$fileName = "serverroles-$($env:COMPUTERNAME)$dateString.json"

# Convert the result to JSON and save to file
$result | ConvertTo-Json -Depth 5 | Out-File -FilePath $fileName

Write-Host "Server information has been saved to $fileName"
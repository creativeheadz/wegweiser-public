# Main script to run all extractions

# Function to convert output to JSON and save to file
function Save-JsonOutput($data, $fileName) {
    $data | ConvertTo-Json -Depth 5 | Out-File $fileName
}

# a. System Hardware Configuration
function Get-SystemHardwareConfig {
    $hardware = @{
        CPU = (Get-WmiObject Win32_Processor).Name
        RAM = [math]::Round((Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)
        GPU = (Get-WmiObject Win32_VideoController).Name
        Motherboard = (Get-WmiObject Win32_BaseBoard).Product
        BIOS = (Get-WmiObject Win32_BIOS).SMBIOSBIOSVersion
    }
    Save-JsonOutput $hardware "SystemHardwareConfig.json"
}

# b. System Software Configuration
function Get-SystemSoftwareConfig {
    $software = @{
        OS = (Get-WmiObject Win32_OperatingSystem).Caption
        OSVersion = (Get-WmiObject Win32_OperatingSystem).Version
        LastBootUpTime = (Get-WmiObject Win32_OperatingSystem).LastBootUpTime
        WindowsFirewall = (Get-NetFirewallProfile).Enabled
        AntiVirusProduct = (Get-WmiObject -Namespace root\SecurityCenter2 -Class AntiVirusProduct).displayName
    }
    Save-JsonOutput $software "SystemSoftwareConfig.json"
}

# c. Installed Programs
function Get-InstalledPrograms {
    $programs = Get-WmiObject -Class Win32_Product | Select-Object Name, Version, Vendor
    Save-JsonOutput $programs "InstalledPrograms.json"
}

# d. Recent Application Crashes
function Get-RecentAppCrashes {
    $crashes = Get-WinEvent -FilterHashtable @{LogName='Application'; Level=2} -MaxEvents 50 |
               Where-Object {$_.Message -like "*faulting application*"} |
               Select-Object TimeCreated, Message
    Save-JsonOutput $crashes "RecentAppCrashes.json"
}

# e. System Resources (IRQ list)
function Get-SystemResources {
    $irqList = Get-WmiObject Win32_IRQResource | Select-Object IRQNumber, Name, Hardware
    Save-JsonOutput $irqList "SystemResources.json"
}

# f. Network Configuration
function Get-NetworkConfig {
    $network = Get-NetAdapter | 
               Select-Object Name, InterfaceDescription, Status, LinkSpeed, 
                             @{Name="IPAddress";Expression={(Get-NetIPAddress -InterfaceIndex $_.ifIndex -AddressFamily IPv4).IPAddress}}
    Save-JsonOutput $network "NetworkConfig.json"
}

# g. Storage Information
function Get-StorageInfo {
    $storage = Get-WmiObject Win32_LogicalDisk | 
               Where-Object {$_.DriveType -eq 3} |
               Select-Object DeviceID, VolumeName, 
                             @{Name="SizeGB";Expression={[math]::Round($_.Size / 1GB, 2)}},
                             @{Name="FreeSpaceGB";Expression={[math]::Round($_.FreeSpace / 1GB, 2)}},
                             @{Name="UsedSpacePercent";Expression={[math]::Round(($_.Size - $_.FreeSpace) / $_.Size * 100, 2)}}
    Save-JsonOutput $storage "StorageInfo.json"
}

# Run all functions
Get-SystemHardwareConfig
Get-SystemSoftwareConfig
Get-InstalledPrograms
Get-RecentAppCrashes
Get-SystemResources
Get-NetworkConfig
Get-StorageInfo

Write-Host "All data has been extracted and saved to JSON files."
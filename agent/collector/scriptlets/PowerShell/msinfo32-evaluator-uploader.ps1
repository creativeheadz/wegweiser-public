# Advanced msinfo32 Processor and Uploader

# Import required modules
Add-Type -AssemblyName System.Web.Extensions

# Function to convert timestamps
function Convert-WindowsTime {
    param([Parameter(Mandatory=$true)][string]$WinDate)
    [datetime]::ParseExact($WinDate.Split('.')[0], "yyyyMMddHHmmss", $null).ToString("yyyy-MM-dd HH:mm:ss")
}

# Function to save JSON output
function Save-JsonOutput($data, $fileName) {
    $data | ConvertTo-Json -Depth 5 | Out-File $fileName
}

# Function to post data to the endpoint
function Post-ToEndpoint($data, $deviceUuid, $tenantUuid, $specificType) {
    $url = "https://app.wegweiser.tech/ai/device/metadata"
    $body = @{
        tenantuuid = $tenantUuid
        deviceuuid = $deviceUuid
        metalogos_type = "msinfo32-$specificType"
        metalogos = $data
    } | ConvertTo-Json

    $headers = @{
        "Content-Type" = "application/json"
    }

    try {
        $response = Invoke-RestMethod -Uri $url -Method Post -Body $body -Headers $headers
        Write-Host "Data successfully posted to endpoint. Type: msinfo32-$specificType. Response: $($response | ConvertTo-Json)"
    }
    catch {
        Write-Host "Error posting data to endpoint: $_"
    }
}

# Main execution
$deviceUuid = "d9a98bd4-0159-48cb-a2f3-d27ec9cf07e6"
$tenantUuid = "d7f55679-f0ad-402b-a0bb-dc8f870d1c5d"

function Get-SystemHardwareConfig {
    $hardware = @{
        CPU = (Get-WmiObject Win32_Processor).Name
        RAM = [math]::Round((Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)
        GPU = (Get-WmiObject Win32_VideoController).Name
        Motherboard = (Get-WmiObject Win32_BaseBoard).Product
        BIOS = (Get-WmiObject Win32_BIOS).SMBIOSBIOSVersion
    }
    Save-JsonOutput $hardware "SystemHardwareConfig.json"
    Post-ToEndpoint $hardware $deviceUuid $tenantUuid "SystemHardwareConfig"
}

function Get-SystemSoftwareConfig {
    $software = @{
        OS = (Get-WmiObject Win32_OperatingSystem).Caption
        OSVersion = (Get-WmiObject Win32_OperatingSystem).Version
        LastBootUpTime = (Get-WmiObject Win32_OperatingSystem).LastBootUpTime
        WindowsFirewall = (Get-NetFirewallProfile).Enabled
        AntiVirusProduct = (Get-WmiObject -Namespace root\SecurityCenter2 -Class AntiVirusProduct).displayName
    }
    Save-JsonOutput $software "SystemSoftwareConfig.json"
    Post-ToEndpoint $software $deviceUuid $tenantUuid "SystemSoftwareConfig"
}

function Get-InstalledPrograms {
    $programs = Get-WmiObject -Class Win32_Product | Select-Object Name, Version, Vendor
    Save-JsonOutput $programs "InstalledPrograms.json"
    Post-ToEndpoint $programs $deviceUuid $tenantUuid "InstalledPrograms"
}

function Get-SystemResources {
    $irqList = Get-WmiObject Win32_IRQResource | Select-Object IRQNumber, Name, Hardware
    Save-JsonOutput $irqList "SystemResources.json"
    Post-ToEndpoint $irqList $deviceUuid $tenantUuid "SystemResources"
}

function Get-NetworkConfig {
    $network = Get-NetAdapter | 
               Select-Object Name, InterfaceDescription, Status, LinkSpeed, 
                             @{Name="IPAddress";Expression={(Get-NetIPAddress -InterfaceIndex $_.ifIndex -AddressFamily IPv4).IPAddress}}
    Save-JsonOutput $network "NetworkConfig.json"
    Post-ToEndpoint $network $deviceUuid $tenantUuid "NetworkConfig"
}

function Get-StorageInfo {
    $storage = Get-WmiObject Win32_LogicalDisk | 
               Where-Object {$_.DriveType -eq 3} |
               Select-Object DeviceID, VolumeName, 
                             @{Name="SizeGB";Expression={[math]::Round($_.Size / 1GB, 2)}},
                             @{Name="FreeSpaceGB";Expression={[math]::Round($_.FreeSpace / 1GB, 2)}},
                             @{Name="UsedSpacePercent";Expression={[math]::Round(($_.Size - $_.FreeSpace) / $_.Size * 100, 2)}}
    Save-JsonOutput $storage "StorageInfo.json"
    Post-ToEndpoint $storage $deviceUuid $tenantUuid "StorageInfo"
}

# Run all functions
Get-SystemHardwareConfig
Get-SystemSoftwareConfig
Get-InstalledPrograms
Get-SystemResources
Get-NetworkConfig
Get-StorageInfo

Write-Host "All data has been extracted, saved to JSON files, and posted to the endpoint."

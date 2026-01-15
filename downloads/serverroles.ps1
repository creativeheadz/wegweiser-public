$serverRolesData = @{
    "ServerRoles" = @()
    "Features" = @()
    "Timestamp" = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
}

# Check if it's a Windows Server
$isServer = (Get-WmiObject -Class Win32_OperatingSystem).ProductType -ne 1

if ($isServer) {
    # Get all installed roles and features
    $roles = Get-WindowsFeature | Where-Object {$_.Installed -eq $true}
    
    foreach ($role in $roles) {
        if ($role.FeatureType -eq "Role") {
            $roleInfo = @{
                "Name" = $role.Name
                "DisplayName" = $role.DisplayName
                "Description" = $role.Description
                "SubFeatures" = @($role.SubFeatures)
            }
            $serverRolesData.ServerRoles += $roleInfo
        } else {
            $featureInfo = @{
                "Name" = $role.Name
                "DisplayName" = $role.DisplayName
                "Description" = $role.Description
            }
            $serverRolesData.Features += $featureInfo
        }
    }
} else {
    $serverRolesData.Add("Error", "Not a Windows Server operating system")
}

# Output as JSON
$serverRolesData | ConvertTo-Json -Depth 10
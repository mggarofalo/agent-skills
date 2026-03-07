# PowerShellGet & Gallery Reference

## Overview

**PowerShell Gallery** (https://www.powershellgallery.com) is the central repository for PowerShell modules, scripts, and DSC resources.

**PSResourceGet** (`Microsoft.PowerShell.PSResourceGet`) is the modern replacement for PowerShellGet:
- Ships with PowerShell 7.4+
- Faster and more reliable than legacy PowerShellGet
- Uses `*-PSResource` cmdlet naming

### Legacy vs Modern Cmdlets
| Legacy (PowerShellGet) | Modern (PSResourceGet) |
|------------------------|------------------------|
| `Find-Module` | `Find-PSResource` |
| `Install-Module` | `Install-PSResource` |
| `Update-Module` | `Update-PSResource` |
| `Uninstall-Module` | `Uninstall-PSResource` |
| `Get-InstalledModule` | `Get-InstalledPSResource` |
| `Publish-Module` | `Publish-PSResource` |

---

## Setup

```powershell
# Check installed version
Get-Module -Name Microsoft.PowerShell.PSResourceGet -ListAvailable

# Install/update PSResourceGet
Install-Module -Name Microsoft.PowerShell.PSResourceGet -Force

# Configure PSGallery
Get-PSResourceRepository
Register-PSResourceRepository -PSGallery  # if not present
Set-PSResourceRepository -Name PSGallery -Trusted
```

---

## Finding Modules

```powershell
Find-PSResource -Name 'Az.Compute'
Find-PSResource -Name 'Az.*'
Find-PSResource -Tag 'Azure', 'Cloud'
Find-PSResource -Name 'Pester' -Version '*'        # all versions
Find-PSResource -Name 'Az' -Version '[5.0,7.0)'    # version range
Find-PSResource -CommandName 'Invoke-RestMethod'
```

### Version Range Syntax (NuGet)
| Syntax | Meaning |
|--------|---------|
| `1.0.0` | Exact version |
| `[1.0,2.0]` | >= 1.0 AND <= 2.0 |
| `[1.0,2.0)` | >= 1.0 AND < 2.0 |
| `(1.0,)` | > 1.0 |
| `[,2.0]` | <= 2.0 |

---

## Installing Modules

```powershell
Install-PSResource -Name 'Az.Compute'                              # latest stable
Install-PSResource -Name 'Pester' -Version '5.0.0'                # specific version
Install-PSResource -Name 'PSReadLine' -Scope CurrentUser -TrustRepository
Install-PSResource -Name 'PSReadLine' -Scope AllUsers              # requires admin
Install-PSResource -Name 'Az' -Prerelease
```

---

## Managing Modules

```powershell
Get-InstalledPSResource
Get-InstalledPSResource -Name 'Az.*'

Update-PSResource -Name 'Az.Compute'
Update-PSResource -Name '*'  # update all

Uninstall-PSResource -Name 'Pester' -Version '4.0.0'
Uninstall-PSResource -Name 'Pester' -Version '*'  # all versions

Save-PSResource -Name 'Az.Compute' -Path 'C:\OfflineModules'  # download without install
```

---

## Common Patterns

### Install if Missing
```powershell
function Ensure-Module {
    param([string]$Name, [string]$MinVersion)
    $installed = Get-InstalledPSResource -Name $Name -ErrorAction SilentlyContinue
    if (-not $installed -or ($MinVersion -and $installed.Version -lt $MinVersion)) {
        Install-PSResource -Name $Name -Scope CurrentUser -TrustRepository
    }
    Import-Module $Name
}
Ensure-Module -Name 'Az.Compute' -MinVersion '5.0.0'
```

### Bulk Install from List
```powershell
$modules = @(
    @{ Name = 'Pester'; Version = '5.0.0' }
    @{ Name = 'PSReadLine' }
)
foreach ($mod in $modules) {
    $params = @{ Name = $mod.Name; Scope = 'CurrentUser'; TrustRepository = $true }
    if ($mod.Version) { $params.Version = $mod.Version }
    Install-PSResource @params
}
```

---

## Publishing Modules

```powershell
# Module manifest minimum fields
@{
    RootModule        = 'MyModule.psm1'
    ModuleVersion     = '1.0.0'
    GUID              = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
    Author            = 'Your Name'
    Description       = 'Module description'
    PowerShellVersion = '5.1'
    FunctionsToExport = @('Get-MyFunction')
    Tags              = @('Utility', 'Automation')
}

# Publish
$apiKey = 'your-api-key'
Publish-PSResource -Path './MyModule' -ApiKey $apiKey -Repository PSGallery
Publish-PSResource -Path './MyModule' -ApiKey $apiKey -WhatIf  # dry run
```

---

## Useful Links

- **PowerShell Gallery**: https://www.powershellgallery.com
- **PSResourceGet Docs**: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.psresourceget/
- **Module Browser**: https://learn.microsoft.com/en-us/powershell/module/

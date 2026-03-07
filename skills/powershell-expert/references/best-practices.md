# PowerShell Best Practices Reference

## Naming Conventions

### Cmdlet/Function Names
- **Verb-Noun format**: Always use approved verbs from `Get-Verb`
- **Pascal Case**: Capitalize first letter of verb and all noun terms
- **Singular Nouns**: Even for cmdlets operating on multiple items

```powershell
# Good
Get-SQLServer
New-AzureStorageAccount
Remove-UserSession

# Bad
Get-Server           # Too generic
Get-Servers          # Plural noun
get-sqlserver        # Wrong case
```

### Parameter Names
- **Pascal Case**: `ErrorAction`, not `errorAction`
- **Singular Names**: Unless parameter always accepts arrays
- **Standard Names**: Use established parameter names with aliases

```powershell
param(
    [Parameter(Mandatory)]
    [string]$Name,

    [Alias('ComputerName', 'CN')]
    [string]$Server,

    [string[]]$Tags  # Plural - accepts array
)
```

### Variable Names
- **$PascalCase** for script/global scope
- **$camelCase** acceptable for local scope

---

## Parameter Design

### Use Strong Typing
```powershell
param(
    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$Name,

    [ValidateRange(1, 100)]
    [int]$Count = 10,

    [ValidateSet('Debug', 'Info', 'Warning', 'Error')]
    [string]$LogLevel = 'Info',

    [switch]$Force,

    [nullable[bool]]$Enabled  # Three states: true, false, unspecified
)
```

### Parameter Sets
```powershell
[CmdletBinding(DefaultParameterSetName = 'ByName')]
param(
    [Parameter(ParameterSetName = 'ByName', Position = 0)]
    [string]$Name,

    [Parameter(ParameterSetName = 'ByID')]
    [int]$ID,

    [Parameter(ParameterSetName = 'ByObject', ValueFromPipeline)]
    [PSObject]$InputObject
)
```

### Common Parameters to Support
| Parameter | Use Case |
|-----------|----------|
| `-Force` | Override warnings/protections |
| `-PassThru` | Return modified objects |
| `-WhatIf` | Preview changes without executing |
| `-Confirm` | Prompt before executing |
| `-Verbose` | Detailed operational info |

---

## Pipeline Support

### Accept Pipeline Input
```powershell
param(
    [Parameter(ValueFromPipeline)]
    [string[]]$Name,

    [Parameter(ValueFromPipelineByPropertyName)]
    [Alias('FullName')]
    [string]$Path
)

process {
    foreach ($item in $Name) {
        Write-Output $result
    }
}
```

### Write Objects Immediately
```powershell
# Good - stream output
foreach ($item in $collection) {
    $result = Process-Item $item
    Write-Output $result
}

# Bad - buffer then output
$results = @()
foreach ($item in $collection) {
    $results += Process-Item $item
}
$results
```

---

## Error Handling

### Use Try/Catch with Specific Errors
```powershell
try {
    $result = Get-Content -Path $Path -ErrorAction Stop
}
catch [System.IO.FileNotFoundException] {
    Write-Error "File not found: $Path"
    return
}
catch [System.UnauthorizedAccessException] {
    Write-Error "Access denied: $Path"
    return
}
catch {
    Write-Error "Unexpected error: $_"
    throw
}
```

### Terminating vs Non-Terminating Errors
```powershell
# Terminating - stops execution
throw "Critical error occurred"
$PSCmdlet.ThrowTerminatingError($errorRecord)

# Non-terminating - continues execution
Write-Error "Problem with item: $item"
$PSCmdlet.WriteError($errorRecord)
```

### Feedback Methods
```powershell
Write-Warning "File will be overwritten"
Write-Verbose "Processing file: $Path"         # requires -Verbose
Write-Debug "Variable state: $($var | ConvertTo-Json)"  # requires -Debug
Write-Progress -Activity "Processing" -Status "Item $i of $total" -PercentComplete (($i / $total) * 100)
```

---

## Output Patterns

### Return Typed Objects
```powershell
[PSCustomObject]@{
    PSTypeName = 'MyModule.ServerInfo'
    Name       = $server.Name
    Status     = $server.Status
    IPAddress  = $server.IP
}
```

### ShouldProcess Pattern
```powershell
function Remove-Item {
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
    param([string]$Path)

    if ($PSCmdlet.ShouldProcess($Path, 'Delete')) {
        # Perform deletion
    }
}
```

---

## Code Style

### Avoid Aliases in Scripts
```powershell
# Good
Get-ChildItem | Where-Object { $_.Length -gt 1MB } | ForEach-Object { $_.Name }

# Bad
gci | ? { $_.Length -gt 1MB } | % { $_.Name }
```

### Splatting for Readability
```powershell
$params = @{
    Path        = $sourcePath
    Destination = $destPath
    Recurse     = $true
    Force       = $true
    ErrorAction = 'Stop'
}
Copy-Item @params
```

### Line Continuation
```powershell
# Good - natural breaks after pipe operators
Get-Process |
    Where-Object { $_.CPU -gt 100 } |
    Sort-Object CPU -Descending |
    Select-Object -First 10

# Avoid backticks for continuation
```

### Comment-Based Help
```powershell
function Get-ServerStatus {
    <#
    .SYNOPSIS
        Gets the status of specified servers.
    .DESCRIPTION
        Retrieves operational status including CPU, memory, and network info.
    .PARAMETER Name
        The server name(s) to query.
    .EXAMPLE
        Get-ServerStatus -Name 'Server01'
    .EXAMPLE
        'Server01', 'Server02' | Get-ServerStatus
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory, ValueFromPipeline)]
        [string[]]$Name
    )
}
```

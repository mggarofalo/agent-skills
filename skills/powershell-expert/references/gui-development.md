# PowerShell GUI Development Reference

> **Note**: GUI development works on Windows platforms only.

## Windows Forms Basics

### Required Assemblies
```powershell
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
```

### Form Creation Pattern
```powershell
$form = New-Object System.Windows.Forms.Form -Property @{
    Text            = 'Application Title'
    Size            = New-Object System.Drawing.Size(400, 300)
    StartPosition   = 'CenterScreen'
    FormBorderStyle = 'FixedDialog'
    MaximizeBox     = $false
    MinimizeBox     = $false
    Topmost         = $true
}
```

### Display and Result Handling
```powershell
# Modal dialog - blocks until closed
$result = $form.ShowDialog()

if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    # Process OK action
}

# Non-modal - returns immediately
$form.Show()
```

---

## Common Controls

### Button
```powershell
$button = New-Object System.Windows.Forms.Button -Property @{
    Location     = New-Object System.Drawing.Point(10, 10)
    Size         = New-Object System.Drawing.Size(100, 30)
    Text         = 'Click Me'
    DialogResult = [System.Windows.Forms.DialogResult]::OK
}
$form.Controls.Add($button)
$form.AcceptButton = $button  # Enter key triggers this button
```

### TextBox
```powershell
# Single-line
$textBox = New-Object System.Windows.Forms.TextBox -Property @{
    Location  = New-Object System.Drawing.Point(10, 50)
    Size      = New-Object System.Drawing.Size(200, 20)
    MaxLength = 100
}

# Multi-line
$textArea = New-Object System.Windows.Forms.TextBox -Property @{
    Location   = New-Object System.Drawing.Point(10, 80)
    Size       = New-Object System.Drawing.Size(300, 150)
    Multiline  = $true
    ScrollBars = 'Vertical'
    WordWrap   = $true
}

# Password field
$passwordBox = New-Object System.Windows.Forms.TextBox -Property @{
    Location     = New-Object System.Drawing.Point(10, 240)
    Size         = New-Object System.Drawing.Size(200, 20)
    PasswordChar = '*'
}
```

### ComboBox (Dropdown)
```powershell
$comboBox = New-Object System.Windows.Forms.ComboBox -Property @{
    Location      = New-Object System.Drawing.Point(10, 40)
    Size          = New-Object System.Drawing.Size(200, 20)
    DropDownStyle = 'DropDownList'  # Read-only selection
}
$comboBox.Items.AddRange(@('Option 1', 'Option 2', 'Option 3'))
$comboBox.SelectedIndex = 0
```

### ListBox
```powershell
$listBox = New-Object System.Windows.Forms.ListBox -Property @{
    Location      = New-Object System.Drawing.Point(10, 70)
    Size          = New-Object System.Drawing.Size(200, 100)
    SelectionMode = 'MultiExtended'  # Allow multi-select with Ctrl/Shift
}
$listBox.Items.AddRange(@('Item 1', 'Item 2', 'Item 3'))
```

### CheckBox / RadioButton
```powershell
$checkBox = New-Object System.Windows.Forms.CheckBox -Property @{
    Location = New-Object System.Drawing.Point(10, 180)
    Size     = New-Object System.Drawing.Size(200, 20)
    Text     = 'Enable feature'
    Checked  = $true
}

$groupBox = New-Object System.Windows.Forms.GroupBox -Property @{
    Location = New-Object System.Drawing.Point(10, 210)
    Size     = New-Object System.Drawing.Size(200, 80)
    Text     = 'Select Option'
}
$radio1 = New-Object System.Windows.Forms.RadioButton -Property @{
    Location = New-Object System.Drawing.Point(10, 20)
    Size     = New-Object System.Drawing.Size(150, 20)
    Text     = 'Option A'
    Checked  = $true
}
$groupBox.Controls.Add($radio1)
```

### ProgressBar
```powershell
$progressBar = New-Object System.Windows.Forms.ProgressBar -Property @{
    Location = New-Object System.Drawing.Point(10, 330)
    Size     = New-Object System.Drawing.Size(300, 20)
    Minimum  = 0
    Maximum  = 100
    Value    = 0
    Style    = 'Continuous'  # or 'Marquee' for indeterminate
}
```

### DataGridView
```powershell
$dataGrid = New-Object System.Windows.Forms.DataGridView -Property @{
    Location              = New-Object System.Drawing.Point(10, 10)
    Size                  = New-Object System.Drawing.Size(400, 200)
    AutoSizeColumnsMode   = 'Fill'
    ReadOnly              = $true
    AllowUserToAddRows    = $false
}
$data = Get-Process | Select-Object Name, CPU, WorkingSet -First 10
$dataGrid.DataSource = [System.Collections.ArrayList]@($data)
```

---

## Layout Patterns

### Anchoring (Resize Handling)
```powershell
$textBox.Anchor = [System.Windows.Forms.AnchorStyles]::Top -bor
                  [System.Windows.Forms.AnchorStyles]::Left -bor
                  [System.Windows.Forms.AnchorStyles]::Right
```

### TableLayoutPanel
```powershell
$tableLayout = New-Object System.Windows.Forms.TableLayoutPanel -Property @{
    Location    = New-Object System.Drawing.Point(10, 10)
    Size        = New-Object System.Drawing.Size(380, 200)
    ColumnCount = 2
    RowCount    = 3
}
$tableLayout.ColumnStyles.Add((New-Object System.Windows.Forms.ColumnStyle('Percent', 30)))
$tableLayout.ColumnStyles.Add((New-Object System.Windows.Forms.ColumnStyle('Percent', 70)))
$tableLayout.Controls.Add($label, 0, 0)
$tableLayout.Controls.Add($textBox, 1, 0)
```

---

## Event Handling

### Common Events
```powershell
$button.Add_Click({
    [System.Windows.Forms.MessageBox]::Show('Clicked!', 'Info')
})

$form.Add_Load({
    $textBox.Focus()
})

$form.Add_FormClosing({
    param($sender, $e)
    $result = [System.Windows.Forms.MessageBox]::Show('Are you sure?', 'Confirm', 'YesNo', 'Question')
    if ($result -eq 'No') { $e.Cancel = $true }
})

$textBox.Add_TextChanged({
    $button.Enabled = $textBox.Text.Length -gt 0
})
```

### Timer for Background Updates
```powershell
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 1000  # 1 second
$timer.Add_Tick({
    $label.Text = "Time: $(Get-Date -Format 'HH:mm:ss')"
})
$timer.Start()
# $timer.Stop() when done
```

---

## WPF with XAML

```powershell
Add-Type -AssemblyName PresentationFramework

[xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="WPF Application" Height="300" Width="400"
        WindowStartupLocation="CenterScreen">
    <Grid Margin="10">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
            <RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>
        <Label Grid.Row="0" Content="Enter text:"/>
        <TextBox Grid.Row="1" x:Name="InputText" Margin="0,5"/>
        <StackPanel Grid.Row="2" Orientation="Horizontal" HorizontalAlignment="Right">
            <Button x:Name="OKButton" Content="OK" Width="75" Margin="5"/>
            <Button x:Name="CancelButton" Content="Cancel" Width="75" Margin="5"/>
        </StackPanel>
    </Grid>
</Window>
"@

$reader = New-Object System.Xml.XmlNodeReader $xaml
$window = [Windows.Markup.XamlReader]::Load($reader)

$inputText   = $window.FindName('InputText')
$okButton    = $window.FindName('OKButton')
$cancelButton = $window.FindName('CancelButton')

$okButton.Add_Click({
    $script:result = $inputText.Text
    $window.DialogResult = $true
    $window.Close()
})
$cancelButton.Add_Click({
    $window.DialogResult = $false
    $window.Close()
})

$null = $window.ShowDialog()
```

**WPF advantages over WinForms**: better styling, data binding, MVVM support, vector graphics, modern controls.

---

## GUI Templates

### Input Dialog
```powershell
function Show-InputDialog {
    param(
        [string]$Title = 'Input',
        [string]$Prompt = 'Enter value:',
        [string]$DefaultValue = ''
    )

    Add-Type -AssemblyName System.Windows.Forms, System.Drawing

    $form = New-Object System.Windows.Forms.Form -Property @{
        Text = $Title; Size = New-Object System.Drawing.Size(350, 150)
        StartPosition = 'CenterScreen'; FormBorderStyle = 'FixedDialog'
        MaximizeBox = $false; MinimizeBox = $false
    }
    $label   = New-Object System.Windows.Forms.Label   -Property @{ Location = New-Object System.Drawing.Point(10,15); Size = New-Object System.Drawing.Size(320,20); Text = $Prompt }
    $textBox = New-Object System.Windows.Forms.TextBox -Property @{ Location = New-Object System.Drawing.Point(10,40); Size = New-Object System.Drawing.Size(310,20); Text = $DefaultValue }
    $ok      = New-Object System.Windows.Forms.Button  -Property @{ Location = New-Object System.Drawing.Point(160,75); Size = New-Object System.Drawing.Size(75,23); Text = 'OK';     DialogResult = [System.Windows.Forms.DialogResult]::OK }
    $cancel  = New-Object System.Windows.Forms.Button  -Property @{ Location = New-Object System.Drawing.Point(245,75); Size = New-Object System.Drawing.Size(75,23); Text = 'Cancel'; DialogResult = [System.Windows.Forms.DialogResult]::Cancel }

    $form.AcceptButton = $ok; $form.CancelButton = $cancel
    $form.Controls.AddRange(@($label, $textBox, $ok, $cancel))
    $form.Add_Shown({ $textBox.Select() })

    if ($form.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { return $textBox.Text }
    return $null
}
```

### File / Folder Browser
```powershell
function Show-FileBrowser {
    param([string]$Title = 'Select File', [string]$Filter = 'All files (*.*)|*.*', [switch]$MultiSelect)
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.OpenFileDialog -Property @{
        Title = $Title; Filter = $Filter; Multiselect = $MultiSelect
    }
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        return ($MultiSelect ? $dialog.FileNames : $dialog.FileName)
    }
    return $null
}

function Show-FolderBrowser {
    param([string]$Description = 'Select folder')
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog -Property @{ Description = $Description }
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { return $dialog.SelectedPath }
    return $null
}
```

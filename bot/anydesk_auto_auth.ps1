param([string]$password = "St@313326339")
Add-Type -AssemblyName System.Windows.Forms
$wshell = New-Object -ComObject WScript.Shell
$start = Get-Date
$injected = $false

while (((Get-Date) - $start).TotalSeconds -lt 20) {
    # Check for AnyDesk or Authorization window
    $activated = $wshell.AppActivate("Authorization")
    if (-not $activated) {
        $activated = $wshell.AppActivate("AnyDesk")
    }
    if ($activated) {
        Start-Sleep -Milliseconds 350
        try {
            # Try clipboard paste first for exact character fidelity
            [System.Windows.Forms.Clipboard]::SetText($password)
            [System.Windows.Forms.SendKeys]::SendWait("^v")
        } catch {
            # Fallback direct send
            [System.Windows.Forms.SendKeys]::SendWait($password)
        }
        Start-Sleep -Milliseconds 150
        # Tab to "Log in automatically from now on"
        [System.Windows.Forms.SendKeys]::SendWait("{TAB}")
        Start-Sleep -Milliseconds 150
        # Space to check the box
        [System.Windows.Forms.SendKeys]::SendWait(" ")
        Start-Sleep -Milliseconds 150
        # Submit OK
        [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
        Write-Output "SUCCESS_INJECTED"
        $injected = $true
        break
    }
    Start-Sleep -Milliseconds 300
}

if (-not $injected) {
    Write-Output "WINDOW_NOT_FOUND_OR_ALREADY_AUTH"
}

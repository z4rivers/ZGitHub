# Auto-backup script for HVAC calculator
# Run this every 30 minutes to auto-commit changes

$repoPath = "C:\ZGitHub"
$logFile = "$repoPath\backup_log.txt"

# Working hours and idle guard
$startHour = 7      # 07:00 local time
$endHour   = 21     # 21:00 local time
$idleLimitMinutes = 10

# Change to repo directory
Set-Location $repoPath

# Get current timestamp
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# Skip outside working hours
$hour = (Get-Date).Hour
if ($hour -lt $startHour -or $hour -gt $endHour) {
    Add-Content -Path $logFile -Value "$timestamp - Skipped: outside working hours ($startHour-$endHour)"
    Write-Host "Skipped: outside working hours"
    exit 0
}

# Skip if user idle for too long
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class IdleTimeHelper {
    [StructLayout(LayoutKind.Sequential)]
    public struct LASTINPUTINFO { public uint cbSize; public uint dwTime; }
    [DllImport("user32.dll")] public static extern bool GetLastInputInfo(ref LASTINPUTINFO plii);
    public static uint GetIdleMilliseconds() {
        LASTINPUTINFO info = new LASTINPUTINFO();
        info.cbSize = (uint)System.Runtime.InteropServices.Marshal.SizeOf(info);
        if (!GetLastInputInfo(ref info)) return 0;
        return (uint)Environment.TickCount - info.dwTime;
    }
}
"@
$idleMs = [IdleTimeHelper]::GetIdleMilliseconds()
if ($idleMs -gt ($idleLimitMinutes * 60 * 1000)) {
    Add-Content -Path $logFile -Value "$timestamp - Skipped: user idle > $idleLimitMinutes min"
    Write-Host "Skipped: user idle"
    exit 0
}

# Check if there are any changes
$status = git status --porcelain

if ($status) {
    # Add all changes
    git add .
    
    # Commit with timestamp
    $commitMessage = "Auto-backup: $timestamp"
    git commit -m $commitMessage
    
    # Log the backup
    Add-Content -Path $logFile -Value "$timestamp - Auto-backup completed"
    Write-Host "Auto-backup completed at $timestamp"

    # Push to GitHub so remote stays current
    git push origin main | Out-Null
    Add-Content -Path $logFile -Value "$timestamp - Pushed to origin/main"
} else {
    Add-Content -Path $logFile -Value "$timestamp - No changes to backup"
    Write-Host "No changes to backup at $timestamp"
}



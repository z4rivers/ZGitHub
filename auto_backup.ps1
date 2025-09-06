# Auto-backup script for HVAC calculator
# Run this every 30 minutes to auto-commit changes

$repoPath = "C:\ZGitHub"
$logFile = "$repoPath\backup_log.txt"

# Change to repo directory
Set-Location $repoPath

# Get current timestamp
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

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
} else {
    Add-Content -Path $logFile -Value "$timestamp - No changes to backup"
    Write-Host "No changes to backup at $timestamp"
}

Write-Output "=== WINDOWS CREDENTIAL MANAGER (github.com) ==="
cmdkey /list:git:https://github.com 2>&1 | Out-String | Write-Output
Write-Output "=== GIT CREDENTIAL HELPERS ==="
git config --show-origin --get-all credential.helper 2>&1 | Out-String | Write-Output

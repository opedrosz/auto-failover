# Verificar sintaxe de todos os modulos Python
$root = 'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover'
Get-ChildItem -Path $root -Recurse -Filter '*.py' -File | Where-Object { -not $_.FullName.Contains('\backups\') } | ForEach-Object {
    $rel = $_.FullName.Replace($root, '')
    $result = & python -m py_compile $_.FullName 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Output ("  [OK] " + $rel)
    } else {
        Write-Output ("  [ERRO] " + $rel)
        $result | ForEach-Object { Write-Output ("      " + $_) }
    }
}
# Backup protegido da V1.0.3 - sem duplicar credenciais
$bk = 'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover\backups\V1.0.3'
$root = 'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover'
$exclude = @('backups','reports','logs','data','checkpoints','config','audit','cache','locks','tests')

# Copiar todos os arquivos .py dos diretorios de componentes
Get-ChildItem -Path $root -Directory | ForEach-Object {
    if ($_.Name -notin $exclude) {
        $dest = Join-Path $bk $_.Name
        if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
        $pyFiles = Get-ChildItem -Path $_.FullName -Filter '*.py' -File
        foreach ($f in $pyFiles) {
            Copy-Item -Path $f.FullName -Destination (Join-Path $dest $f.Name) -Force
        }
    }
}
# Copiar relatorios
if (-not (Test-Path (Join-Path $bk 'reports'))) { New-Item -ItemType Directory -Path (Join-Path $bk 'reports') -Force | Out-Null }
Copy-Item -Path (Join-Path $root 'reports\*.md') -Destination (Join-Path $bk 'reports') -Force

# Registrar manifesto do backup (sem credenciais)
$manifest = @{
    versao = 'V1.0.3'
    data_backup = (Get-Date).ToUniversalTime().ToString('o')
    observacao = 'Backup protegido sem credenciais; somente codigo e documentacao'
    arquivos_py = @(Get-ChildItem -Path $bk -Recurse -Filter '*.py' -File | ForEach-Object { $_.FullName.Replace($bk, '') })
}
$manifest | ConvertTo-Json -Depth 5 | Out-File -FilePath (Join-Path $bk 'manifest.json') -Encoding utf8

Write-Output "Backup concluido:"
Get-ChildItem -Path $bk -Recurse -Filter '*.py' -File | Group-Object DirectoryName | ForEach-Object {
    Write-Output ("  {0}: {1} arquivos" -f $_.Name, $_.Count)
}
Write-Output ("Total .py: " + @(Get-ChildItem -Path $bk -Recurse -Filter '*.py' -File).Count)
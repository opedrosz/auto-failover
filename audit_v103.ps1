# Auditoria da V1.0.4 - estado da V1.0.3
$root = 'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover'

Write-Output "=== 1. TODOS OS ARQUIVOS (exceto backups) ==="
Get-ChildItem -Path $root -Recurse -File | Where-Object { -not $_.FullName.Contains('\backups\') } |
    ForEach-Object { $_.FullName.Replace($root, '') } | Sort-Object

Write-Output ""
Write-Output "=== 2. CONTAGEM POR EXTENSAO ==="
Get-ChildItem -Path $root -Recurse -File | Where-Object { -not $_.FullName.Contains('\backups\') } |
    Group-Object Extension | ForEach-Object { Write-Output ("  {0}: {1}" -f $_.Name, $_.Count) }

Write-Output ""
Write-Output "=== 3. DOCUMENTOS TECNICOS (V1.0.3 alega 15 docs; verificar) ==="
$docsEsperados = @('README.md','AGENTS.md','CHANGELOG.md','ARCHITECTURE.md','SECURITY.md','PROVIDERS.md','MEMORY.md','CHECKPOINTS.md','FAILOVER.md','TESTING.md','USER-GUIDE.md','RECOVERY.md','SKILLS-INTEGRATION.md','ROADMAP.md','REAL-PROVIDERS-VALIDATION-PLAN.md')
foreach ($d in $docsEsperados) {
    $existe = @(Get-ChildItem -Path $root -Recurse -Filter $d -File | Where-Object { -not $_.FullName.Contains('\backups\') }).Count -gt 0
    Write-Output ("  {0}: {1}" -f $d, $(if ($existe) {'PRESENTE'} else {'AUSENTE'}))
}

Write-Output ""
Write-Output "=== 4. RESULTADOS DE TESTES (procurar evidencias dos 2 avisos) ==="
$testFiles = @(Get-ChildItem -Path $root -Recurse -File | Where-Object { $_.Name -match 'test|result|scenario' -and -not $_.FullName.Contains('\backups\') })
if ($testFiles.Count -eq 0) { Write-Output "  NENHUM arquivo de teste/resultado encontrado" }
else { $testFiles | ForEach-Object { Write-Output ("  " + $_.FullName.Replace($root,'')) } }

Write-Output ""
Write-Output "=== 5. VERSAO OPENCODE ==="
opencode --version

Write-Output ""
Write-Output "=== 6. PROVEDORES CONECTADOS ==="
opencode auth list

Write-Output ""
Write-Output "=== 7. PYTHON DISPONIVEL ==="
$py = Get-Command python -ErrorAction SilentlyContinue
if ($py) { Write-Output ("  python: " + $py.Source); python --version }
else { Write-Output "  python: NAO DISPONIVEL no PATH" }
$py3 = Get-Command py -ErrorAction SilentlyContinue
if ($py3) { Write-Output ("  py launcher: " + $py3.Source); py --version }
else { Write-Output "  py launcher: NAO DISPONIVEL" }

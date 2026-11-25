# Consolidacao V1.0.4 - auditoria completa
$root = 'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover'
Write-Output "=== 1. IDENTIFICACAO ==="
Write-Output "Diretorio absoluto: $root"
Write-Output "Versao: V1.0.4"
Write-Output "Repositorio Git: NAO e repositorio git (verificar proposta)"

Write-Output ""
Write-Output "=== 2. INTEGRIDADE DOS ARQUIVOS ==="
$py = @(Get-ChildItem $root -Recurse -Filter '*.py' -File | Where-Object { -not $_.FullName.Contains('\backups\') })
Write-Output ("Arquivos Python (exceto backups): " + $py.Count)
$erros = 0
foreach ($f in $py) {
    $r = & python -m py_compile $f.FullName 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Output ("  ERRO: " + $f.FullName.Replace($root,'')); $erros++ }
}
Write-Output ("Erros de sintaxe: " + $erros)

Write-Output ""
Write-Output "=== 3. DOCUMENTACAO EXISTENTE ==="
$docs = @('README.md','AGENTS.md','ARCHITECTURE.md','STATUS.md','HANDOFF.md','ROADMAP.md','SECURITY.md','CHANGELOG.md','DECISIONS.md')
foreach ($d in $docs) {
    $p1 = Join-Path $root $d
    $p2 = Join-Path $root (Join-Path 'docs' $d)
    $existe = (Test-Path $p1) -or (Test-Path $p2)
    Write-Output ("  {0}: {1}" -f $d, $(if ($existe) {'PRESENTE'} else {'AUSENTE'}))
}

Write-Output ""
Write-Output "=== 4. VERIFICACAO DE DADOS SENSIVEIS ==="
$padroes = @('sk-[a-zA-Z0-9]{20,}','Bearer\s+[a-zA-Z0-9]{20,}','ghp_[a-zA-Z0-9]{20,}','api[_-]?key\s*[:=]\s*["'']?[a-zA-Z0-9]{16,}')
$arquivos = @(Get-ChildItem $root -Recurse -File | Where-Object { $_.Extension -in @('.py','.md','.json','.jsonl','.txt') -and -not $_.FullName.Contains('\backups\') })
$achados = 0
foreach ($f in $arquivos) {
    $conteudo = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
    foreach ($p in $padroes) {
        if ($conteudo -match $p) { Write-Output ("  POSSIVEL SEGREDO em " + $f.FullName.Replace($root,'')); $achados++ }
    }
}
Write-Output ("Achados: " + $achados)

Write-Output ""
Write-Output "=== 5. .gitignore ==="
$gi = Join-Path $root '.gitignore'
if (Test-Path $gi) { Get-Content $gi } else { Write-Output "  AUSENTE - precisa criar" }

Write-Output ""
Write-Output "=== 6. ESTADO GITHUB / REMOTOS (sem modificacao) ==="
Write-Output "Repositorio atual: NAO e git"
Write-Output "GitHub CLI:"
gh auth status 2>&1 | Out-String | Write-Output

Write-Output ""
Write-Output "=== 7. OUTROS PROJETOS (apenas leitura) ==="
foreach ($p in @('C:\Users\Pedro\Orion','C:\Users\Pedro\ADS-Intelligence')) {
    if (Test-Path $p) {
        Write-Output ("  {0}: existe" -f $p)
        if (Test-Path (Join-Path $p '.git')) {
            Write-Output ("    branch: " + (& git -C $p branch --show-current 2>&1))
        }
    } else { Write-Output ("  {0}: nao encontrado" -f $p) }
}

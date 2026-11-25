$ErrorActionPreference = 'Stop'
$root = 'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover'
Set-Location $root

Write-Output "=== 1. GIT INIT ==="
if (-not (Test-Path (Join-Path $root '.git'))) {
    git init
    Write-Output "Repositorio inicializado"
} else {
    Write-Output "Repositorio ja existe"
}

Write-Output "=== 2. CONFIG LOCAL ==="
git config user.name "Pedro"
git config user.email "281536735+opedrosz@users.noreply.github.com"
git config init.defaultBranch main

Write-Output "=== 3. VERIFICAR .gitignore ==="
Get-Content '.gitignore' | Select-Object -First 5

Write-Output "=== 4. GIT STATUS (antes do add) ==="
git status --short | Select-Object -First 20

Write-Output "=== 5. GIT ADD ==="
git add -A

Write-Output "=== 6. GIT STATUS (staged) ==="
git status --short

Write-Output "=== 7. VERIFICAR SEgredos NO STAGE ==="
$staged = git diff --cached --name-only
$secretos = 0
foreach ($f in $staged) {
    if (Test-Path $f) {
        $conteudo = Get-Content $f -Raw -ErrorAction SilentlyContinue
        if ($conteudo -match 'ghp_[a-zA-Z0-9]{20,}|github_pat_[a-zA-Z0-9_]{20,}') {
            Write-Output ("  ALERTA: possivel token em " + $f)
            $secretos++
        }
    }
}
Write-Output ("  Arquivos staged: " + @($staged).Count + " | Alertas: " + $secretos)

if ($secretos -gt 0) {
    Write-Output "ABORTANDO commit por segredos detectados"
    exit 1
}

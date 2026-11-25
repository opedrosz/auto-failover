$root = 'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover'
Write-Output '=== DOCUMENTACAO FINAL ==='
foreach ($d in @('README.md','AGENTS.md','docs/ARCHITECTURE.md','docs/STATUS.md','docs/HANDOFF.md','docs/ROADMAP.md','docs/SECURITY.md','docs/CHANGELOG.md','docs/DECISIONS.md','.gitignore')) {
    $p = Join-Path $root $d
    $ok = if (Test-Path $p) { 'OK' } else { 'FALTANDO' }
    Write-Output ("  {0}: {1}" -f $d, $ok)
}
Write-Output '=== TESTE FINAL ==='
python (Join-Path $root 'cli.py') status

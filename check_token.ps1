$names = @('GITHUB_TOKEN','GH_TOKEN','GITHUB_PAT','OPENCODE_GITHUB_TOKEN')
foreach ($n in $names) {
    $v = [Environment]::GetEnvironmentVariable($n)
    if ($v) { Write-Output ($n + ': PRESENTE (valor nao exibido)') }
    else { Write-Output ($n + ': ausente') }
}

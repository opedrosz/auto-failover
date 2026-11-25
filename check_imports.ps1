# Verificar imports em runtime de todos os componentes
$root = 'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover'
$dirs = @('orchestrator','provider_registry','Model Selector','health_monitor','cost_controller','checkpoint_manager','failover_manager','task_recovery','shared_memory_manager','security_controller','audit_logger','config_validator','stop_controller','skills_integration','project_manager')

$script = @"
import sys, os
root = r'$root'
dirs = $($dirs | ForEach-Object { "r'$root\\$_'" }) -join ','
paths = [root] + list(dirs)
for p in paths:
    if p not in sys.path: sys.path.insert(0, p)
mods = ['orchestrator','provider_registry','model_selector','health_monitor','cost_controller','checkpoint_manager','failover_manager','task_recovery','shared_memory_manager','security_controller','audit_logger','config_validator','stop_controller','skills_integration','project_manager']
ok = 0; fail = 0
for m in mods:
    try:
        __import__(m)
        print('  [OK] ' + m)
        ok += 1
    except Exception as e:
        print('  [ERRO] ' + m + ': ' + type(e).__name__ + ': ' + str(e)[:200])
        fail += 1
print('TOTAL: OK=' + str(ok) + ' ERRO=' + str(fail))
"@
$script | Out-File -FilePath (Join-Path $root 'check_imports_temp.py') -Encoding utf8
python (Join-Path $root 'check_imports_temp.py')
Remove-Item (Join-Path $root 'check_imports_temp.py') -Force
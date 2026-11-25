#!/usr/bin/env python3
"""Verificar imports de runtime de todos os 15 componentes."""
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
dirs = [
    'orchestrator', 'provider_registry', 'Model Selector', 'health_monitor',
    'cost_controller', 'checkpoint_manager', 'failover_manager', 'task_recovery',
    'shared_memory_manager', 'security_controller', 'audit_logger',
    'config_validator', 'stop_controller', 'skills_integration', 'project_manager'
]
for d in dirs:
    p = str(root / d)
    if p not in sys.path:
        sys.path.insert(0, p)
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

mods = [
    'orchestrator', 'provider_registry', 'model_selector', 'health_monitor',
    'cost_controller', 'checkpoint_manager', 'failover_manager', 'task_recovery',
    'shared_memory_manager', 'security_controller', 'audit_logger',
    'config_validator', 'stop_controller', 'skills_integration', 'project_manager'
]
ok, fail = 0, 0
for m in mods:
    try:
        __import__(m)
        print(f'  [OK] {m}')
        ok += 1
    except Exception as e:
        print(f'  [ERRO] {m}: {type(e).__name__}: {str(e)[:200]}')
        fail += 1
print(f'TOTAL: OK={ok} ERRO={fail}')
sys.exit(0 if fail == 0 else 1)

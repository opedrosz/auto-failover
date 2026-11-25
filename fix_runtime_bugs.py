#!/usr/bin/env python3
"""Corrigir bugs de runtime encontrados na auditoria V1.0.4."""
from pathlib import Path

root = Path(__file__).resolve().parent

# 1. Adicionar 'import os' onde falta
need_os = [
    'orchestrator/orchestrator.py',
    'provider_registry/provider_registry.py',
    'Model Selector/model_selector.py',
    'health_monitor/health_monitor.py',
    'cost_controller/cost_controller.py',
    'failover_manager/failover_manager.py',
    'task_recovery/task_recovery.py',
    'audit_logger/audit_logger.py',
    'config_validator/config_validator.py',
    'skills_integration/skills_integration.py',
]
for rel in need_os:
    p = root / rel
    c = p.read_text(encoding='utf-8')
    if '\nimport os\n' not in c and not c.startswith('import os'):
        # inserir apos 'import json' ou no inicio dos imports
        if '\nimport json\n' in c:
            c = c.replace('\nimport json\n', '\nimport json\nimport os\n', 1)
        else:
            # apos o docstring
            idx = c.find('\n\n')
            c = c[:idx+2] + 'import os\n' + c[idx+2:]
        p.write_text(c, encoding='utf-8')
        print(f'[FIX] import os adicionado: {rel}')

# 2. Corrigir _carregar_orchestrator no checkpoint_manager (falta self)
p = root / 'checkpoint_manager/checkpoint_manager.py'
c = p.read_text(encoding='utf-8')
c = c.replace('    def _carregar_orchestrator():\n        """Carregar orchestrator - metodo estatico placeholder."""\n        pass',
              '    def _carregar_orchestrator(self):\n        """Carregar orchestrator existente ou retornar None."""\n        try:\n            from orchestrator import Orchestrator\n            return Orchestrator(self.base_dir)\n        except Exception as e:\n            logger.debug(f"Orchestrator nao disponivel: {e}")\n            return None')
p.write_text(c, encoding='utf-8')
print('[FIX] _carregar_orchestrator corrigido no checkpoint_manager')

# 3. Adicionar _carregar_project_manager no shared_memory_manager
p = root / 'shared_memory_manager/shared_memory_manager.py'
c = p.read_text(encoding='utf-8')
if 'def _carregar_project_manager' not in c:
    marker = '    def _garantir_diretorios(self):'
    addition = '''    def _carregar_project_manager(self):
        """Carregar Project Manager existente ou retornar None."""
        try:
            from project_manager import ProjectManager
            return ProjectManager(self.base_dir)
        except Exception as e:
            logger.debug(f"Project Manager nao disponivel: {e}")
            return None

'''
    c = c.replace(marker, addition + marker, 1)
    p.write_text(c, encoding='utf-8')
    print('[FIX] _carregar_project_manager adicionado no shared_memory_manager')

print('Correcoes de runtime concluidas.')

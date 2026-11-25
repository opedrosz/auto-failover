#!/usr/bin/env python3
"""CLI local da infraestrutura AUTO FAILOVER V1.0.6."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for d in ['orchestrator', 'provider_registry', 'Model Selector', 'health_monitor',
          'cost_controller', 'checkpoint_manager', 'failover_manager', 'task_recovery',
          'shared_memory_manager', 'security_controller', 'audit_logger',
          'config_validator', 'stop_controller', 'skills_integration',
          'project_manager', 'supervisor', 'adapters']:
    p = str(ROOT / d)
    if p not in sys.path:
        sys.path.insert(0, p)

def cmd_doctor():
    print("=== DOCTOR ===")
    checks = {}
    # Python
    checks['python'] = sys.version.split()[0]
    # OpenCode
    import subprocess
    try:
        r = subprocess.run(['opencode', '--version'], capture_output=True, text=True, timeout=20)
        checks['opencode'] = r.stdout.strip()
    except Exception as e:
        checks['opencode'] = f'ERRO: {e}'
    # Modulos
    mods = ['orchestrator', 'provider_registry', 'model_selector', 'health_monitor',
            'cost_controller', 'checkpoint_manager', 'failover_manager', 'task_recovery',
            'shared_memory_manager', 'security_controller', 'audit_logger',
            'config_validator', 'stop_controller', 'skills_integration', 'project_manager']
    ok = []
    for m in mods:
        try:
            __import__(m)
            ok.append(m)
        except Exception as e:
            print(f"  ERRO modulo {m}: {e}")
    checks['modulos_ok'] = f'{len(ok)}/{len(mods)}'
    for k, v in checks.items():
        print(f"  {k}: {v}")

def cmd_validate():
    from config_validator import ConfigValidator
    v = ConfigValidator(str(ROOT))
    cfg = {
        'provedores': {
            'opencode_console': {'tipo': 'nativo', 'gratuito': True},
            'google_gemini': {'tipo': 'cloud', 'gratuito': True},
            'openrouter': {'tipo': 'roteador', 'gratuito': True},
            'github_copilot': {'tipo': 'assinatura', 'gratuito': False},
            'openai': {'tipo': 'cloud', 'gratuito': False},
        },
        'prioridade': ['opencode_console', 'google_gemini', 'openrouter',
                       'github_copilot', 'openai', 'local_llm'],
        'politica_custo': 'zero_por_padrao',
        'max_custo_usd_sessao': 0.0,
    }
    r = v.validar_todas(cfg, 'CLI')
    print(f"Valido: {r['valido']} | Erros: {len(r['erros'])} | Avisos: {len(r['avisos'])}")
    for e in r['erros']:
        print(f"  ERRO: {e}")

def cmd_providers():
    from provider_registry import ProviderRegistry
    r = ProviderRegistry(str(ROOT))
    print("=== PROVEDORES ===")
    for alias, p in r.provedores.items():
        print(f"  {alias}: {p.get('nome_exibicao')} | tipo={p.get('tipo')} | "
              f"gratuito={p.get('gratuito')} | status={p.get('status')}")

def cmd_models():
    from provider_registry import ProviderRegistry
    r = ProviderRegistry(str(ROOT))
    print("=== MODELOS ===")
    for alias, modelos in r.modelos.items():
        print(f"  {alias}: {len(modelos)} modelos")
        for m in modelos[:5]:
            print(f"    - {m['nome']} (gratuito={m.get('gratuito')}, {m.get('confirmado')})")

def cmd_status():
    print("=== STATUS ===")
    sc = ROOT / 'reports' / 'resultados_testes_v104.json'
    if sc.exists():
        d = json.loads(sc.read_text(encoding='utf-8'))
        print(f"  Ultimos testes: {d['aprovados']}/{d['total']} aprovados")
    demo = ROOT / 'reports' / 'demo_multiagente.json'
    if demo.exists():
        d = json.loads(demo.read_text(encoding='utf-8'))
        print(f"  Demo multiagente: sucesso={d['sucesso_geral']}")
    hal = ROOT / 'reports' / 'homologacao_limitada.json'
    if hal.exists():
        d = json.loads(hal.read_text(encoding='utf-8'))
        print(f"  Homologacao: {d['utilizacao']['total_chamadas']} chamadas, "
              f"custo=${d['utilizacao']['custo_observado_usd']}")

def cmd_history():
    from shared_memory_manager import SharedMemory
    m = SharedMemory(str(ROOT))
    print("=== HISTORICO ===")
    print(json.dumps(m.get_estado_memoria(), ensure_ascii=False, indent=2))

def cmd_test():
    import subprocess
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="auto-failover-tests-") as base:
        return subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=ROOT, env={**os.environ, "AUTO_FAILOVER_BASE": base},
            timeout=300, check=False,
        ).returncode

def cmd_demo_local():
    import subprocess
    return subprocess.run(
        [sys.executable, str(ROOT / "demo" / "demo_failover_v106.py")],
        timeout=90, check=False,
    ).returncode

def cmd_start():
    print("Homologacao externa pendente. Execute: python cli.py demo-local")

def cmd_pause_resume_stop(args):
    from stop_controller import StopController
    s = StopController(str(ROOT))
    if args[0] == 'pause':
        print(s.pausar(args[1], 'cli'))
    elif args[0] == 'resume':
        print(s.retoma(args[1]))
    elif args[0] == 'stop':
        print(s.cancelar(args[1], 'cli'))
    elif args[0] == 'recover':
        from checkpoint_manager import CheckpointManager
        c = CheckpointManager(str(ROOT))
        print(c.recuperar_checkpoint(args[1]))

COMANDOS = {
    'doctor': cmd_doctor, 'validate': cmd_validate, 'providers': cmd_providers,
    'models': cmd_models, 'status': cmd_status, 'history': cmd_history,
    'test': cmd_test, 'demo': cmd_demo_local, 'demo-local': cmd_demo_local, 'start': cmd_start,
}

def main():
    if len(sys.argv) < 2:
        print("Comandos: doctor validate providers models status history test demo demo-local start pause resume stop recover")
        return 1
    cmd = sys.argv[1]
    if cmd in ('pause', 'resume', 'stop', 'recover'):
        if len(sys.argv) < 3:
            print(f"Uso: cli.py {cmd} <task_id>")
            return 1
        cmd_pause_resume_stop([cmd, sys.argv[2]])
        return 0
    if cmd in COMANDOS:
        return COMANDOS[cmd]() or 0
    print(f"Comando desconhecido: {cmd}")
    return 1

if __name__ == '__main__':
    sys.exit(main())

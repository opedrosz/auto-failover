#!/usr/bin/env python3
"""
Homologacao externa limitada - sondagem de modelos gratuitos.
Apenas dados sinteticos. Max 1 chamada por modelo testado nesta sondagem.
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'adapters'))

from opencode_adapter import OpenCodeAdapter, FREE_MODELS, FinancialBlocked

# Modelos candidatos para sondagem (gratuitos confirmados via opencode models)
CANDIDATOS = [
    ('opencode', 'opencode/hy4-flash-free'),
    ('opencode', 'opencode/beam-free'),
]

PROMPT_SINTETICO = (
    "Dados sinteticos de teste. Responda EXATAMENTE com a palavra OK e nada mais. "
    "Nao execute comandos, nao acesse arquivos."
)

resultados = []
adapter = OpenCodeAdapter(str(ROOT), budget_usd=0.0, max_calls=15, max_per_provider=3)

for provedor, modelo in CANDIDATOS:
    print(f"\n=== Sondagem: {provedor}/{modelo} ===")
    try:
        # Verificacao financeira (9 passos)
        dec = adapter.autorizar_chamada(provedor, modelo, dados_sinteticos=True)
        print(f"  Autorizacao financeira: {dec['autorizado']}")
    except FinancialBlocked as e:
        print(f"  BLOQUEADO financeiramente: {e}")
        resultados.append({'modelo': modelo, 'status': 'BLOQUEADO', 'motivo': str(e)})
        continue

    # Verificar identificador real
    ident = adapter.identificar_modelo(modelo)
    print(f"  Identificador existe: {ident.get('existe')}")
    if not ident.get('existe'):
        resultados.append({'modelo': modelo, 'status': 'MODELO_INEXISTENTE'})
        continue

    # Chamada real unica, dados sinteticos
    r = adapter.executar_inferencia(provedor, modelo, PROMPT_SINTETICO, timeout=120)
    print(f"  Sucesso: {r['sucesso']} | returncode: {r.get('returncode')}")
    if r.get('stderr'):
        print(f"  stderr: {r['stderr'][:300]}")
    if r.get('stdout'):
        print(f"  stdout: {r['stdout'][:300]}")

    resultados.append({
        'modelo': modelo,
        'status': 'SUCESSO' if r['sucesso'] else 'FALHA',
        'returncode': r.get('returncode'),
        'stdout_preview': r.get('stdout', '')[:200],
        'stderr_preview': r.get('stderr', '')[:200],
    })

path = ROOT / 'reports' / 'homologacao_limitada.json'
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps({
    'timestamp': datetime.utcnow().isoformat(),
    'tipo': 'HOMOLOGACAO_EXTERNA_LIMITADA',
    'dados': 'SINTETICOS',
    'limites': {'por_provedor': 3, 'total': 15},
    'resultados': resultados,
    'utilizacao': adapter.get_utilizacao(),
}, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"\nResultados salvos: {path}")

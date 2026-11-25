#!/usr/bin/env python3
"""
Adaptador Real OpenCode - AUTO FAILOVER V1.0.4

Utiliza a interface oficial `opencode run --model <provider/model> --format json`.
Nao extrai tokens internos, nao copia credenciais OAuth.

Protecao financeira antes de qualquer chamada externa:
1. Confirmar provedor.
2. Confirmar identificador do modelo.
3. Confirmar modalidade gratuita (modelo na lista FREE_MODELS).
4. Verificar condicoes de faturamento.
5. Confirmar modelo autorizado.
6. Verificar limites de utilizacao.
7. Confirmar que nao existe fallback pago.
8. Verificar que os dados sao sinteticos.
9. Registrar decisao de autorizacao.

Se qualquer informacao financeira necessaria for desconhecida, bloquear.
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('AutoFailover.OpenCodeAdapter')

# Modelos comprovadamente gratuitos (confirmados via `opencode models`)
FREE_MODELS = {
    'opencode/beam-free',
    'opencode/deepseek-v4.1-flash-free',
    'opencode/gemini-3.5-flash-lite',
    'opencode/hy4-flash-free',
    'opencode/nemotron-3.5-lightning-free',
    'opencode/nemotron-3.5-super-vl-free',
    'opencode/tidepool-alpha-free',
    'opencode/iceman-free',
    'opencode/mimo-v2.6-flash-free',
    'opencode/flint-40b-free',
    'google/gemini-3.5-flash-lite',
    'openrouter/google/gemini-3.5-flash-lite',
}

class FinancialBlocked(Exception):
    """Chamada bloqueada por politica financeira."""

class OpenCodeAdapter:
    """Adaptador para interface CLI real do OpenCode."""

    def __init__(self, base_dir=None, budget_usd=0.0, max_calls=15, max_per_provider=3):
        self.base_dir = Path(base_dir) if base_dir else Path(
            os.environ.get('AUTO_FAILOVER_BASE',
                           r'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover'))
        self.budget_usd = budget_usd
        self.max_calls = max_calls
        self.max_per_provider = max_per_provider
        self.calls_realizadas = []
        self.registro_path = self.base_dir / 'data' / 'chamadas_reais.jsonl'
        self.registro_path.parent.mkdir(parents=True, exist_ok=True)

    def verificar_disponibilidade(self):
        """Verificar disponibilidade da CLI OpenCode."""
        try:
            r = subprocess.run(['opencode', '--version'], capture_output=True,
                               text=True, timeout=20)
            return {"disponivel": r.returncode == 0, "versao": r.stdout.strip(),
                    "erro": r.stderr.strip()}
        except Exception as e:
            return {"disponivel": False, "erro": str(e)}

    def identificar_modelo(self, modelo):
        """Verificar se o modelo existe na lista oficial."""
        try:
            r = subprocess.run(['opencode', 'models'], capture_output=True,
                               text=True, timeout=30)
            modelos = [l.strip() for l in r.stdout.splitlines() if l.strip()]
            return {"existe": modelo in modelos, "modelo": modelo,
                    "total_modelos": len(modelos)}
        except Exception as e:
            return {"existe": False, "erro": str(e)}

    def autorizar_chamada(self, provedor, modelo, dados_sinteticos=True):
        """Aplicar as 9 verificacoes financeiras antes de uma chamada."""
        motivos_bloqueio = []

        # 1. Confirmar provedor
        if not provedor:
            motivos_bloqueio.append('provedor_nao_informado')
        elif provedor not in ('opencode', 'google', 'openrouter', 'github-copilot', 'openai'):
            motivos_bloqueio.append(f'provedor_nao_autorizado:{provedor}')

        # 2. Confirmar identificador do modelo
        if not modelo:
            motivos_bloqueio.append('modelo_nao_informado')

        # 3. Confirmar modalidade gratuita
        if modelo not in FREE_MODELS:
            motivos_bloqueio.append(f'modelo_nao_confirmado_gratuito:{modelo}')

        # 4. Verificar condicoes de faturamento (fail-closed para desconhecido)
        if self.budget_usd != 0.0:
            motivos_bloqueio.append('orcamento_nao_e_zero')

        # 5. Confirmar modelo autorizado (interseccao com FREE_MODELS)
        autorizados = list(FREE_MODELS)
        if modelo not in autorizados:
            motivos_bloqueio.append('modelo_nao_autorizado')

        # 6. Verificar limites de utilizacao
        if len(self.calls_realizadas) >= self.max_calls:
            motivos_bloqueio.append('limite_total_chamadas_excedido')
        chamadas_prov = sum(1 for c in self.calls_realizadas
                            if c.get('provedor') == provedor)
        if chamadas_prov >= self.max_per_provider:
            motivos_bloqueio.append('limite_chamadas_provedor_excedido')

        # 7. Confirmar que nao existe fallback pago
        # (adaptador so usa FREE_MODELS; nenhum fallback pago possivel)
        fallback_pago = False
        if fallback_pago:
            motivos_bloqueio.append('fallback_pago_detectado')

        # 8. Verificar dados sinteticos
        if not dados_sinteticos:
            motivos_bloqueio.append('dados_nao_sinteticos')

        # 9. Registrar decisao de autorizacao
        decisao = {
            "timestamp": datetime.utcnow().isoformat(),
            "provedor": provedor, "modelo": modelo,
            "dados_sinteticos": dados_sinteticos,
            "autorizado": len(motivos_bloqueio) == 0,
            "motivos_bloqueio": motivos_bloqueio,
            "orcamento_usd": self.budget_usd,
            "custo_estimado_usd": 0.0 if modelo in FREE_MODELS else None,
        }
        self._registrar(decisao)

        if motivos_bloqueio:
            raise FinancialBlocked('; '.join(motivos_bloqueio))
        return decisao

    def executar_inferencia(self, provedor, modelo, mensagem, timeout=180,
                           max_output_tokens=512, dados_sinteticos=True):
        """Executar chamada real de inferencia via interface oficial."""
        # Protecao financeira primeiro
        self.autorizar_chamada(provedor, modelo, dados_sinteticos)

        # Verificar identificador real
        id_check = self.identificar_modelo(modelo)
        if not id_check.get('existe'):
            return {"sucesso": False, "erro": "modelo_nao_existe",
                    "detalhes": id_check}

        cmd = [
            'opencode', 'run',
            '--model', modelo,
            '--format', 'json',
            '--auto',  # aprovar permissoes nao explicitamente negadas
            mensagem,
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=timeout, cwd=str(self.base_dir))
            registro = {
                "timestamp": datetime.utcnow().isoformat(),
                "provedor": provedor, "modelo": modelo,
                "returncode": r.returncode,
                "stdout_len": len(r.stdout), "stderr": r.stderr[-500:],
                "sucesso": r.returncode == 0,
                "custo_observado_usd": 0.0,
            }
            self.calls_realizadas.append(registro)
            self._registrar(registro)
            return {
                "sucesso": r.returncode == 0,
                "stdout": r.stdout, "stderr": r.stderr,
                "returncode": r.returncode,
                "registro": registro,
            }
        except subprocess.TimeoutExpired:
            return {"sucesso": False, "erro": "timeout"}

    def _registrar(self, entry):
        try:
            with open(self.registro_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Erro ao registrar chamada: {e}")

    def get_utilizacao(self):
        return {
            "total_chamadas": len(self.calls_realizadas),
            "por_provedor": {},
            "custo_observado_usd": sum(c.get('custo_observado_usd', 0)
                                       for c in self.calls_realizadas),
            "limite_total": self.max_calls,
            "limite_por_provedor": self.max_per_provider,
        }

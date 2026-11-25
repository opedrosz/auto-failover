#!/usr/bin/env python3
"""Corrigir as 10 falhas reais encontradas nos testes V1.0.4."""
from pathlib import Path

root = Path(__file__).resolve().parent

# 1. orchestrator: import hashlib
p = root / 'orchestrator/orchestrator.py'
c = p.read_text(encoding='utf-8')
if 'import hashlib' not in c:
    c = c.replace('import json\n', 'import json\nimport hashlib\n', 1)
    p.write_text(c, encoding='utf-8')
    print('[FIX 1] import hashlib no orchestrator')

# 2. audit_logger: garantir diretorio config antes de escrever
p = root / 'audit_logger/audit_logger.py'
c = p.read_text(encoding='utf-8')
old = "        if config_path.exists():"
new = "        config_path.parent.mkdir(parents=True, exist_ok=True)\n        if config_path.exists():"
if new not in c:
    c = c.replace(old, new, 1)
    p.write_text(c, encoding='utf-8')
    print('[FIX 2] config dir no audit_logger')

# 3. supervisor: renomear verificar__processo -> verificar_processo
p = root / 'supervisor/supervisor.py'
c = p.read_text(encoding='utf-8')
c = c.replace('verificar__processo', 'verificar_processo')
p.write_text(c, encoding='utf-8')
print('[FIX 3] nome do metodo no supervisor')

# 4. failover_manager: tratar status 401/403 sem mensagem
p = root / 'failover_manager/failover_manager.py'
c = p.read_text(encoding='utf-8')
old = """        # 7. Falha de autenticacao
        if any(kw in mensagem for kw in ["authentication failed", "auth failed", """
new = """        # 7. Falha de autenticacao
        if status in (401, 403):
            return FailureCategory.AUTHENTICATION_FAILURE
        if any(kw in mensagem for kw in ["authentication failed", "auth failed", """
if new not in c:
    c = c.replace(old, new, 1)
    p.write_text(c, encoding='utf-8')
    print('[FIX 4] status 401/403 no failover_manager')

# 5. checkpoint_manager: recuperar de checkpoint corrompido -> usar anterior
p = root / 'checkpoint_manager/checkpoint_manager.py'
c = p.read_text(encoding='utf-8')
old = """        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
            
            # Validar idempotencia: verificar se checksum confere com contexto atual
            # (Em implementacao completa, compararia com estado atual)
            # Por enquanto, apenas retornar
            
            logger.info(f"Checkpoint recuperado: stage={checkpoint.get('stage')}, "
                         f"checksum={checkpoint.get('checksum', '')[:16]}...")"""
new = """        # Tentar carregar o checkpoint selecionado; se corrompido, tentar anteriores
        checkpoint = None
        candidatos = list(reversed(checkpoints))  # do mais recente ao mais antigo
        if checkpoint_file in candidatos:
            # garantir que o selecionado seja o primeiro
            candidatos.remove(checkpoint_file)
            candidatos.insert(0, checkpoint_file)
        for candidato in candidatos:
            try:
                with open(candidato, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                if candidato != checkpoint_file:
                    logger.warning(f"Checkpoint {checkpoint_file.name} corrompido; "
                                   f"usando checkpoint anterior: {candidato.name}")
                    checkpoint_file = candidato
                break
            except Exception as e:
                logger.warning(f"Checkpoint corrompido ignorado: {candidato.name}: {e}")
                checkpoint = None
        if checkpoint is None:
            logger.error("Todos os checkpoints da tarefa estao corrompidos")
            return None
            
        logger.info(f"Checkpoint recuperado: stage={checkpoint.get('stage')}, "
                     f"checksum={checkpoint.get('checksum', '')[:16]}...")"""
if new not in c:
    # localizar bloco exato com indentacao
    if old in c:
        c = c.replace(old, new, 1)
        p.write_text(c, encoding='utf-8')
        print('[FIX 5] recuperacao de checkpoint corrompido')
    else:
        print('[AVISO FIX 5] bloco nao encontrado - verificar manualmente')

# 6. security_controller: regex de credencial mais flexivel
p = root / 'security_controller/security_controller.py'
c = p.read_text(encoding='utf-8')
old = 'r"sk-[a-zA-Z0-9]{48,}",  # OpenAI API keys'
new = 'r"sk-[a-zA-Z0-9]{8,}",  # OpenAI API keys'
if new not in c:
    c = c.replace(old, new, 1)
    p.write_text(c, encoding='utf-8')
    print('[FIX 6] regex de credencial')

# 7. cost_controller: considerar modelos opencode/* como gratuitos
p = root / 'cost_controller/cost_controller.py'
c = p.read_text(encoding='utf-8')
old = """        # Determinar custo estimado
        if modelo_encontrado and modelo_encontrado.get("gratuito", False):
            custo_estimado = 0.0
            gratuito = True"""
new = """        # Determinar custo estimado
        # Modelos opencode/* com sufixo -free sao comprovadamente gratuitos (V1.0.4)
        identificador_lower = str(modelo_identificador).lower()
        is_free_opencode = (identificador_lower.startswith('opencode/') and
                            identificador_lower.endswith('-free'))
        if (modelo_encontrado and modelo_encontrado.get("gratuito", False)) or is_free_opencode:
            custo_estimado = 0.0
            gratuito = True"""
if new not in c:
    c = c.replace(old, new, 1)
    p.write_text(c, encoding='utf-8')
    print('[FIX 7] modelos opencode free no cost_controller')

# 8. test harness: registrar falhas e erros tambem
p = root / 'tests/test_scenarios_v104.py'
c = p.read_text(encoding='utf-8')
old = """if __name__ == '__main__':
    unittest.main(exit=False, verbosity=1)
    resumo = salvar_resultados()"""
new = """if __name__ == '__main__':
    resultado = unittest.main(exit=False, verbosity=1).result
    # Registrar testes que falharam/erraram mas nao chamaram registrar_resultado
    registrados = {r['numero'] for r in RESULTADOS}
    mapeamento = {}
    for cls in [TestCenarios01a20, TestCenarios21a40, TestCenarios41a70]:
        for nome in dir(cls):
            if nome.startswith('test_'):
                try:
                    num = int(nome.split('_')[1])
                    mapeamento[nome] = num
                except (ValueError, IndexError):
                    pass
    for teste in resultado.failures + resultado.errors:
        nome = teste[0]._testMethodName
        num = mapeamento.get(nome)
        if num and num not in registrados:
            registrar_resultado(num, nome, 'LOCAL_REAL', 'REPROVADO',
                                teste[1][-200:])
    resumo = salvar_resultados()"""
if new not in c:
    c = c.replace(old, new, 1)
    p.write_text(c, encoding='utf-8')
    print('[FIX 8] registro de falhas no harness')

print('Correcoes de falhas concluidas.')

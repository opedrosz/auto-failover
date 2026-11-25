from test_scenarios_v104 import CenariosBase

from model_selector import ModelSelector
from provider_registry import ProviderRegistry, normalizar_contexto
from supervisor import Supervisor


class FailoverV106(CenariosBase):
    def setUp(self):
        super().setUp()
        self.registry = ProviderRegistry(self.base)
        self.registry.provedores = {
            name: {"privado": True, "status": "conectado",
                   "contexto_maximo": "128K tokens (sintetico)", "programacao": "forte"}
            for name in ("a", "b")
        }
        self.registry.modelos = {
            name: [{"nome": name, "identificador": name, "gratuito": True}]
            for name in ("a", "b")
        }
        self.selector = ModelSelector(self.base, self.registry)

    def test_requisitos_padrao(self):
        result = self.selector.selecionar_modelo("sintetica")
        self.assertTrue(result["sucesso"], result)
        self.assertEqual(result["provedor_selecionado"], "a")
        self.assertEqual(result["modelo_selecionado"]["identificador"], "a")

    def test_contexto_variavel_bloqueado(self):
        for provider in self.registry.provedores.values():
            provider["contexto_maximo"] = "variável (configurável)"
        result = self.selector.selecionar_modelo("sintetica")
        self.assertEqual(result["motivo"], "nenhum_provedor_compativel")
        self.assertEqual(set(result["rejeicoes"]), {"a", "b"})

    def test_failover_continua_em_outro_processo(self):
        import sys

        supervisor = Supervisor(self.base)
        progress = self.base / "calculadora.py"

        def command(selection):
            if selection["provedor_selecionado"] == "a":
                script = "from pathlib import Path; Path('calculadora.py').write_text('def soma(a,b): return a+b\\n'); raise SystemExit(75)"
            else:
                script = "from pathlib import Path; p=Path('calculadora.py'); p.write_text(p.read_text()+'def sub(a,b): return a-b\\n')"
            return [sys.executable, "-c", script]

        def validate():
            import runpy

            namespace = runpy.run_path(str(progress))
            return namespace["soma"](2, 3) == 5 and namespace["sub"](5, 3) == 2

        result = supervisor.supervisionar_failover(
            "calculadora", self.selector, command, validate, cwd=self.base,
            capturar_progresso=lambda: {"artefato": progress.name}
        )
        self.assertEqual(result["status"], "concluido")
        self.assertEqual([item["provedor"] for item in result["tentativas"]], ["a", "b"])
        self.assertEqual(result["tentativas"][0]["returncode"], 75)
        self.assertNotEqual(result["tentativas"][0]["pid"], result["tentativas"][1]["pid"])
        self.assertFalse(supervisor.get_estado()["processo_ativo"])
        reloaded = Supervisor(self.base)
        saved = reloaded.state["tarefas"]["calculadora"]
        self.assertEqual(saved["status"], "concluido")
        self.assertEqual(saved["tentativas"][0]["checkpoint"], {"artefato": progress.name})

    def test_formatos_de_contexto(self):
        for raw, expected in [
            (128000, 128000), ("128000", 128000), ("128K", 128000),
            ("128K tokens", 128000), ("128K tokens (exemplo)", 128000),
            ("1M", 1000000), ("1.5M", 1500000), ("variável", None),
            ("variável (configurável)", None), ("desconhecido", None),
            (None, None), ("", None), (-1, None), ("-1K", None),
            ("1..5M", None), (True, None),
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(normalizar_contexto(raw)["janela_total"], expected)
        self.assertEqual(normalizar_contexto("variável (configurável)")["estado"], "variavel")
        self.assertTrue(normalizar_contexto("variável (configurável)")["configuravel"])

    def test_limites_compartilhados_e_modelos_distintos(self):
        self.registry.modelos["a"][0]["contexto"] = {
            "janela_total": 100, "entrada": 90, "saida": 30,
        }
        self.registry.modelos["b"][0]["contexto"] = {
            "janela_total": 200, "entrada": 90, "saida": 30,
        }
        result = self.selector.selecionar_modelo("sintetica", {"tokens_entrada": 90, "tokens_saida": 30})
        self.assertEqual(result["provedor_selecionado"], "b")
        self.assertIn("Janela total insuficiente", result["rejeicoes"]["a"]["a"][0])
        blocked = self.selector.selecionar_modelo(
            "sintetica", {"tokens_entrada": 90, "tokens_saida": 30}, exclude_provedores={"b"}
        )
        self.assertFalse(blocked["sucesso"])

    def test_exclusao_de_modelo_cota_e_circuito(self):
        self.registry.modelos["a"].append({"identificador": "a2", "gratuito": True})
        result = self.selector.selecionar_modelo("sintetica", excluir_modelos={("a", "a")})
        self.assertEqual(result["modelo_selecionado"]["identificador"], "a2")
        self.registry.provedores["a"]["grupo_cota"] = "compartilhado"
        result = self.selector.selecionar_modelo(
            "sintetica", grupos_excluidos={"compartilhado"}, pode_executar=lambda alias: alias != "b"
        )
        self.assertFalse(result["sucesso"])
        self.assertEqual(result["rejeicoes"]["a"]["a"], ["cota indisponivel"])
        self.assertIn("circuito aberto", result["rejeicoes"]["b"]["*"][0])

    def test_falha_incerta_nao_dispara_segundo_processo(self):
        import sys

        calls = []

        def command(selection):
            calls.append(selection["provedor_selecionado"])
            return [sys.executable, "-c", "raise SystemExit(1)"]

        supervisor = Supervisor(self.base)
        result = supervisor.supervisionar_failover(
            "incerta", self.selector, command, lambda: self.fail("nao concluiu"), cwd=self.base
        )
        self.assertEqual(result["motivo"], "falha_requer_reconciliacao")
        self.assertEqual(calls, ["a"])
        self.assertFalse(supervisor.get_estado()["processo_ativo"])

    def test_lock_impede_sobreposicao(self):
        path = self.base / ".auto-failover.lock"
        path.write_text("synthetic-owner", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            Supervisor(self.base).supervisionar_failover(
                "lock", self.selector, lambda _: self.fail("processo nao pode iniciar"),
                lambda: False, cwd=self.base,
            )
        self.assertEqual(path.read_text(encoding="utf-8"), "synthetic-owner")

    def test_custo_remoto_nao_verificado(self):
        self.registry.provedores["a"]["privado"] = False
        self.registry.modelos["a"][0]["gratuito"] = True
        result = self.selector.selecionar_modelo("sintetica", {})
        self.assertEqual(result["provedor_selecionado"], "b")
        self.assertIn("custo remoto nao verificado", result["rejeicoes"]["a"]["a"])

    def test_cancelamento_entre_tentativas_impede_novo_filho(self):
        import sys
        from stop_controller import StopController

        calls = []
        stop = StopController(self.base)

        def command(selection):
            calls.append(selection["provedor_selecionado"])
            return [sys.executable, "-c", "raise SystemExit(75)"]

        def checkpoint():
            stop.cancelar("tarefa", "teste", salvar_checkpoint=False)
            return {"artefato": "sintetico"}

        result = Supervisor(self.base).supervisionar_failover(
            "tarefa", self.selector, command, lambda: self.fail("nao concluiu"), cwd=self.base,
            capturar_progresso=checkpoint,
            controle_interrupcao=lambda task_id: stop.verificar_tarefa(task_id)["status"] == "cancelado",
        )
        self.assertEqual(result["motivo"], "interrupcao_solicitada")
        self.assertEqual(calls, ["a"])

    def test_workspace_bloqueia_escape_de_caminho(self):
        from security_controller import SecurityController
        from types import SimpleNamespace

        workspace = self.base / "projeto"
        workspace.mkdir()
        manager = SimpleNamespace(config={"projetos": {"p": {"caminho_base": str(workspace)}}})
        security = SecurityController(self.base, project_manager=manager)
        outside = security.validar_acao({"tipo": "escrita", "caminho_arquivo": "../fora.py"}, {"projeto_id": "p"})
        self.assertFalse(outside["autorizada"])
        self.assertIn("escrita_fora_projeto", outside["restricoes"])
        inside = security.validar_acao({"tipo": "escrita", "caminho_arquivo": "dentro.py"}, {"projeto_id": "p"})
        self.assertTrue(inside["autorizada"])

    def test_demo_e_templates_em_processo_novo(self):
        import json
        from pathlib import Path
        import subprocess
        import sys

        root = Path(__file__).resolve().parents[1]
        process = subprocess.run(
            [sys.executable, str(root / "cli.py"), "demo-local"], cwd=self.base,
            capture_output=True, text=True, timeout=30, check=True,
        )
        result = json.loads(process.stdout)
        self.assertEqual(result["status"], "concluido")
        self.assertEqual(result["inferencias_reais"], 0)
        first, second = result["tentativas"]
        self.assertNotEqual(first["provedor"], second["provedor"])
        self.assertEqual(first["checkpoint"]["artefato"], "calc.py")
        self.assertEqual(second["returncode"], 0)

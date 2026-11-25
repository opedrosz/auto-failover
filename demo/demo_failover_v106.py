"""Demonstração local com dois provedores simulados e processos Python reais."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
for module in ("Model Selector", "provider_registry", "supervisor"):
    sys.path.insert(0, str(ROOT / module))


def executar(base):
    from model_selector import ModelSelector
    from provider_registry import ProviderRegistry
    from supervisor import Supervisor

    templates = ROOT / "examples"
    (base / "config").mkdir(exist_ok=True)
    (base / "data").mkdir(exist_ok=True)
    shutil.copyfile(templates / "model_selector_config.example.json", base / "config/model_selector_config.json")
    shutil.copyfile(templates / "provider_registry.example.json", base / "data/provider_registry.json")
    registry = ProviderRegistry(base)
    workers = {
        "sintetico-a": ("from pathlib import Path; "
                        "Path('calc.py').write_text('def soma(a, b): return a + b\\n'); "
                        "raise SystemExit(75)"),
        "sintetico-b": ("from pathlib import Path; p = Path('calc.py'); "
                        "p.write_text(p.read_text() + 'def sub(a, b): return a - b\\n')"),
    }

    def comando(selecao):
        return [sys.executable, "-I", "-c", workers[selecao["provedor_selecionado"]]]

    def validar():
        return subprocess.run(
            [sys.executable, "-c", "from calc import soma, sub; "
             "assert soma(2, 3) == 5 and sub(5, 3) == 2"],
            cwd=base, timeout=15, check=False,
        ).returncode == 0

    def capturar_progresso():
        return {"artefato": "calc.py", "sha256": hashlib.sha256(
            (base / "calc.py").read_bytes()
        ).hexdigest()}

    resultado = Supervisor(base).supervisionar_failover(
        "calculadora", ModelSelector(base, registry), comando, validar, cwd=base,
        capturar_progresso=capturar_progresso,
    )
    return {**resultado, "inferencias_reais": 0, "custo_adicional_brl": 0}


if __name__ == "__main__":
    with TemporaryDirectory(prefix="auto-failover-sintetico-") as temp:
        os.environ["AUTO_FAILOVER_BASE"] = temp
        result = executar(Path(temp))
        print(json.dumps(result, indent=2))
        sys.exit(result["status"] != "concluido")

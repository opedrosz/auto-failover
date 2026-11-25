#!/usr/bin/env python3
"""Parse das respostas reais para extrair texto final e uso."""
import json
from pathlib import Path

# Executar uma chamada de confirmacao com saida completa
import subprocess

prompt = "Responda EXATAMENTE com a palavra OK e nada mais."
r = subprocess.run(
    ['opencode', 'run', '--model', 'opencode/hy4-flash-free', '--format', 'json', '--auto', prompt],
    capture_output=True, text=True, timeout=120,
)
textos = []
for linha in r.stdout.splitlines():
    try:
        obj = json.loads(linha)
        if obj.get('type') == 'text':
            part = obj.get('part', {})
            txt = part.get('text', '')
            if txt:
                textos.append(txt)
    except json.JSONDecodeError:
        continue

print("Texto extraido:", repr(''.join(textos)))
print("Returncode:", r.returncode)
print("Total linhas de evento:", len(r.stdout.splitlines()))

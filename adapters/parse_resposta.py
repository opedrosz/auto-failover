#!/usr/bin/env python3
"""Extrai texto de eventos JSON do OpenCode recebidos pela entrada padrão."""
import json
import sys


def extrair_texto(linhas):
    partes = []
    for linha in linhas:
        try:
            evento = json.loads(linha)
        except json.JSONDecodeError:
            continue
        if isinstance(evento, dict) and evento.get("type") == "text":
            texto = evento.get("part", {}).get("text")
            if isinstance(texto, str):
                partes.append(texto)
    return "".join(partes)


if __name__ == "__main__":
    print(extrair_texto(sys.stdin))

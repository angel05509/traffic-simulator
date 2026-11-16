"""Historial de corridas (JSON) y utilidades de archivos."""
import json
import os
import subprocess
import sys

from .config import ARCHIVO_JSON


def cargar_historial():
    try:
        with open(ARCHIVO_JSON, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return [r for r in datos if isinstance(r, dict) and "serie" in r] if isinstance(datos, list) else []
    except (OSError, ValueError):
        return []


def guardar_historial(datos):
    try:
        with open(ARCHIVO_JSON, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
    except OSError:
        pass


def abrir_carpeta(ruta):
    os.makedirs(ruta, exist_ok=True)
    try:
        if sys.platform.startswith("win"):
            os.startfile(ruta)  # noqa
        elif sys.platform == "darwin":
            subprocess.Popen(["open", ruta])
        else:
            subprocess.Popen(["xdg-open", ruta])
    except Exception:
        pass

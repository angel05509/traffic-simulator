"""Escenario estático (fondo, trayectorias, HUD, velo): se construye una sola vez."""
import pygame

from .config import *
from .geometria import RUTAS


_REC = {}


def recurso_fondo():
    if "fondo" not in _REC:
        f = pygame.Surface((ANCHO_V, ALTO_V))
        f.fill(GRAMA)
        for x in range(20, ANCHO_V, 90):
            for y in range(18, ALTO_V, 85):
                pygame.draw.circle(f, (38, 64, 52), (x + (y % 17), y), 2)
        pygame.draw.rect(f, BORDE, (0, Y_ARRIBA - 4, ANCHO_V, ANCHO_CALLE + 8))
        pygame.draw.rect(f, BORDE, (X_IZQ - 4, 0, ANCHO_CALLE + 8, ALTO_V))
        pygame.draw.rect(f, CALLE, (0, Y_ARRIBA, ANCHO_V, ANCHO_CALLE))
        pygame.draw.rect(f, CALLE, (X_IZQ, 0, ANCHO_CALLE, ALTO_V))
        for x in range(0, ANCHO_V, 38):
            if not X_IZQ - 5 <= x <= X_DER:
                pygame.draw.line(f, LINEA, (x, CENTRO_Y), (x + 20, CENTRO_Y), 2)
        for y in range(0, ALTO_V, 38):
            if not Y_ARRIBA - 5 <= y <= Y_ABAJO:
                pygame.draw.line(f, LINEA, (CENTRO_X, y), (CENTRO_X, y + 20), 2)
        cebra = (185, 187, 182)
        for i in range(7):
            xx = X_IZQ + 8 + i * 23
            pygame.draw.rect(f, cebra, (xx, Y_ARRIBA - 19, 13, 13))
            pygame.draw.rect(f, cebra, (xx, Y_ABAJO + 6, 13, 13))
            yy = Y_ARRIBA + 8 + i * 23
            pygame.draw.rect(f, cebra, (X_IZQ - 19, yy, 13, 13))
            pygame.draw.rect(f, cebra, (X_DER + 6, yy, 13, 13))
        pygame.draw.rect(f, BLANCO, (X_IZQ - DIST_PARADA, CENTRO_Y + 3, 4, MITAD - 3))
        pygame.draw.rect(f, BLANCO, (X_DER + DIST_PARADA - 4, Y_ARRIBA, 4, MITAD - 3))
        pygame.draw.rect(f, BLANCO, (X_IZQ, Y_ARRIBA - DIST_PARADA, MITAD - 3, 4))
        pygame.draw.rect(f, BLANCO, (CENTRO_X + 3, Y_ABAJO + DIST_PARADA - 4, MITAD - 3, 4))
        _REC["fondo"] = f
    return _REC["fondo"]


def recurso_rutas():
    if "rutas" not in _REC:
        ov = pygame.Surface((ANCHO_V, ALTO_V), pygame.SRCALPHA)
        for r in RUTAS.values():
            pts, s = [], r.s_linea - 35
            while s <= r.s_salida + 35:
                pts.append(r.punto(s))
                s += 5
            pygame.draw.lines(ov, COLOR_GIRO[r.giro] + (140,), False, pts, 2)
        _REC["rutas"] = ov
    return _REC["rutas"]


def recurso_hud():
    if "hud" not in _REC:
        s = pygame.Surface((ANCHO_V, 48), pygame.SRCALPHA)
        s.fill((13, 17, 20, 215))
        _REC["hud"] = s
    return _REC["hud"]


def recurso_velo():
    if "velo" not in _REC:
        s = pygame.Surface((ANCHO_V, ALTO_V), pygame.SRCALPHA)
        s.fill((10, 14, 18, 185))
        _REC["velo"] = s
    return _REC["velo"]

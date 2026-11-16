"""Sprites de coche: se dibujan una vez y se rotan con caché."""
import pygame

from .config import ANCHO, LARGO


_BASES = {}
_ROTADOS = {}


def _construir_base(color):
    S = 3
    w, h = LARGO * S, ANCHO * S
    base = pygame.Surface((w, h), pygame.SRCALPHA)
    oscuro = tuple(max(0, c - 45) for c in color)
    claro = tuple(min(255, c + 28) for c in color)
    pygame.draw.rect(base, oscuro, (0, 0, w, h), border_radius=16)
    pygame.draw.rect(base, color, (3, 3, w - 6, h - 6), border_radius=14)
    pygame.draw.rect(base, (28, 43, 54), (int(w * 0.60), 8, int(w * 0.15), h - 16), border_radius=7)
    pygame.draw.rect(base, (28, 43, 54), (int(w * 0.20), 9, int(w * 0.12), h - 18), border_radius=6)
    pygame.draw.rect(base, claro, (int(w * 0.33), 8, int(w * 0.26), h - 16), border_radius=6)
    pygame.draw.line(base, (112, 145, 158), (int(w * 0.62), 14), (int(w * 0.72), h - 14), 2)
    for yy in (0.2, 0.8):
        pygame.draw.ellipse(base, (255, 244, 190), (int(w * 0.92), int(h * yy) - 6, 14, 12))
        pygame.draw.ellipse(base, (150, 25, 30), (int(w * 0.03), int(h * yy) - 6, 12, 12))
    cuerpo = pygame.transform.smoothscale(base, (LARGO, ANCHO))
    sombra = pygame.Surface((LARGO, ANCHO), pygame.SRCALPHA)
    pygame.draw.rect(sombra, (0, 0, 0, 95), (0, 0, LARGO, ANCHO), border_radius=6)
    return cuerpo, sombra


def sprite_coche(color, grados):
    clave = (color, grados)
    par = _ROTADOS.get(clave)
    if par is None:
        base = _BASES.get(color)
        if base is None:
            base = _BASES[color] = _construir_base(color)
        par = _ROTADOS[clave] = (pygame.transform.rotate(base[0], grados),
                                 pygame.transform.rotate(base[1], grados))
    return par

"""Ventana, fuentes, ratón, botones y escalado del lienzo virtual."""
import pygame

from .config import *


pygame.init()
pygame.display.set_caption(TITULO)
PANTALLA_REAL = pygame.display.set_mode((ANCHO_V, ALTO_V), pygame.RESIZABLE | pygame.DOUBLEBUF)
CANVAS = pygame.Surface((ANCHO_V, ALTO_V))
RELOJ = pygame.time.Clock()

_FAM = "segoeui,arial,dejavusans,helvetica"
F_TITULO = pygame.font.SysFont(_FAM, 38, bold=True)
F_SUB = pygame.font.SysFont(_FAM, 20)
F_BTN = pygame.font.SysFont(_FAM, 24, bold=True)
F_BTN_S = pygame.font.SysFont(_FAM, 18, bold=True)
F_TXT = pygame.font.SysFont(_FAM, 18)
F_PEQ = pygame.font.SysFont(_FAM, 15)
F_HUD = pygame.font.SysFont(_FAM, 17, bold=True)
F_KPI = pygame.font.SysFont(_FAM, 22, bold=True)
F_SEC = pygame.font.SysFont(_FAM, 28, bold=True)


# Ratón en coordenadas del lienzo virtual (la ventana puede estar escalada)
VISTA = {"esc": 1.0, "ox": 0, "oy": 0}


def raton(pos=None):
    x, y = pos if pos is not None else pygame.mouse.get_pos()
    return int((x - VISTA["ox"]) / VISTA["esc"]), int((y - VISTA["oy"]) / VISTA["esc"])


def texto(sup, msg, fuente, color, pos, centro=False, derecha=False):
    img = fuente.render(msg, True, color)
    r = img.get_rect()
    if centro:
        r.center = pos
    elif derecha:
        r.topright = pos
    else:
        r.topleft = pos
    sup.blit(img, r)
    return r


class Boton:
    def __init__(self, rect, etiqueta, color=ACENTO, fuente=None):
        self.rect = pygame.Rect(rect)
        self.etiqueta = etiqueta
        self.color = color
        self.fuente = fuente or F_BTN
        self.habilitado = True

    def dibujar(self, sup):
        if not self.habilitado:
            pygame.draw.rect(sup, (44, 50, 56), self.rect, border_radius=10)
            texto(sup, self.etiqueta, self.fuente, (105, 112, 116), self.rect.center, centro=True)
            return
        encima = self.rect.collidepoint(raton())
        col = tuple(min(255, c + 35) for c in self.color) if encima else self.color
        pygame.draw.rect(sup, col, self.rect, border_radius=10)
        texto(sup, self.etiqueta, self.fuente, (255, 255, 255), self.rect.center, centro=True)

    def clic(self, ev):
        return (self.habilitado and ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
                and self.rect.collidepoint(raton(ev.pos)))


def tarjeta(sup, x, y, w, h, etiqueta, valor, color=BLANCO):
    pygame.draw.rect(sup, PANEL, (x, y, w, h), border_radius=10)
    texto(sup, etiqueta, F_PEQ, GRIS, (x + 12, y + 6))
    texto(sup, valor, F_KPI, color, (x + 12, y + 25))


_ESC = {"surf": None}


def presentar():
    aw, ah = PANTALLA_REAL.get_size()
    esc = min(aw / ANCHO_V, ah / ALTO_V)
    w, h = max(1, int(ANCHO_V * esc)), max(1, int(ALTO_V * esc))
    ox, oy = (aw - w) // 2, (ah - h) // 2
    VISTA.update(esc=w / ANCHO_V, ox=ox, oy=oy)
    PANTALLA_REAL.fill((10, 12, 14))
    if (w, h) == (ANCHO_V, ALTO_V):
        PANTALLA_REAL.blit(CANVAS, (ox, oy))
    else:
        if _ESC["surf"] is None or _ESC["surf"].get_size() != (w, h):
            _ESC["surf"] = pygame.Surface((w, h))
        pygame.transform.smoothscale(CANVAS, (w, h), _ESC["surf"])
        PANTALLA_REAL.blit(_ESC["surf"], (ox, oy))
    pygame.display.flip()

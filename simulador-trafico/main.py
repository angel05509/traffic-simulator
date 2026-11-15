"""
Simulador de Tráfico - Fase 6 (Menú de inicio + Gráficas + Reportes PDF)
=========================================================================
Intersección con semáforo, giros fluidos (Bézier), cruce sin choques y ahora:

  * VENTANA DE INICIO   Iniciar simulación, nivel de tráfico, duración,
                        ver gráficas y salir (con una simulación de fondo).
  * VENTANA DE GRÁFICAS Análisis de cada corrida: cruces por intervalo, colas
                        por acceso, espera promedio, maniobras, velocidad,
                        comparativa entre corridas. Navega entre corridas.
  * REPORTES PDF        Al terminar cada corrida se guarda automáticamente un
                        PDF (2 páginas) en la carpeta  reportes/  con la fecha
                        y la hora en el nombre:  reporte_2026-11-15_10-35-12.pdf
  * HISTORIAL           Todas las corridas (con sus series) quedan en
                        historial_simulaciones.json.

Controles en la simulación
  ESPACIO pausa | +/- velocidad | T trayectorias | E estelas
  F terminar ahora y ver gráficas | ESC cancelar | F11 pantalla completa

Controles en gráficas
  Clic en los botones, o  ←/→ cambiar de corrida | TAB cambiar de vista | G guardar PDF

Requisitos:  pip install pygame matplotlib
"""

import json
import math
import os
import random
import subprocess
import sys
import textwrap
from bisect import bisect_right
from collections import deque
from datetime import datetime

import pygame

try:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.figure import Figure
    from matplotlib.patches import Patch, Rectangle
    HAY_MPL = True
except ImportError:  # el simulador funciona, pero sin gráficas ni PDF
    HAY_MPL = False

# ──────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────
TITULO = "Simulador de Tráfico - Fase 6"
ANCHO_V, ALTO_V = 1000, 700          # lienzo virtual (se escala a la ventana)
FPS = 120

BASE = os.path.dirname(os.path.abspath(__file__))
CARPETA_PDF = os.path.join(BASE, "reportes")
ARCHIVO_JSON = os.path.join(BASE, "historial_simulaciones.json")

CENTRO_X, CENTRO_Y = ANCHO_V // 2, ALTO_V // 2
ANCHO_CALLE = 180
MITAD = ANCHO_CALLE // 2
CARRIL = 43
DIST_PARADA = 26
MARGEN_FUERA = 70
X_IZQ, X_DER = CENTRO_X - MITAD, CENTRO_X + MITAD
Y_ARRIBA, Y_ABAJO = CENTRO_Y - MITAD, CENTRO_Y + MITAD
LARGO, ANCHO = 42, 23

A_ACEL = 160.0
A_COMODO = 190.0
A_FRENO = 340.0
UMBRAL_CONFLICTO = 40.0
KMH = 0.36                       # 1 px ≈ 0.1 m  →  px/s * 0.36 = km/h

# (nombre, segundos entre coches generados en total)
NIVELES = [("Bajo", 2.2), ("Medio", 1.1), ("Alto", 0.6)]
DURACIONES = [60, 120, 180]      # segundos simulados por corrida
ESCALAS = [0.5, 1.0, 2.0, 4.0, 8.0]

# ──────────────────────────────────────────────
# Pygame y recursos
# ──────────────────────────────────────────────
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

# Paleta
GRAMA = (33, 57, 48)
CALLE = (53, 57, 62)
BORDE = (115, 120, 123)
LINEA = (205, 203, 176)
BLANCO = (242, 242, 235)
GRIS = (160, 168, 172)
AMARILLO = (255, 197, 61)
ROJO = (255, 75, 75)
VERDE = (65, 220, 120)
APAGADO = (62, 65, 67)
FONDO = (18, 24, 28)
PANEL = (30, 38, 44)
ACENTO = (70, 160, 255)

COLORES_H = [(65, 190, 245), (70, 220, 190), (95, 145, 255), (220, 225, 235)]
COLORES_V = [(255, 155, 65), (245, 95, 105), (205, 125, 245), (245, 210, 85)]
COLOR_GIRO = {"FRENTE": (120, 170, 230), "DERECHA": (90, 230, 150), "IZQUIERDA": (255, 190, 80)}

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


# ──────────────────────────────────────────────
# Rutas (entrada → cruce → salida) como polilíneas con curvas Bézier
# ──────────────────────────────────────────────
ORIGENES = ("OESTE", "ESTE", "NORTE", "SUR")
GIROS = ("FRENTE", "DERECHA", "IZQUIERDA")
DIRS = {"OESTE": (1, 0), "ESTE": (-1, 0), "NORTE": (0, 1), "SUR": (0, -1)}
ETIQ = {"OESTE": "Oeste", "ESTE": "Este", "NORTE": "Norte", "SUR": "Sur",
        "FRENTE": "Frente", "DERECHA": "Derecha", "IZQUIERDA": "Izquierda"}


def girar(d, giro):
    dx, dy = d
    if giro == "DERECHA":
        return (-dy, dx)
    if giro == "IZQUIERDA":
        return (dy, -dx)
    return d


class Ruta:
    PASOS_CURVA = 40

    def __init__(self, origen, giro):
        self.origen, self.giro = origen, giro
        d = DIRS[origen]
        d2 = girar(d, giro)
        self.dir_entrada, self.dir_salida = d, d2
        self.eje = "H" if d[0] != 0 else "V"

        rv = (-d[1], d[0])
        rv2 = (-d2[1], d2[0])
        ext = ANCHO_V // 2 if d[0] != 0 else ALTO_V // 2
        ext2 = ANCHO_V // 2 if d2[0] != 0 else ALTO_V // 2

        inicio = (CENTRO_X + rv[0] * CARRIL - d[0] * (ext + MARGEN_FUERA),
                  CENTRO_Y + rv[1] * CARRIL - d[1] * (ext + MARGEN_FUERA))
        p_in = (CENTRO_X + rv[0] * CARRIL - d[0] * MITAD, CENTRO_Y + rv[1] * CARRIL - d[1] * MITAD)
        p_out = (CENTRO_X + rv2[0] * CARRIL + d2[0] * MITAD, CENTRO_Y + rv2[1] * CARRIL + d2[1] * MITAD)
        fin = (CENTRO_X + rv2[0] * CARRIL + d2[0] * (ext2 + MARGEN_FUERA),
               CENTRO_Y + rv2[1] * CARRIL + d2[1] * (ext2 + MARGEN_FUERA))

        pts = [inicio, p_in]
        if giro != "FRENTE":
            c = (p_out[0], p_in[1]) if d[0] != 0 else (p_in[0], p_out[1])
            n = self.PASOS_CURVA
            for i in range(1, n):
                t = i / n
                u = 1 - t
                pts.append((u * u * p_in[0] + 2 * u * t * c[0] + t * t * p_out[0],
                            u * u * p_in[1] + 2 * u * t * c[1] + t * t * p_out[1]))
        pts += [p_out, fin]

        self.pts = pts
        self.acum = [0.0]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            self.acum.append(self.acum[-1] + math.hypot(x1 - x0, y1 - y0))
        self.largo = self.acum[-1]
        self.s_linea = self.acum[1]
        self.s_parada = self.s_linea - DIST_PARADA
        self.s_salida = self.acum[-2]
        self.s_fin_cruce = self.s_salida + 40
        self.p_salida = p_out

    def punto(self, s):
        s = 0.0 if s < 0 else self.largo if s > self.largo else s
        i = bisect_right(self.acum, s) - 1
        i = min(max(i, 0), len(self.pts) - 2)
        seg = self.acum[i + 1] - self.acum[i]
        t = (s - self.acum[i]) / seg if seg > 0 else 0.0
        x0, y0 = self.pts[i]
        x1, y1 = self.pts[i + 1]
        return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t

    def muestra(self, s):
        x, y = self.punto(s)
        xa, ya = self.punto(s + 7)
        xb, yb = self.punto(s - 7)
        hx, hy = xa - xb, ya - yb
        n = math.hypot(hx, hy)
        if n < 1e-6:
            return x, y, float(self.dir_entrada[0]), float(self.dir_entrada[1])
        return x, y, hx / n, hy / n


RUTAS = {(o, g): Ruta(o, g) for o in ORIGENES for g in GIROS}
_CONFLICTOS = {}


def en_conflicto(ra, rb):
    clave = (ra.origen, ra.giro, rb.origen, rb.giro)
    res = _CONFLICTOS.get(clave)
    if res is None:
        def muestras(r):
            lst, s = [], r.s_linea - 10
            while s <= r.s_salida + 30:
                lst.append(r.punto(s))
                s += 6
            return lst
        a, b = muestras(ra), muestras(rb)
        u2 = UMBRAL_CONFLICTO ** 2
        res = any((ax - bx) ** 2 + (ay - by) ** 2 < u2 for ax, ay in a for bx, by in b)
        _CONFLICTOS[clave] = res
    return res


# ──────────────────────────────────────────────
# Sprites de coche (se dibujan una vez y se rotan con caché)
# ──────────────────────────────────────────────
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


# ──────────────────────────────────────────────
# Semáforo
# ──────────────────────────────────────────────
class Semaforo:
    ORDEN = ["H_VERDE", "H_AMARILLO", "H_TODO_ROJO", "V_VERDE", "V_AMARILLO", "V_TODO_ROJO"]

    def __init__(self, verde=10.0, amarillo=2.5, todo_rojo=1.2):
        self.verde, self.amarillo, self.todo_rojo = verde, amarillo, todo_rojo
        self.estado = "H_VERDE"
        self.t = 0.0

    def _duracion(self):
        if self.estado.endswith("VERDE"):
            return self.verde
        if self.estado.endswith("AMARILLO"):
            return self.amarillo
        return self.todo_rojo

    def actualizar(self, dt):
        self.t += dt
        while self.t >= self._duracion():
            self.t -= self._duracion()
            self.estado = self.ORDEN[(self.ORDEN.index(self.estado) + 1) % len(self.ORDEN)]

    def restante(self):
        return max(0.0, self._duracion() - self.t)

    def luz(self, eje):
        if self.estado.startswith(eje + "_"):
            if self.estado.endswith("VERDE"):
                return "VERDE"
            if self.estado.endswith("AMARILLO"):
                return "AMARILLO"
        return "ROJO"

    def descripcion(self):
        nombres = {"H_VERDE": "H VERDE", "H_AMARILLO": "H AMARILLO", "V_VERDE": "V VERDE",
                   "V_AMARILLO": "V AMARILLO", "H_TODO_ROJO": "TODO ROJO", "V_TODO_ROJO": "TODO ROJO"}
        return f"{nombres[self.estado]} {self.restante():.0f}s"

    def color(self):
        if self.estado.endswith("VERDE"):
            return VERDE
        if self.estado.endswith("AMARILLO"):
            return AMARILLO
        return ROJO

    def dibujar(self, sup):
        posiciones = [
            (X_IZQ - 42, Y_ABAJO + 8, "H"), (X_DER + 18, Y_ARRIBA - 57, "H"),
            (X_IZQ - 42, Y_ARRIBA - 57, "V"), (X_DER + 18, Y_ABAJO + 8, "V"),
        ]
        colores = {"ROJO": ROJO, "AMARILLO": AMARILLO, "VERDE": VERDE}
        for x, y, eje in posiciones:
            pygame.draw.rect(sup, (17, 19, 21), (x, y, 25, 62), border_radius=7)
            activa = self.luz(eje)
            for i, nombre in enumerate(("ROJO", "AMARILLO", "VERDE")):
                cx, cy = x + 12, y + 11 + i * 20
                if activa == nombre:
                    c = colores[nombre]
                    pygame.draw.circle(sup, tuple(int(v * 0.35 + 17 * 0.65) for v in c), (cx, cy), 10)
                    pygame.draw.circle(sup, c, (cx, cy), 7)
                else:
                    pygame.draw.circle(sup, APAGADO, (cx, cy), 7)


# ──────────────────────────────────────────────
# Vehículo
# ──────────────────────────────────────────────
class Vehiculo:
    def __init__(self, origen, s=0.0):
        self.origen = origen
        self.giro = random.choices(GIROS, [0.60, 0.20, 0.20])[0]
        self.ruta = RUTAS[(origen, self.giro)]
        self.s = s
        self.v_crucero = random.uniform(105, 140)
        self.v_giro = random.uniform(60, 78)
        self.vel = self.v_crucero
        self.color = random.choice(COLORES_H if self.ruta.eje == "H" else COLORES_V)
        self.autorizado = False
        self.cruzo = False
        self.t_espera = 0.0      # tiempo bloqueado por conflicto (prioridad)
        self.espera = 0.0        # tiempo total detenido antes de cruzar (estadística)
        self.frenando = False
        self.tick = random.random() * 2
        self.estela = deque(maxlen=45)
        self._cuenta = 0
        self._ult_estela = None
        self._pose()

    def _pose(self):
        self.x, self.y, self.hx, self.hy = self.ruta.muestra(self.s)

    def _buscar_lider(self, sim):
        r = self.ruta
        muestras = [(k, *r.punto(self.s + k)) for k in range(16, 126, 10)]
        mejor = None
        for o in sim.vehiculos:
            if o is self:
                continue
            dx, dy = o.x - self.x, o.y - self.y
            if dx * dx + dy * dy > 170 * 170:
                continue
            if o.hx * self.hx + o.hy * self.hy < 0.35:
                continue
            for k, qx, qy in muestras:
                ex, ey = o.x - qx, o.y - qy
                if ex * ex + ey * ey < 22 * 22:
                    gap = k + ex * self.hx + ey * self.hy - LARGO
                    if mejor is None or gap < mejor[0]:
                        mejor = (gap, o)
                    break
        return mejor

    def _salida_bloqueada(self, sim):
        px, py = self.ruta.p_salida
        d2x, d2y = self.ruta.dir_salida
        for o in sim.vehiculos:
            if o is self:
                continue
            rx, ry = o.x - px, o.y - py
            f = rx * d2x + ry * d2y
            lat = abs(-rx * d2y + ry * d2x)
            if -10 < f < 95 and lat < 26 and o.vel < 30:
                return True
        return False

    def _evaluar_paso(self, sim, gap, dt):
        r = self.ruta
        luz = sim.semaforo.luz(r.eje)
        if luz == "ROJO":
            self.t_espera = 0.0
            return False
        if luz == "AMARILLO" and self.vel ** 2 / (2 * A_COMODO) <= max(0.0, gap):
            self.t_espera = 0.0
            return False
        for o in sim.vehiculos:
            if o is not self and o.origen == self.origen and not o.autorizado and o.s > self.s:
                return False
        bloqueado = self._salida_bloqueada(sim)
        if not bloqueado:
            for o in sim.vehiculos:
                if o is self or o.origen == self.origen:
                    continue
                if o.autorizado and not o.cruzo:
                    if en_conflicto(r, o.ruta):
                        bloqueado = True
                        break
                elif not o.autorizado and o.t_espera > self.t_espera + 0.05:
                    if en_conflicto(r, o.ruta):
                        bloqueado = True
                        break
        if bloqueado:
            self.t_espera += dt
            return False
        return True

    def actualizar(self, dt, sim):
        r = self.ruta
        self.tick += dt
        objetivo = self.v_crucero

        if self.giro != "FRENTE" and self.s < r.s_salida:
            d = max(0.0, r.s_linea - self.s)
            objetivo = min(objetivo, math.sqrt(self.v_giro ** 2 + 2 * A_COMODO * d))

        if not self.autorizado:
            gap = r.s_parada - 3 - LARGO / 2 - self.s
            if gap < -8:
                self.autorizado = True
            else:
                umbral = max(45.0, self.vel ** 2 / (2 * A_COMODO) + 30)
                if gap < umbral and self._evaluar_paso(sim, gap, dt):
                    self.autorizado = True
                    self.t_espera = 0.0
                if not self.autorizado:
                    objetivo = 0.0 if gap < 0.5 else min(objetivo, math.sqrt(2 * A_COMODO * gap))

        lider = self._buscar_lider(sim)
        if lider:
            gap, o = lider
            v_perm = math.sqrt(o.vel ** 2 + 2 * A_COMODO * max(0.0, gap - 10))
            if gap < 4:
                v_perm = min(v_perm, o.vel * 0.5)
            objetivo = min(objetivo, v_perm)

        if objetivo < self.vel:
            self.vel = max(objetivo, self.vel - A_FRENO * dt)
            self.frenando = True
        else:
            self.vel = min(objetivo, self.vel + A_ACEL * dt)
            self.frenando = self.vel < 4
        if self.vel < 0.5 and objetivo == 0.0:
            self.vel = 0.0

        self.s += self.vel * dt
        self._pose()

        # Estadísticas: tiempo detenido antes de cruzar y registro del cruce
        if not self.cruzo and self.vel < 5:
            self.espera += dt
        if self.autorizado and not self.cruzo and self.s > r.s_fin_cruce:
            self.cruzo = True
            sim.registrar_cruce(self)

        self._cuenta += 1
        if self.giro != "FRENTE" and r.s_linea - 25 <= self.s <= r.s_salida + 35:
            u = self._ult_estela
            if u is None or (self.x - u[0]) ** 2 + (self.y - u[1]) ** 2 > 9:
                self.estela.append((self.x, self.y))
                self._ult_estela = (self.x, self.y)
        elif self.estela and self._cuenta % 2 == 0:
            self.estela.popleft()

    def fuera_pantalla(self):
        return self.s >= self.ruta.largo

    def _grados(self):
        deg = -math.degrees(math.atan2(self.hy, self.hx))
        return int(round(deg / 3.0)) * 3 % 360

    def dibujar_sombra(self, c):
        _, sombra = sprite_coche(self.color, self._grados())
        c.blit(sombra, sombra.get_rect(center=(self.x + 3, self.y + 5)))

    def dibujar(self, c):
        cuerpo, _ = sprite_coche(self.color, self._grados())
        c.blit(cuerpo, cuerpo.get_rect(center=(self.x, self.y)))
        rvx, rvy = -self.hy, self.hx

        def mundo(f, lado):
            return (self.x + self.hx * f + rvx * lado, self.y + self.hy * f + rvy * lado)

        if self.frenando:
            for lado in (-1, 1):
                pygame.draw.circle(c, (255, 60, 60), mundo(-(LARGO / 2 - 3), lado * (ANCHO / 2 - 4)), 3)
        r = self.ruta
        if self.giro != "FRENTE" and r.s_linea - 170 <= self.s <= r.s_salida - 10 \
                and int(self.tick * 3.5) % 2 == 0:
            lado = 1 if self.giro == "DERECHA" else -1
            for f in (LARGO / 2 - 4, -(LARGO / 2 - 4)):
                p = mundo(f, lado * (ANCHO / 2 - 3))
                pygame.draw.circle(c, (130, 95, 20), p, 5)
                pygame.draw.circle(c, AMARILLO, p, 3)


# ──────────────────────────────────────────────
# Escenario estático (se construye una sola vez)
# ──────────────────────────────────────────────
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


# ──────────────────────────────────────────────
# Simulación (motor + estadísticas para las gráficas)
# ──────────────────────────────────────────────
class Simulacion:
    def __init__(self, nivel=1, duracion=60, demo=False):
        self.nombre_nivel, self.intervalo = NIVELES[nivel]
        self.duracion = duracion
        self.demo = demo
        self.semaforo = Semaforo()
        self.vehiculos = []
        self.t = 0.0
        self.terminada = False
        self.pausada = False
        self.idx_escala = ESCALAS.index(1.0)
        self.mostrar_rutas = False
        self.mostrar_estelas = True

        self.generados = 0
        self.cruzaron = 0
        self.espera_total = 0.0
        self.espera_max = 0.0
        self.cruz_origen = {o: 0 for o in ORIGENES}
        self.esp_origen = {o: 0.0 for o in ORIGENES}
        self.giros = {g: 0 for g in GIROS}
        self.cola_max = 0
        self.serie = {"t": [], "cola": {o: [] for o in ORIGENES}, "en_via": [], "vel_kmh": [], "cruces": []}
        self.prox_muestra = 1.0

        self.generacion = 0.0
        self.sig_generacion = self.intervalo
        for origen in ORIGENES:
            for i in range(3):
                self.vehiculos.append(Vehiculo(origen, s=60 + i * 95 + random.uniform(0, 12)))
                self.generados += 1

    # --- generación y registro ------------------------------------------
    def _crear(self, origen):
        if len(self.vehiculos) >= 70:
            return False
        for v in self.vehiculos:
            if v.origen == origen and v.s < 95:
                return False
        self.vehiculos.append(Vehiculo(origen))
        self.generados += 1
        return True

    def registrar_cruce(self, v):
        self.cruzaron += 1
        self.espera_total += v.espera
        self.espera_max = max(self.espera_max, v.espera)
        self.cruz_origen[v.origen] += 1
        self.esp_origen[v.origen] += v.espera
        self.giros[v.giro] += 1

    def _muestrear(self):
        colas = {o: 0 for o in ORIGENES}
        suma_v = 0.0
        for v in self.vehiculos:
            suma_v += v.vel
            if not v.cruzo and v.vel < 5:
                colas[v.origen] += 1
        s = self.serie
        s["t"].append(int(round(self.prox_muestra)))
        for o in ORIGENES:
            s["cola"][o].append(colas[o])
        s["en_via"].append(len(self.vehiculos))
        s["vel_kmh"].append(round(suma_v / len(self.vehiculos) * KMH, 1) if self.vehiculos else 0.0)
        s["cruces"].append(self.cruzaron)
        self.cola_max = max(self.cola_max, max(colas.values()))

    def actualizar(self, dt):
        self.t += dt
        self.semaforo.actualizar(dt)
        self.generacion += dt
        if self.generacion >= self.sig_generacion:
            self.generacion = 0.0
            self.sig_generacion = self.intervalo * random.uniform(0.7, 1.3)
            self._crear(random.choice(ORIGENES))
        for v in self.vehiculos:
            v.actualizar(dt, self)
        self.vehiculos = [v for v in self.vehiculos if not v.fuera_pantalla()]
        if not self.demo:
            while self.t >= self.prox_muestra:
                self._muestrear()
                self.prox_muestra += 1.0
            if self.t >= self.duracion:
                self.terminada = True

    def resultados(self):
        ahora = datetime.now()
        n = self.cruzaron
        vel = self.serie["vel_kmh"]
        return {
            "fecha": ahora.strftime("%d/%m/%Y %H:%M:%S"),
            "fecha_archivo": ahora.strftime("%Y-%m-%d_%H-%M-%S"),
            "trafico": self.nombre_nivel,
            "duracion_s": round(self.t, 1),
            "generados": self.generados,
            "cruzaron": n,
            "espera_prom": round(self.espera_total / n, 2) if n else 0.0,
            "espera_max": round(self.espera_max, 1),
            "cola_max": self.cola_max,
            "flujo_veh_min": round(n / (self.t / 60.0), 1) if self.t > 0 else 0.0,
            "vel_media_kmh": round(sum(vel) / len(vel), 1) if vel else 0.0,
            "por_origen": {o: {"cruzaron": self.cruz_origen[o],
                               "espera_prom": round(self.esp_origen[o] / self.cruz_origen[o], 2)
                               if self.cruz_origen[o] else 0.0} for o in ORIGENES},
            "giros": dict(self.giros),
            "serie": self.serie,
            "pdf": "",
        }

    # --- dibujo ---------------------------------------------------------
    def dibujar_hud(self, c):
        c.blit(recurso_hud(), (0, 0))
        detenidos = sum(1 for v in self.vehiculos if v.vel < 3)
        items = [
            (f"Tráfico {self.nombre_nivel}", BLANCO),
            (f"Tiempo {self.t:4.0f}/{self.duracion} s", BLANCO),
            (f"Generados {self.generados}", BLANCO),
            (f"Cruzaron {self.cruzaron}", BLANCO),
            (f"Detenidos {detenidos}", AMARILLO if detenidos > 6 else BLANCO),
            (self.semaforo.descripcion(), self.semaforo.color()),
            (f"Vel x{ESCALAS[self.idx_escala]:g}", BLANCO),
        ]
        x = 14
        for msg, col in items:
            r = texto(c, msg, F_HUD, col, (x, 14))
            x = r.right + 16
        if self.pausada:
            texto(c, "PAUSA", F_HUD, AMARILLO, (ANCHO_V - 14, 14), derecha=True)
        pygame.draw.rect(c, (40, 50, 58), (0, 48, ANCHO_V, 4))
        pygame.draw.rect(c, ACENTO, (0, 48, int(ANCHO_V * min(1.0, self.t / self.duracion)), 4))
        ayuda = ("ESPACIO pausa  |  +/- velocidad  |  T trayectorias  |  E estelas  |  "
                 "F terminar y ver gráficas  |  ESC cancelar  |  F11 pantalla completa")
        texto(c, ayuda, F_PEQ, (225, 228, 220), (14, ALTO_V - 24))

    def renderizar(self, c, hud=True):
        c.blit(recurso_fondo(), (0, 0))
        if self.mostrar_rutas:
            c.blit(recurso_rutas(), (0, 0))
        if self.mostrar_estelas:
            for v in self.vehiculos:
                n = len(v.estela)
                if n < 2:
                    continue
                pts = list(v.estela)
                for i in range(1, n):
                    k = i / n
                    col = tuple(int(CALLE[j] + (v.color[j] - CALLE[j]) * k * 0.9) for j in range(3))
                    pygame.draw.line(c, col, pts[i - 1], pts[i], 3)
        for v in self.vehiculos:
            v.dibujar_sombra(c)
        for v in self.vehiculos:
            v.dibujar(c)
        self.semaforo.dibujar(c)
        if hud:
            self.dibujar_hud(c)


# ──────────────────────────────────────────────
# Historial (JSON)
# ──────────────────────────────────────────────
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


# ──────────────────────────────────────────────
# Gráficas (matplotlib): se usan en pantalla (tema oscuro) y en el PDF (tema claro)
# ──────────────────────────────────────────────
TEMAS = {
    "oscuro": dict(fig="#12181c", ax="#1b242a", txt="#e8ebe6", sub="#9aa5ab", grid="#33404a"),
    "claro": dict(fig="#ffffff", ax="#fbfcfd", txt="#1b2328", sub="#5b666d", grid="#d9dee2"),
}
HEX_ORIGEN = {"OESTE": "#41bef5", "ESTE": "#46dcbe", "NORTE": "#ff9b41", "SUR": "#f55f69"}
HEX_GIRO = {"FRENTE": "#78aae6", "DERECHA": "#5ae696", "IZQUIERDA": "#ffbe50"}
HEX_NIVEL = {"Bajo": "#4cc38a", "Medio": "#f0b53c", "Alto": "#ef5b5b"}
HEX_ACENTO, HEX_AMAR = "#3d93f0", "#e8a820"


def _estilo(ax, T, titulo, fs, xlabel=None, ylabel=None):
    ax.set_facecolor(T["ax"])
    ax.set_title(titulo, fontsize=fs + 1.5, color=T["txt"], weight="bold", loc="left", pad=6)
    ax.tick_params(colors=T["sub"], labelsize=fs - 0.5, length=2)
    for sp in ax.spines.values():
        sp.set_color(T["grid"])
    ax.grid(True, color=T["grid"], linewidth=0.5, alpha=0.8)
    ax.set_axisbelow(True)
    if xlabel:
        ax.set_xlabel(xlabel, color=T["sub"], fontsize=fs)
    if ylabel:
        ax.set_ylabel(ylabel, color=T["sub"], fontsize=fs)


def _leyenda(ax, T, fs, **kw):
    leg = ax.legend(fontsize=fs - 1, frameon=True, facecolor=T["ax"], edgecolor=T["grid"],
                    labelcolor=T["txt"], **kw)
    leg.get_frame().set_alpha(0.9)


def _vacio(ax, T, fs, msg="Sin datos"):
    ax.text(0.5, 0.5, msg, ha="center", va="center", transform=ax.transAxes, color=T["sub"], fontsize=fs + 1)


def g_flujo(ax, res, hist, idx, T, fs):
    cr = res["serie"]["cruces"]
    paso = 5 if len(cr) <= 90 else 10
    _estilo(ax, T, f"Cruces cada {paso} s", fs, "Tiempo (s)", "Vehículos")
    if not cr:
        return _vacio(ax, T, fs)

    def acum(tt):
        return 0 if tt <= 0 else cr[min(tt, len(cr)) - 1]

    n = math.ceil(len(cr) / paso)
    vals = [acum((i + 1) * paso) - acum(i * paso) for i in range(n)]
    xs = [i * paso + paso / 2 for i in range(n)]
    ax.bar(xs, vals, width=paso * 0.82, color=HEX_ACENTO)
    media = sum(vals) / len(vals)
    ax.axhline(media, color=HEX_AMAR, ls="--", lw=1.2, label=f"Media {media:.1f}")
    _leyenda(ax, T, fs, loc="upper right")


def g_colas(ax, res, hist, idx, T, fs):
    _estilo(ax, T, "Cola por acceso (vehículos detenidos)", fs, "Tiempo (s)", "Vehículos")
    s = res["serie"]
    if not s["t"]:
        return _vacio(ax, T, fs)
    for o in ORIGENES:
        ax.plot(s["t"], s["cola"][o], color=HEX_ORIGEN[o], lw=1.6, label=ETIQ[o])
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    _leyenda(ax, T, fs, loc="upper left", ncol=2)


def _barras(ax, T, fs, claves, valores, colores, fmt):
    ax.bar(range(len(claves)), valores, color=colores, width=0.62)
    ax.set_xticks(range(len(claves)))
    ax.set_xticklabels([ETIQ[k] for k in claves])
    tope = max(valores) if valores and max(valores) > 0 else 1
    ax.set_ylim(0, tope * 1.22)
    for i, v in enumerate(valores):
        ax.text(i, v + tope * 0.02, fmt(v), ha="center", va="bottom", fontsize=fs, color=T["txt"])


def g_espera(ax, res, hist, idx, T, fs):
    _estilo(ax, T, "Espera promedio por acceso", fs, None, "Segundos")
    vals = [res["por_origen"][o]["espera_prom"] for o in ORIGENES]
    _barras(ax, T, fs, ORIGENES, vals, [HEX_ORIGEN[o] for o in ORIGENES], lambda v: f"{v:.1f}")


def g_cruces_origen(ax, res, hist, idx, T, fs):
    _estilo(ax, T, "Vehículos que cruzaron por acceso", fs, None, "Vehículos")
    vals = [res["por_origen"][o]["cruzaron"] for o in ORIGENES]
    _barras(ax, T, fs, ORIGENES, vals, [HEX_ORIGEN[o] for o in ORIGENES], lambda v: f"{v:d}")


def g_giros(ax, res, hist, idx, T, fs):
    _estilo(ax, T, "Maniobras de los que cruzaron", fs)
    ax.grid(False)
    claves = [g for g in GIROS if res["giros"].get(g, 0) > 0]
    total = sum(res["giros"].values())
    if not claves:
        return _vacio(ax, T, fs)
    vals = [res["giros"][g] for g in claves]
    _, _, auto = ax.pie(
        vals, labels=[ETIQ[g] for g in claves], colors=[HEX_GIRO[g] for g in claves],
        autopct=lambda p: f"{p:.0f}%" if p >= 6 else "", pctdistance=0.78, startangle=90, counterclock=False,
        wedgeprops=dict(width=0.45, edgecolor=T["ax"], linewidth=1.5), textprops=dict(fontsize=fs, color=T["txt"]))
    for a in auto:
        a.set_color("#0e1215")
        a.set_weight("bold")
        a.set_fontsize(fs - 0.5)
    ax.text(0, 0, f"{total}\ncruces", ha="center", va="center", color=T["txt"], fontsize=fs, weight="bold")


def g_velocidad(ax, res, hist, idx, T, fs):
    _estilo(ax, T, "Velocidad media y vehículos en vía", fs, "Tiempo (s)", "km/h")
    s = res["serie"]
    if not s["t"]:
        return _vacio(ax, T, fs)
    l1, = ax.plot(s["t"], s["vel_kmh"], color=HEX_ACENTO, lw=1.8, label="Velocidad media (km/h)")
    ax.set_ylim(bottom=0)
    ax.set_xlim(left=0)
    ax2 = ax.twinx()
    l2, = ax2.plot(s["t"], s["en_via"], color=HEX_AMAR, lw=1.3, ls="--", label="Vehículos en vía")
    ax2.tick_params(colors=T["sub"], labelsize=fs - 0.5, length=2)
    for sp in ax2.spines.values():
        sp.set_color(T["grid"])
    ax2.set_ylabel("Vehículos", color=T["sub"], fontsize=fs)
    ax2.set_ylim(bottom=0)
    leg = ax.legend([l1, l2], [l1.get_label(), l2.get_label()], fontsize=fs - 1, loc="lower right",
                    frameon=True, facecolor=T["ax"], edgecolor=T["grid"], labelcolor=T["txt"])
    leg.get_frame().set_alpha(0.9)


def _ventana(hist, idx):
    base = max(0, idx - 11)
    return base, hist[base: idx + 1]


def g_comp_cruces(ax, res, hist, idx, T, fs):
    _estilo(ax, T, "Cruces por corrida", fs, "Corrida", "Vehículos")
    base, vent = _ventana(hist, idx)
    if not vent:
        return _vacio(ax, T, fs)
    for k, r in enumerate(vent):
        actual = (k == len(vent) - 1)
        ax.bar(k, r["cruzaron"], color=HEX_NIVEL.get(r["trafico"], HEX_ACENTO), width=0.7,
               edgecolor=T["txt"] if actual else "none", linewidth=1.8 if actual else 0)
    ax.set_xticks(range(len(vent)))
    ax.set_xticklabels([f"#{base + k + 1}" for k in range(len(vent))])
    niveles = [n for n in HEX_NIVEL if any(r["trafico"] == n for r in vent)]
    _leyenda(ax, T, fs, handles=[Patch(color=HEX_NIVEL[n], label=f"Tráfico {n}") for n in niveles],
             loc="upper left")
    ax.set_ylim(0, max(r["cruzaron"] for r in vent) * 1.35 + 1)


def g_comp_espera(ax, res, hist, idx, T, fs):
    _estilo(ax, T, "Espera promedio por corrida", fs, "Corrida", "Segundos")
    base, vent = _ventana(hist, idx)
    if not vent:
        return _vacio(ax, T, fs)
    xs = list(range(len(vent)))
    ys = [r["espera_prom"] for r in vent]
    ax.plot(xs, ys, color=HEX_ACENTO, lw=1.6, zorder=2)
    ax.scatter(xs, ys, c=[HEX_NIVEL.get(r["trafico"], HEX_ACENTO) for r in vent], s=46, zorder=3,
               edgecolors=T["txt"], linewidths=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"#{base + k + 1}" for k in xs])
    ax.set_ylim(0, max(ys + [1]) * 1.25)


VISTAS = {
    0: [g_flujo, g_colas, g_espera, g_giros],
    1: [g_cruces_origen, g_velocidad, g_comp_cruces, g_comp_espera],
}
NOMBRE_VISTA = {0: "Principal", 1: "Detalle"}


def _rellenar(fig, gs, res, hist, idx, vista, T, fs):
    for i, fn in enumerate(VISTAS[vista]):
        fn(fig.add_subplot(gs[i // 2, i % 2]), res, hist, idx, T, fs)


def figura_pantalla(res, hist, idx, vista):
    T = TEMAS["oscuro"]
    fig = Figure(figsize=(9.6, 4.7), dpi=100, facecolor=T["fig"])
    FigureCanvasAgg(fig)
    gs = fig.add_gridspec(2, 2, left=0.06, right=0.985, top=0.93, bottom=0.095, hspace=0.72, wspace=0.27)
    _rellenar(fig, gs, res, hist, idx, vista, T, 7.5)
    return fig


def observaciones(res):
    po = res["por_origen"]
    if res["cruzaron"] == 0:
        return ["No cruzó ningún vehículo durante la corrida."]
    peor = max(ORIGENES, key=lambda o: po[o]["espera_prom"])
    mejor = min(ORIGENES, key=lambda o: po[o]["espera_prom"])
    top = max(ORIGENES, key=lambda o: po[o]["cruzaron"])
    giro = max(GIROS, key=lambda g: res["giros"].get(g, 0))
    cr = res["serie"]["cruces"]
    pico = ""
    if len(cr) >= 10:
        mejor_i, mejor_v = 0, -1
        for i in range(0, len(cr) - 9, 5):
            v = cr[i + 9] - (cr[i - 1] if i > 0 else 0)
            if v > mejor_v:
                mejor_i, mejor_v = i, v
        pico = f"El intervalo de 10 s con más flujo fue {mejor_i + 1}-{mejor_i + 10} s ({mejor_v} cruces). "
    ratio = res["cruzaron"] / res["generados"] * 100 if res["generados"] else 0
    return [
        f"• Mayor espera promedio en el acceso {ETIQ[peor]} ({po[peor]['espera_prom']:.1f} s) y menor en el acceso "
        f"{ETIQ[mejor]} ({po[mejor]['espera_prom']:.1f} s).",
        f"• El acceso con más cruces fue {ETIQ[top]} ({po[top]['cruzaron']} de {res['cruzaron']} vehículos). "
        f"La maniobra más frecuente fue «{ETIQ[giro].lower()}».",
        f"• Cruzó el {ratio:.0f}% de los vehículos generados; la cola máxima fue de {res['cola_max']} vehículos y la "
        f"velocidad media de {res['vel_media_kmh']} km/h.",
        f"• {pico}Ciclo del semáforo: verde 10 s, amarillo 2.5 s y todo rojo 1.2 s por eje.",
    ]


def figura_pdf(res, hist, idx, vista):
    T = TEMAS["claro"]
    fig = Figure(figsize=(8.27, 11.69), dpi=100, facecolor=T["fig"])
    FigureCanvasAgg(fig)
    fig.text(0.07, 0.955, "Reporte de simulación de tráfico", fontsize=19, weight="bold", color=T["txt"])
    fig.text(0.07, 0.930, f"{res['fecha']}   ·   Tráfico {res['trafico']}   ·   "
             f"Duración {res['duracion_s']:g} s simulados", fontsize=9.5, color=T["sub"])
    fig.add_artist(Rectangle((0.07, 0.918), 0.86, 0.0018, transform=fig.transFigure,
                             facecolor=HEX_ACENTO, edgecolor="none"))
    if vista == 0:
        kp = [("Vehículos generados", str(res["generados"])), ("Vehículos que cruzaron", str(res["cruzaron"])),
              ("Espera promedio", f"{res['espera_prom']:.1f} s"), ("Espera máxima", f"{res['espera_max']:.1f} s"),
              ("Cola máxima", f"{res['cola_max']} veh."), ("Flujo", f"{res['flujo_veh_min']} veh/min")]
        for i, (lab, val) in enumerate(kp):
            x, y, w, h = 0.07 + (i % 3) * 0.2933, 0.80 - (i // 3) * 0.10, 0.2733, 0.08
            fig.add_artist(Rectangle((x, y), w, h, transform=fig.transFigure, facecolor="#f1f4f7",
                                     edgecolor=T["grid"], linewidth=0.8))
            fig.text(x + 0.015, y + h - 0.027, lab, fontsize=8.5, color=T["sub"])
            fig.text(x + 0.015, y + 0.016, val, fontsize=16, weight="bold", color=T["txt"])
    else:
        fig.text(0.07, 0.885, "Observaciones", fontsize=12, weight="bold", color=T["txt"])
        y = 0.858
        for linea in observaciones(res):
            partes = textwrap.wrap(linea, 98, subsequent_indent="   ")
            for p in partes:
                fig.text(0.07, y, p, fontsize=9, color=T["txt"])
                y -= 0.0205
            y -= 0.006
    gs = fig.add_gridspec(2, 2, left=0.09, right=0.95, top=0.635, bottom=0.095, hspace=0.62, wspace=0.34)
    _rellenar(fig, gs, res, hist, idx, vista, T, 8)
    fig.text(0.07, 0.028, "Simulador de Tráfico · Fase 6", fontsize=8, color=T["sub"])
    fig.text(0.93, 0.028, f"Página {vista + 1}/2", fontsize=8, color=T["sub"], ha="right")
    return fig


def guardar_pdf(res, hist, idx):
    """Guarda el reporte en reportes/reporte_AAAA-MM-DD_HH-MM-SS.pdf y devuelve la ruta."""
    os.makedirs(CARPETA_PDF, exist_ok=True)
    nombre = f"reporte_{res['fecha_archivo']}.pdf"
    ruta = os.path.join(CARPETA_PDF, nombre)
    with PdfPages(ruta) as pdf:
        info = pdf.infodict()
        info["Title"] = f"Reporte de simulación de tráfico - {res['fecha']}"
        info["Author"] = "Simulador de Tráfico"
        for vista in (0, 1):
            pdf.savefig(figura_pdf(res, hist, idx, vista))
    res["pdf"] = nombre
    return ruta


def figura_a_superficie(fig):
    canvas = fig.canvas
    canvas.draw()
    w, h = canvas.get_width_height()
    return pygame.image.frombuffer(bytes(canvas.buffer_rgba()), (w, h), "RGBA").convert()


# ──────────────────────────────────────────────
# Ventana de gráficas
# ──────────────────────────────────────────────
class PantallaGraficas:
    def __init__(self):
        self.hist = []
        self.idx = 0
        self.vista = 0
        self.cache = {}
        self.mensaje = ""
        self.msg_color = VERDE
        gris = (70, 82, 94)
        self.b_ant = Boton((20, 646, 118, 44), "< Anterior", gris, F_BTN_S)
        self.b_sig = Boton((146, 646, 118, 44), "Siguiente >", gris, F_BTN_S)
        self.b_vista = Boton((272, 646, 190, 44), "", (110, 90, 190), F_BTN_S)
        self.b_pdf = Boton((470, 646, 150, 44), "Guardar PDF", (46, 160, 100), F_BTN_S)
        self.b_carpeta = Boton((628, 646, 156, 44), "Abrir carpeta", gris, F_BTN_S)
        self.b_menu = Boton((792, 646, 90, 44), "Menú", (90, 100, 110), F_BTN_S)
        self.b_repetir = Boton((890, 646, 90, 44), "Repetir", ACENTO, F_BTN_S)
        self.b_menu_solo = Boton((400, 420, 200, 52), "Volver al menú", (90, 100, 110))

    def abrir(self, hist, idx=None, mensaje="", color=VERDE):
        self.hist = hist
        self.idx = (len(hist) - 1) if idx is None else idx
        self.vista = 0
        self.cache = {}
        self.mensaje, self.msg_color = mensaje, color

    def _superficie(self):
        clave = (self.idx, self.vista)
        if clave not in self.cache:
            fig = figura_pantalla(self.hist[self.idx], self.hist, self.idx, self.vista)
            self.cache[clave] = figura_a_superficie(fig)
        return self.cache[clave]

    def _guardar_pdf(self):
        if not HAY_MPL:
            self.mensaje, self.msg_color = "Falta matplotlib:  pip install matplotlib", AMARILLO
            return
        try:
            ruta = guardar_pdf(self.hist[self.idx], self.hist, self.idx)
            guardar_historial(self.hist)
            self.mensaje, self.msg_color = f"PDF guardado: reportes/{os.path.basename(ruta)}", VERDE
        except Exception as e:  # noqa
            self.mensaje, self.msg_color = f"No se pudo guardar el PDF: {e}", ROJO

    def _ir(self, nuevo):
        if 0 <= nuevo < len(self.hist):
            self.idx = nuevo
            self.mensaje = ""

    def manejar(self, ev):
        if not self.hist:
            return "menu" if self.b_menu_solo.clic(ev) else None
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_LEFT:
                self._ir(self.idx - 1)
            elif ev.key == pygame.K_RIGHT:
                self._ir(self.idx + 1)
            elif ev.key == pygame.K_TAB:
                self.vista = 1 - self.vista
            elif ev.key == pygame.K_g:
                self._guardar_pdf()
            elif ev.key == pygame.K_ESCAPE:
                return "menu"
        self.b_ant.habilitado = self.idx > 0
        self.b_sig.habilitado = self.idx < len(self.hist) - 1
        if self.b_ant.clic(ev):
            self._ir(self.idx - 1)
        elif self.b_sig.clic(ev):
            self._ir(self.idx + 1)
        elif self.b_vista.clic(ev):
            self.vista = 1 - self.vista
        elif self.b_pdf.clic(ev):
            self._guardar_pdf()
        elif self.b_carpeta.clic(ev):
            abrir_carpeta(CARPETA_PDF)
        elif self.b_menu.clic(ev):
            return "menu"
        elif self.b_repetir.clic(ev):
            return "repetir"
        return None

    def dibujar(self, c):
        c.fill(FONDO)
        texto(c, "ANÁLISIS DE RESULTADOS", F_SEC, BLANCO, (24, 14))
        if not self.hist:
            texto(c, "Aún no hay simulaciones guardadas.", F_SUB, GRIS, (ANCHO_V // 2, 330), centro=True)
            texto(c, "Vuelve al menú y pulsa «Iniciar simulación».", F_TXT, GRIS, (ANCHO_V // 2, 365), centro=True)
            self.b_menu_solo.dibujar(c)
            return
        res = self.hist[self.idx]
        texto(c, f"Corrida {self.idx + 1} de {len(self.hist)}   ·   {res['fecha']}   ·   "
              f"Tráfico {res['trafico']}   ·   {res['duracion_s']:g} s simulados", F_TXT, GRIS, (24, 52))
        kpis = [("Generados", str(res["generados"]), BLANCO), ("Cruzaron", str(res["cruzaron"]), VERDE),
                ("Espera promedio", f"{res['espera_prom']:.1f} s", BLANCO),
                ("Espera máxima", f"{res['espera_max']:.1f} s", BLANCO),
                ("Cola máxima", f"{res['cola_max']} veh.", AMARILLO if res["cola_max"] > 8 else BLANCO),
                ("Flujo", f"{res['flujo_veh_min']} veh/min", ACENTO)]
        for i, (lab, val, col) in enumerate(kpis):
            tarjeta(c, 25 + i * 160, 82, 150, 56, lab, val, col)

        if HAY_MPL:
            try:
                c.blit(self._superficie(), (20, 146))
            except Exception as e:  # noqa
                texto(c, f"Error al generar las gráficas: {e}", F_TXT, ROJO, (30, 300))
        else:
            pygame.draw.rect(c, PANEL, (20, 146, 960, 470), border_radius=12)
            texto(c, "Para ver las gráficas y generar PDF instala matplotlib:", F_SUB, BLANCO,
                  (ANCHO_V // 2, 350), centro=True)
            texto(c, "pip install matplotlib", F_BTN, AMARILLO, (ANCHO_V // 2, 395), centro=True)

        if self.mensaje:
            texto(c, self.mensaje, F_PEQ, self.msg_color, (24, 622))
        elif res.get("pdf"):
            texto(c, f"Reporte: reportes/{res['pdf']}", F_PEQ, GRIS, (24, 622))
        texto(c, "← → cambiar corrida   |   TAB cambiar vista   |   G guardar PDF", F_PEQ, GRIS,
              (ANCHO_V - 24, 622), derecha=True)

        self.b_ant.habilitado = self.idx > 0
        self.b_sig.habilitado = self.idx < len(self.hist) - 1
        self.b_vista.etiqueta = f"Vista: {NOMBRE_VISTA[self.vista]} ({self.vista + 1}/2)"
        for b in (self.b_ant, self.b_sig, self.b_vista, self.b_pdf, self.b_carpeta, self.b_menu, self.b_repetir):
            b.dibujar(c)


# ──────────────────────────────────────────────
# Ventana de inicio
# ──────────────────────────────────────────────
def dibujar_menu(c, demo, botones, hist_n):
    demo.renderizar(c, hud=False)
    c.blit(recurso_velo(), (0, 0))
    panel = pygame.Rect(280, 60, 440, 580)
    pygame.draw.rect(c, PANEL, panel, border_radius=20)
    pygame.draw.rect(c, (52, 64, 72), panel, width=2, border_radius=20)
    texto(c, "SIMULADOR", F_TITULO, BLANCO, (ANCHO_V // 2, 112), centro=True)
    texto(c, "DE TRÁFICO", F_TITULO, ACENTO, (ANCHO_V // 2, 154), centro=True)
    texto(c, "Intersección con semáforo y giros", F_SUB, GRIS, (ANCHO_V // 2, 196), centro=True)
    for b in botones:
        b.dibujar(c)
    estado_mpl = "" if HAY_MPL else "   ·   ¡falta matplotlib!"
    texto(c, f"Corridas guardadas: {hist_n}{estado_mpl}", F_PEQ, AMARILLO if not HAY_MPL else GRIS,
          (ANCHO_V // 2, 574), centro=True)
    texto(c, "Los reportes PDF se guardan en la carpeta «reportes»", F_PEQ, GRIS,
          (ANCHO_V // 2, 600), centro=True)


def terminar_simulacion(sim, grafs):
    res = sim.resultados()
    hist = cargar_historial()
    hist.append(res)
    idx = len(hist) - 1
    if HAY_MPL:
        try:
            ruta = guardar_pdf(res, hist, idx)
            msg, col = f"Reporte PDF guardado: reportes/{os.path.basename(ruta)}", VERDE
        except Exception as e:  # noqa
            msg, col = f"No se pudo guardar el PDF: {e}", ROJO
    else:
        msg, col = "Instala matplotlib para generar gráficas y PDF:  pip install matplotlib", AMARILLO
    guardar_historial(hist)
    grafs.abrir(hist, idx, msg, col)


# ──────────────────────────────────────────────
# Presentación escalada (ventana redimensionable)
# ──────────────────────────────────────────────
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


# ──────────────────────────────────────────────
# Bucle principal
# ──────────────────────────────────────────────
def main():
    estado = "MENU"
    nivel, dur_i = 1, 0
    demo = Simulacion(nivel, 10 ** 9, demo=True)
    sim = None
    grafs = PantallaGraficas()
    hist_n = len(cargar_historial())

    bx, bw, bh = 330, 340, 52
    b_iniciar = Boton((bx, 232, bw, bh), "Iniciar simulación", (46, 160, 100))
    b_nivel = Boton((bx, 296, bw, bh), "", (120, 100, 200))
    b_dur = Boton((bx, 360, bw, bh), "", (200, 130, 50))
    b_graf = Boton((bx, 424, bw, bh), "Ver gráficas", ACENTO)
    b_salir = Boton((bx, 488, bw, bh), "Salir", (170, 70, 70))
    botones_menu = [b_iniciar, b_nivel, b_dur, b_graf, b_salir]

    def salir():
        pygame.quit()
        sys.exit()

    while True:
        dt_real = min(RELOJ.tick(FPS) / 1000.0, 0.05)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                salir()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_F11:
                try:
                    pygame.display.toggle_fullscreen()
                except pygame.error:
                    pass

            if estado == "MENU":
                if b_iniciar.clic(ev):
                    sim, estado = Simulacion(nivel, DURACIONES[dur_i]), "SIM"
                elif b_nivel.clic(ev):
                    nivel = (nivel + 1) % len(NIVELES)
                    demo = Simulacion(nivel, 10 ** 9, demo=True)
                elif b_dur.clic(ev):
                    dur_i = (dur_i + 1) % len(DURACIONES)
                elif b_graf.clic(ev):
                    grafs.abrir(cargar_historial())
                    estado = "GRAF"
                elif b_salir.clic(ev):
                    salir()
            elif estado == "SIM":
                if ev.type == pygame.KEYDOWN:
                    k = ev.key
                    if k == pygame.K_ESCAPE:
                        estado = "MENU"
                    elif k == pygame.K_SPACE:
                        sim.pausada = not sim.pausada
                    elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        sim.idx_escala = min(len(ESCALAS) - 1, sim.idx_escala + 1)
                    elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        sim.idx_escala = max(0, sim.idx_escala - 1)
                    elif k == pygame.K_t:
                        sim.mostrar_rutas = not sim.mostrar_rutas
                    elif k == pygame.K_e:
                        sim.mostrar_estelas = not sim.mostrar_estelas
                    elif k == pygame.K_f:
                        terminar_simulacion(sim, grafs)
                        estado = "GRAF"
            elif estado == "GRAF":
                accion = grafs.manejar(ev)
                if accion == "menu":
                    hist_n = len(cargar_historial())
                    estado = "MENU"
                elif accion == "repetir":
                    sim, estado = Simulacion(nivel, DURACIONES[dur_i]), "SIM"

        # --- actualización ---
        if estado == "MENU":
            demo.actualizar(dt_real)
        elif estado == "SIM" and not sim.pausada:
            dt = dt_real * ESCALAS[sim.idx_escala]
            pasos = max(1, math.ceil(dt / (1 / 90)))
            for _ in range(pasos):
                sim.actualizar(dt / pasos)
                if sim.terminada:
                    break
            if sim.terminada:
                terminar_simulacion(sim, grafs)
                estado = "GRAF"

        # --- dibujo ---
        if estado == "MENU":
            b_nivel.etiqueta = f"Tráfico: {NIVELES[nivel][0]}"
            b_dur.etiqueta = f"Duración: {DURACIONES[dur_i]} s"
            dibujar_menu(CANVAS, demo, botones_menu, hist_n)
        elif estado == "SIM":
            sim.renderizar(CANVAS)
        elif estado == "GRAF":
            grafs.dibujar(CANVAS)
        presentar()


if __name__ == "__main__":
    main()

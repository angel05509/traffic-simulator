"""
Simulador de Tráfico - Fase 5 (Unificado, Responsivo y con Giros Fluidos)
=========================================================================
Fusión de las dos versiones de la Fase 5, con el motor de movimiento rehecho.

Novedades principales
- Giros fluidos: cada coche sigue una trayectoria curva (Bézier) por su carril
  y el sprite rota de forma continua con la tangente de la curva. Se ve
  cómo giran a la derecha, a la izquierda o siguen de frente.
- Frenado suave antes del giro y aceleración progresiva al salir.
- Cruce sin choques: reserva de intersección. Un coche solo entra si su
  trayectoria no entra en conflicto con la de otro coche que ya cruza y si la
  calle de salida tiene espacio (evita bloqueos / gridlock).
  Quien lleva más tiempo esperando tiene prioridad (sin inanición).
- Semáforo con fase de "todo rojo", decisión de amarillo realista y cuenta
  regresiva.
- Distancia de seguridad siguiendo la trayectoria (también dentro de curvas).
- Luces direccionales y luces de freno.
- Diseño responsivo: el lienzo virtual se escala al redimensionar o maximizar.
- Movimiento con delta time y subpasos (estable a cualquier FPS).

Controles
  ESPACIO  pausar / reanudar         R      reiniciar tráfico
  T        ver trayectorias de giro  E      ver estelas de los giros
  ↑ / ↓    más / menos tráfico       + / -  velocidad de simulación (cámara lenta)
  F11      pantalla completa         ESC    salir

Requisitos: pip install pygame
"""

import math
import random
import sys
from bisect import bisect_right
from collections import deque

import pygame

# ──────────────────────────────────────────────
# Configuración de lienzo virtual y geometría
# ──────────────────────────────────────────────
ANCHO_VIRTUAL, ALTO_VIRTUAL = 1000, 700
FPS_OBJETIVO = 120
TITULO = "Simulador de Tráfico - Fase 5 (Unificado, Responsivo y Giros Fluidos)"

CENTRO_X, CENTRO_Y = ANCHO_VIRTUAL // 2, ALTO_VIRTUAL // 2
ANCHO_CALLE = 180
MITAD = ANCHO_CALLE // 2
CARRIL = 43            # distancia del centro de la calle al centro de cada carril
DIST_PARADA = 26       # distancia de la línea de alto al borde de la intersección
MARGEN_FUERA = 70      # los coches nacen / mueren a esta distancia fuera de pantalla

X_IZQ = CENTRO_X - MITAD
X_DER = CENTRO_X + MITAD
Y_ARRIBA = CENTRO_Y - MITAD
Y_ABAJO = CENTRO_Y + MITAD

LARGO, ANCHO = 42, 23  # tamaño del coche

# Física (px/s y px/s²)
A_ACEL = 160.0
A_COMODO = 190.0       # frenado "de planificación"
A_FRENO = 340.0        # frenado máximo real (siempre mayor que A_COMODO)
UMBRAL_CONFLICTO = 40.0

pygame.init()
pygame.display.set_caption(TITULO)

PANTALLA_REAL = pygame.display.set_mode((ANCHO_VIRTUAL, ALTO_VIRTUAL), pygame.RESIZABLE | pygame.DOUBLEBUF)
CANVAS_VIRTUAL = pygame.Surface((ANCHO_VIRTUAL, ALTO_VIRTUAL))

RELOJ = pygame.time.Clock()
_FAMILIA = "segoeui,arial,dejavusans,helvetica"
FUENTE = pygame.font.SysFont(_FAMILIA, 18)
FUENTE_PEQUENA = pygame.font.SysFont(_FAMILIA, 14)
FUENTE_TITULO = pygame.font.SysFont(_FAMILIA, 22, bold=True)

# Paleta
GRAMA = (33, 57, 48)
CALLE = (53, 57, 62)
BORDE = (115, 120, 123)
LINEA = (205, 203, 176)
BLANCO = (242, 242, 235)
AMARILLO = (255, 197, 61)
ROJO = (255, 75, 75)
VERDE = (65, 220, 120)
APAGADO = (62, 65, 67)

COLORES_H = [(65, 190, 245), (70, 220, 190), (95, 145, 255), (220, 225, 235)]
COLORES_V = [(255, 155, 65), (245, 95, 105), (205, 125, 245), (245, 210, 85)]

COLOR_GIRO = {"FRENTE": (120, 170, 230), "DERECHA": (90, 230, 150), "IZQUIERDA": (255, 190, 80)}

# ──────────────────────────────────────────────
# Rutas: cada combinación (origen, giro) es una trayectoria
# ──────────────────────────────────────────────
ORIGENES = ("OESTE", "ESTE", "NORTE", "SUR")
GIROS = ("FRENTE", "DERECHA", "IZQUIERDA")
# Dirección de avance (pantalla: y crece hacia abajo). Tráfico por la derecha.
DIRS = {"OESTE": (1, 0), "ESTE": (-1, 0), "NORTE": (0, 1), "SUR": (0, -1)}


def girar(d, giro):
    dx, dy = d
    if giro == "DERECHA":
        return (-dy, dx)
    if giro == "IZQUIERDA":
        return (dy, -dx)
    return d


class Ruta:
    """Trayectoria completa (entrada → cruce → salida) como polilínea con longitud acumulada."""

    PASOS_CURVA = 40

    def __init__(self, origen, giro):
        self.origen, self.giro = origen, giro
        d = DIRS[origen]
        d2 = girar(d, giro)
        self.dir_entrada, self.dir_salida = d, d2
        self.eje = "H" if d[0] != 0 else "V"

        rv = (-d[1], d[0])       # "derecha" del conductor
        rv2 = (-d2[1], d2[0])
        ext = ANCHO_VIRTUAL // 2 if d[0] != 0 else ALTO_VIRTUAL // 2
        ext2 = ANCHO_VIRTUAL // 2 if d2[0] != 0 else ALTO_VIRTUAL // 2

        inicio = (CENTRO_X + rv[0] * CARRIL - d[0] * (ext + MARGEN_FUERA),
                  CENTRO_Y + rv[1] * CARRIL - d[1] * (ext + MARGEN_FUERA))
        p_in = (CENTRO_X + rv[0] * CARRIL - d[0] * MITAD,
                CENTRO_Y + rv[1] * CARRIL - d[1] * MITAD)
        p_out = (CENTRO_X + rv2[0] * CARRIL + d2[0] * MITAD,
                 CENTRO_Y + rv2[1] * CARRIL + d2[1] * MITAD)
        fin = (CENTRO_X + rv2[0] * CARRIL + d2[0] * (ext2 + MARGEN_FUERA),
               CENTRO_Y + rv2[1] * CARRIL + d2[1] * (ext2 + MARGEN_FUERA))

        pts = [inicio, p_in]
        if giro != "FRENTE":
            # Bézier cuadrática: el punto de control es la esquina donde se cortan
            # la recta de entrada y la recta de salida.
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
        self.s_linea = self.acum[1]            # borde de la intersección
        self.s_parada = self.s_linea - DIST_PARADA
        self.s_salida = self.acum[-2]          # fin de la curva
        self.s_fin_cruce = self.s_salida + 40  # a partir de aquí ya "liberó" el cruce
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
        """Posición y dirección unitaria (tangente suavizada) en la distancia s."""
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
    """True si las trayectorias dentro del cruce se acercan lo suficiente como para chocar."""
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

    def texto(self):
        nombres = {"H_VERDE": "H VERDE", "H_AMARILLO": "H AMARILLO", "V_VERDE": "V VERDE",
                   "V_AMARILLO": "V AMARILLO", "H_TODO_ROJO": "TODO ROJO", "V_TODO_ROJO": "TODO ROJO"}
        return f"{nombres[self.estado]} {self.restante():.0f}s"

    def dibujar(self, pantalla):
        # Cada caja está a la derecha de su aproximación, antes de la línea de alto.
        posiciones = [
            (X_IZQ - 42, Y_ABAJO + 8, "H"),    # viene del oeste (→)
            (X_DER + 18, Y_ARRIBA - 57, "H"),  # viene del este (←)
            (X_IZQ - 42, Y_ARRIBA - 57, "V"),  # viene del norte (↓)
            (X_DER + 18, Y_ABAJO + 8, "V"),    # viene del sur (↑)
        ]
        colores = {"ROJO": ROJO, "AMARILLO": AMARILLO, "VERDE": VERDE}
        for x, y, eje in posiciones:
            pygame.draw.rect(pantalla, (17, 19, 21), (x, y, 25, 62), border_radius=7)
            activa = self.luz(eje)
            for i, nombre in enumerate(("ROJO", "AMARILLO", "VERDE")):
                cx, cy = x + 12, y + 11 + i * 20
                if activa == nombre:
                    c = colores[nombre]
                    pygame.draw.circle(pantalla, tuple(int(v * 0.35 + 17 * 0.65) for v in c), (cx, cy), 10)
                    pygame.draw.circle(pantalla, c, (cx, cy), 7)
                else:
                    pygame.draw.circle(pantalla, APAGADO, (cx, cy), 7)


# ──────────────────────────────────────────────
# Vehículo
# ──────────────────────────────────────────────
class Vehiculo:
    _contador = 0

    def __init__(self, origen, s=0.0):
        Vehiculo._contador += 1
        self.id = Vehiculo._contador
        self.origen = origen
        self.giro = random.choices(GIROS, [0.60, 0.20, 0.20])[0]
        self.ruta = RUTAS[(origen, self.giro)]
        self.s = s
        self.v_crucero = random.uniform(105, 140)
        self.v_giro = random.uniform(60, 78)
        self.vel = self.v_crucero
        paleta = COLORES_H if self.ruta.eje == "H" else COLORES_V
        self.color = random.choice(paleta)
        self.autorizado = False     # ya reservó su paso por el cruce
        self.cruzo = False          # ya liberó el cruce
        self.t_espera = 0.0
        self.frenando = False
        self.tick = random.random() * 2
        self.estela = deque(maxlen=45)
        self._cuenta = 0
        self._ult_estela = None
        self._pose()

    # --- geometría ---------------------------------------------------------
    def _pose(self):
        self.x, self.y, self.hx, self.hy = self.ruta.muestra(self.s)

    # --- percepción --------------------------------------------------------
    def _buscar_lider(self, sim):
        """Coche más cercano por delante, siguiendo la trayectoria propia (también en curva)."""
        r = self.ruta
        muestras = []
        for k in range(16, 126, 10):
            qx, qy = r.punto(self.s + k)
            muestras.append((k, qx, qy))
        mejor = None
        for o in sim.vehiculos:
            if o is self:
                continue
            dx, dy = o.x - self.x, o.y - self.y
            if dx * dx + dy * dy > 170 * 170:
                continue
            if o.hx * self.hx + o.hy * self.hy < 0.35:   # solo quien va en sentido parecido
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
        """¿Hay un coche detenido / muy lento justo donde yo saldría del cruce?"""
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
            self.t_espera = 0.0          # puede detenerse con comodidad: se detiene
            return False
        # solo el primero de la fila reserva el cruce
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
                    # alguien con conflicto lleva más tiempo esperando: tiene prioridad
                    if en_conflicto(r, o.ruta):
                        bloqueado = True
                        break
        if bloqueado:
            self.t_espera += dt
            return False
        return True

    # --- dinámica ----------------------------------------------------------
    def actualizar(self, dt, sim):
        r = self.ruta
        self.tick += dt
        objetivo = self.v_crucero

        # 1. Reducir velocidad ANTES del giro y mantenerla durante la curva
        if self.giro != "FRENTE" and self.s < r.s_salida:
            d = max(0.0, r.s_linea - self.s)
            objetivo = min(objetivo, math.sqrt(self.v_giro ** 2 + 2 * A_COMODO * d))

        # 2. Línea de alto: semáforo + reserva del cruce
        if not self.autorizado:
            gap = r.s_parada - 3 - LARGO / 2 - self.s
            if gap < -8:
                self.autorizado = True       # ya pasó la línea (no debería ocurrir)
            else:
                umbral = max(45.0, self.vel ** 2 / (2 * A_COMODO) + 30)
                if gap < umbral and self._evaluar_paso(sim, gap, dt):
                    self.autorizado = True
                    self.t_espera = 0.0
                if not self.autorizado:
                    objetivo = 0.0 if gap < 0.5 else min(objetivo, math.sqrt(2 * A_COMODO * gap))

        # 3. Distancia de seguridad con el coche de adelante
        lider = self._buscar_lider(sim)
        if lider:
            gap, o = lider
            v_perm = math.sqrt(o.vel ** 2 + 2 * A_COMODO * max(0.0, gap - 10))
            if gap < 4:
                v_perm = min(v_perm, o.vel * 0.5)
            objetivo = min(objetivo, v_perm)

        # 4. Aceleración / frenado progresivos
        if objetivo < self.vel:
            self.vel = max(objetivo, self.vel - A_FRENO * dt)
            self.frenando = True
        else:
            self.vel = min(objetivo, self.vel + A_ACEL * dt)
            self.frenando = self.vel < 4
        if self.vel < 0.5 and objetivo == 0.0:
            self.vel = 0.0

        # 5. Avanzar sobre la trayectoria
        self.s += self.vel * dt
        self._pose()

        if self.autorizado and not self.cruzo and self.s > r.s_fin_cruce:
            self.cruzo = True
            sim.pasados += 1

        # 6. Estela del giro (visual)
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

    # --- dibujo ------------------------------------------------------------
    def _grados(self):
        deg = -math.degrees(math.atan2(self.hy, self.hx))
        return int(round(deg / 3.0)) * 3 % 360

    def dibujar_sombra(self, lienzo):
        _, sombra = sprite_coche(self.color, self._grados())
        lienzo.blit(sombra, sombra.get_rect(center=(self.x + 3, self.y + 5)))

    def dibujar(self, lienzo):
        cuerpo, _ = sprite_coche(self.color, self._grados())
        lienzo.blit(cuerpo, cuerpo.get_rect(center=(self.x, self.y)))

        rvx, rvy = -self.hy, self.hx   # lado derecho del conductor

        def mundo(f, lado):
            return (self.x + self.hx * f + rvx * lado, self.y + self.hy * f + rvy * lado)

        if self.frenando:
            for lado in (-1, 1):
                pygame.draw.circle(lienzo, (255, 60, 60), mundo(-(LARGO / 2 - 3), lado * (ANCHO / 2 - 4)), 3)

        r = self.ruta
        if self.giro != "FRENTE" and r.s_linea - 170 <= self.s <= r.s_salida - 10 \
                and int(self.tick * 3.5) % 2 == 0:
            lado = 1 if self.giro == "DERECHA" else -1
            for f in (LARGO / 2 - 4, -(LARGO / 2 - 4)):
                p = mundo(f, lado * (ANCHO / 2 - 3))
                pygame.draw.circle(lienzo, (130, 95, 20), p, 5)
                pygame.draw.circle(lienzo, AMARILLO, p, 3)


# ──────────────────────────────────────────────
# Controlador del simulador
# ──────────────────────────────────────────────
ESCALAS_TIEMPO = [0.1, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0]


class Simulador:
    def __init__(self):
        self.semaforo = Semaforo()
        self.vehiculos = []
        self.ejecutando = True
        self.pausado = False
        self.generacion = 0.0
        self.intervalo = 1.1
        self.fps_mostrados = 0
        self.pasados = 0
        self.idx_escala = ESCALAS_TIEMPO.index(1.0)
        self.mostrar_rutas = False
        self.mostrar_estelas = True
        self._fondo = self._construir_fondo()
        self._overlay_rutas = self._construir_overlay_rutas()
        self._panel_hud = pygame.Surface((ANCHO_VIRTUAL, 44), pygame.SRCALPHA)
        self._panel_hud.fill((13, 17, 20, 215))
        self._escalado = None
        self._reiniciar()

    # --- estado ------------------------------------------------------------
    def _reiniciar(self):
        self.vehiculos.clear()
        self.semaforo = Semaforo()
        self.pasados = 0
        self.generacion = 0.0
        for origen in ORIGENES:
            for i in range(3):
                self.vehiculos.append(Vehiculo(origen, s=60 + i * 95 + random.uniform(0, 12)))

    def _crear_vehiculo(self, origen):
        if len(self.vehiculos) >= 70:
            return
        for v in self.vehiculos:
            if v.origen == origen and v.s < 95:
                return
        self.vehiculos.append(Vehiculo(origen))

    def actualizar(self, dt):
        self.semaforo.actualizar(dt)
        self.generacion += dt
        if self.generacion >= self.intervalo:
            self.generacion = 0.0
            self._crear_vehiculo(random.choice(ORIGENES))
        for v in self.vehiculos:
            v.actualizar(dt, self)
        self.vehiculos = [v for v in self.vehiculos if not v.fuera_pantalla()]

    # --- dibujo estático ---------------------------------------------------
    def _construir_fondo(self):
        f = pygame.Surface((ANCHO_VIRTUAL, ALTO_VIRTUAL))
        f.fill(GRAMA)
        for x in range(20, ANCHO_VIRTUAL, 90):
            for y in range(18, ALTO_VIRTUAL, 85):
                pygame.draw.circle(f, (38, 64, 52), (x + (y % 17), y), 2)

        pygame.draw.rect(f, BORDE, (0, Y_ARRIBA - 4, ANCHO_VIRTUAL, ANCHO_CALLE + 8))
        pygame.draw.rect(f, BORDE, (X_IZQ - 4, 0, ANCHO_CALLE + 8, ALTO_VIRTUAL))
        pygame.draw.rect(f, CALLE, (0, Y_ARRIBA, ANCHO_VIRTUAL, ANCHO_CALLE))
        pygame.draw.rect(f, CALLE, (X_IZQ, 0, ANCHO_CALLE, ALTO_VIRTUAL))

        for x in range(0, ANCHO_VIRTUAL, 38):
            if not X_IZQ - 5 <= x <= X_DER:
                pygame.draw.line(f, LINEA, (x, CENTRO_Y), (x + 20, CENTRO_Y), 2)
        for y in range(0, ALTO_VIRTUAL, 38):
            if not Y_ARRIBA - 5 <= y <= Y_ABAJO:
                pygame.draw.line(f, LINEA, (CENTRO_X, y), (CENTRO_X, y + 20), 2)

        # Pasos peatonales
        cebra = (185, 187, 182)
        for i in range(7):
            xx = X_IZQ + 8 + i * 23
            pygame.draw.rect(f, cebra, (xx, Y_ARRIBA - 19, 13, 13))
            pygame.draw.rect(f, cebra, (xx, Y_ABAJO + 6, 13, 13))
            yy = Y_ARRIBA + 8 + i * 23
            pygame.draw.rect(f, cebra, (X_IZQ - 19, yy, 13, 13))
            pygame.draw.rect(f, cebra, (X_DER + 6, yy, 13, 13))

        # Líneas de alto (una por aproximación, en su mitad de calzada)
        pygame.draw.rect(f, BLANCO, (X_IZQ - DIST_PARADA, CENTRO_Y + 3, 4, MITAD - 3))
        pygame.draw.rect(f, BLANCO, (X_DER + DIST_PARADA - 4, Y_ARRIBA, 4, MITAD - 3))
        pygame.draw.rect(f, BLANCO, (X_IZQ, Y_ARRIBA - DIST_PARADA, MITAD - 3, 4))
        pygame.draw.rect(f, BLANCO, (CENTRO_X + 3, Y_ABAJO + DIST_PARADA - 4, MITAD - 3, 4))
        return f

    def _construir_overlay_rutas(self):
        ov = pygame.Surface((ANCHO_VIRTUAL, ALTO_VIRTUAL), pygame.SRCALPHA)
        for r in RUTAS.values():
            pts, s = [], r.s_linea - 35
            while s <= r.s_salida + 35:
                pts.append(r.punto(s))
                s += 5
            pygame.draw.lines(ov, COLOR_GIRO[r.giro] + (140,), False, pts, 2)
        return ov

    # --- HUD ---------------------------------------------------------------
    def dibujar_hud(self, lienzo):
        lienzo.blit(self._panel_hud, (0, 0))
        detenidos = sum(1 for v in self.vehiculos if v.vel < 3)
        estado = "PAUSADO" if self.pausado else "EN MARCHA"
        x = 16
        t = FUENTE_TITULO.render("TRÁFICO URBANO", True, BLANCO)
        lienzo.blit(t, (x, 9))
        x += t.get_width() + 24
        items = [
            (f"Vehículos {len(self.vehiculos)}", BLANCO),
            (f"Cruzaron {self.pasados}", BLANCO),
            (f"Detenidos {detenidos}", AMARILLO if detenidos > 6 else BLANCO),
            (self.semaforo.texto(), self.semaforo_color()),
            (f"Vel x{ESCALAS_TIEMPO[self.idx_escala]:g}", BLANCO),
            (estado, AMARILLO if self.pausado else VERDE),
        ]
        for texto, color in items:
            s = FUENTE.render(texto, True, color)
            lienzo.blit(s, (x, 12))
            x += s.get_width() + 18

        ayuda = ("ESPACIO pausa  |  R reiniciar  |  T trayectorias  |  E estelas  |  "
                 "↑/↓ tráfico  |  +/- velocidad  |  F11 pantalla completa  |  ESC salir")
        lienzo.blit(FUENTE_PEQUENA.render(ayuda, True, (225, 228, 220)), (16, ALTO_VIRTUAL - 25))
        fps = FUENTE_PEQUENA.render(f"FPS {self.fps_mostrados}", True, VERDE if self.fps_mostrados >= 55 else AMARILLO)
        lienzo.blit(fps, (ANCHO_VIRTUAL - fps.get_width() - 14, ALTO_VIRTUAL - 25))

    def semaforo_color(self):
        e = self.semaforo.estado
        if e.endswith("VERDE"):
            return VERDE
        if e.endswith("AMARILLO"):
            return AMARILLO
        return ROJO

    # --- render completo ---------------------------------------------------
    def renderizar(self, lienzo):
        lienzo.blit(self._fondo, (0, 0))
        if self.mostrar_rutas:
            lienzo.blit(self._overlay_rutas, (0, 0))
        if self.mostrar_estelas:
            for v in self.vehiculos:
                n = len(v.estela)
                if n < 2:
                    continue
                pts = list(v.estela)
                for i in range(1, n):
                    k = i / n
                    col = tuple(int(CALLE[j] + (v.color[j] - CALLE[j]) * k * 0.9) for j in range(3))
                    pygame.draw.line(lienzo, col, pts[i - 1], pts[i], 3)
        for v in self.vehiculos:
            v.dibujar_sombra(lienzo)
        for v in self.vehiculos:
            v.dibujar(lienzo)
        self.semaforo.dibujar(lienzo)
        self.dibujar_hud(lienzo)

    def presentar(self):
        ancho_win, alto_win = PANTALLA_REAL.get_size()
        escala = min(ancho_win / ANCHO_VIRTUAL, alto_win / ALTO_VIRTUAL)
        w, h = max(1, int(ANCHO_VIRTUAL * escala)), max(1, int(ALTO_VIRTUAL * escala))
        PANTALLA_REAL.fill((10, 12, 14))
        if (w, h) == (ANCHO_VIRTUAL, ALTO_VIRTUAL):
            PANTALLA_REAL.blit(CANVAS_VIRTUAL, ((ancho_win - w) // 2, (alto_win - h) // 2))
        else:
            if self._escalado is None or self._escalado.get_size() != (w, h):
                self._escalado = pygame.Surface((w, h))
            pygame.transform.smoothscale(CANVAS_VIRTUAL, (w, h), self._escalado)
            PANTALLA_REAL.blit(self._escalado, ((ancho_win - w) // 2, (alto_win - h) // 2))
        pygame.display.flip()

    # --- entrada -----------------------------------------------------------
    def _tecla(self, k):
        if k == pygame.K_ESCAPE:
            self.ejecutando = False
        elif k == pygame.K_SPACE:
            self.pausado = not self.pausado
        elif k == pygame.K_r:
            self._reiniciar()
        elif k == pygame.K_t:
            self.mostrar_rutas = not self.mostrar_rutas
        elif k == pygame.K_e:
            self.mostrar_estelas = not self.mostrar_estelas
        elif k == pygame.K_UP:
            self.intervalo = max(0.35, self.intervalo - 0.15)
        elif k == pygame.K_DOWN:
            self.intervalo = min(3.0, self.intervalo + 0.15)
        elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.idx_escala = min(len(ESCALAS_TIEMPO) - 1, self.idx_escala + 1)
        elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.idx_escala = max(0, self.idx_escala - 1)
        elif k == pygame.K_F11:
            try:
                pygame.display.toggle_fullscreen()
            except pygame.error:
                pass

    def ejecutar(self):
        while self.ejecutando:
            dt_real = min(RELOJ.tick(FPS_OBJETIVO) / 1000.0, 0.05)
            self.fps_mostrados = int(RELOJ.get_fps())

            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    self.ejecutando = False
                elif evento.type == pygame.KEYDOWN:
                    self._tecla(evento.key)

            if not self.pausado:
                dt = dt_real * ESCALAS_TIEMPO[self.idx_escala]
                pasos = max(1, math.ceil(dt / (1 / 90)))
                for _ in range(pasos):
                    self.actualizar(dt / pasos)

            self.renderizar(CANVAS_VIRTUAL)
            self.presentar()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Simulador().ejecutar()

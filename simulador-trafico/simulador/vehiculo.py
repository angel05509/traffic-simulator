"""Vehículo: movimiento sobre su ruta, distancia de seguridad, reserva del cruce y estadísticas."""
import math
import random
from collections import deque

import pygame

from .config import *
from .geometria import RUTAS, en_conflicto
from .sprites import sprite_coche


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

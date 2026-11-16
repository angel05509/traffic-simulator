"""Motor de la simulación: generación de tráfico, estadísticas y series para las gráficas."""
import random
from datetime import datetime

import pygame

from .config import *
from .escenario import recurso_fondo, recurso_hud, recurso_rutas
from .semaforo import Semaforo
from .ui import F_HUD, F_PEQ, texto
from .vehiculo import Vehiculo


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

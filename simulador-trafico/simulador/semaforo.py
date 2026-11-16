"""Semáforo de dos fases (eje H y eje V) con amarillo y todo rojo."""
import pygame

from .config import *


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

"""
Simulador de Tráfico - Fase 5 (Versión Responsiva Sin Colisiones)
Novedades:
- Soporte para cambio de tamaño de ventana (RESIZABLE) y pantalla completa.
- Renderizado adaptativo mediante superficie virtual (mantiene aspect ratio).
- Eliminación total de traslapes mediante Hitbox interactivo.
- Prevención de bloqueos en cruce (Gridlock Prevention).

Requisitos: pip install pygame
"""

import math
import random
import sys
import pygame

# Configuración virtual fija (Resolución lógica interna)
ANCHO_VIRTUAL, ALTO_VIRTUAL = 1000, 700
FPS_OBJETIVO = 120
TITULO = "Simulador de Tráfico - Fase 5 (Responsivo)"

CENTRO_X, CENTRO_Y = ANCHO_VIRTUAL // 2, ALTO_VIRTUAL // 2
ANCHO_CALLE = 180

# Coordenadas clave de la intersección
X_IZQ = CENTRO_X - ANCHO_CALLE // 2
X_DER = CENTRO_X + ANCHO_CALLE // 2
Y_ARRIBA = CENTRO_Y - ANCHO_CALLE // 2
Y_ABAJO = CENTRO_Y + ANCHO_CALLE // 2

# Área delimitadora del centro del cruce
CRUCE_RECT = pygame.Rect(X_IZQ, Y_ARRIBA, ANCHO_CALLE, ANCHO_CALLE)

pygame.init()
pygame.display.set_caption(TITULO)

# Ventana física inicial con bandera RESIZABLE
PANTALLA_REAL = pygame.display.set_mode((ANCHO_VIRTUAL, ALTO_VIRTUAL), pygame.RESIZABLE | pygame.DOUBLEBUF)
# Lienzo virtual donde se dibuja la lógica del juego
CANVAS_VIRTUAL = pygame.Surface((ANCHO_VIRTUAL, ALTO_VIRTUAL))

RELOJ = pygame.time.Clock()
FUENTE = pygame.font.SysFont("segoeui", 18)
FUENTE_PEQUENA = pygame.font.SysFont("segoeui", 14)
FUENTE_TITULO = pygame.font.SysFont("segoeui", 22, bold=True)

# Paleta de colores
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


class Semaforo:
    def __init__(self, verde=10.0, amarillo=2.5):
        self.verde = verde
        self.amarillo = amarillo
        self.estado = "H_VERDE"
        self.t = 0.0

    def actualizar(self, dt):
        self.t += dt
        limite = self.verde if "VERDE" in self.estado else self.amarillo
        if self.t >= limite:
            self.t = 0.0
            self.estado = {
                "H_VERDE": "H_AMARILLO",
                "H_AMARILLO": "V_VERDE",
                "V_VERDE": "V_AMARILLO",
                "V_AMARILLO": "H_VERDE",
            }[self.estado]

    def luz(self, eje):
        if eje == "H":
            return "VERDE" if self.estado == "H_VERDE" else "AMARILLO" if self.estado == "H_AMARILLO" else "ROJO"
        return "VERDE" if self.estado == "V_VERDE" else "AMARILLO" if self.estado == "V_AMARILLO" else "ROJO"

    def dibujar(self, pantalla):
        posiciones = [
            (X_IZQ - 42, Y_ARRIBA - 57, "H"),
            (X_DER + 18, Y_ARRIBA - 57, "V"),
            (X_IZQ - 42, Y_ABAJO + 8, "V"),
            (X_DER + 18, Y_ABAJO + 8, "H"),
        ]
        for x, y, eje in posiciones:
            pygame.draw.rect(pantalla, (17, 19, 21), (x, y, 25, 62), border_radius=7)
            luz = self.luz(eje)
            for i, nombre in enumerate(("ROJO", "AMARILLO", "VERDE")):
                color = {"ROJO": ROJO, "AMARILLO": AMARILLO, "VERDE": VERDE}[nombre] if luz == nombre else APAGADO
                pygame.draw.circle(pantalla, color, (x + 12, y + 11 + i * 20), 7)


class Vehiculo:
    LARGO = 42
    ANCHO = 23

    def __init__(self, origen, posicion=None):
        self.origen = origen
        self.orientacion = origen
        self.velocidad_base = random.uniform(110, 145)
        self.velocidad = self.velocidad_base
        self.color = random.choice(COLORES_H if origen in ("DERECHA", "IZQUIERDA") else COLORES_V)
        self.intencion = random.choices(["FRENTE", "DERECHA", "IZQUIERDA"], [0.60, 0.20, 0.20])[0]
        self.ha_girado = False
        self.tick = random.random() * 2
        self.rect = pygame.Rect(0, 0, self.LARGO, self.ANCHO)
        self._poner_en_origen(posicion)

    def _poner_en_origen(self, posicion=None):
        if self.origen == "DERECHA":    # De oeste a este
            self.orientacion = "DERECHA"
            self.rect.size = (self.LARGO, self.ANCHO)
            self.rect.left = -self.LARGO - 10 if posicion is None else posicion
            self.rect.centery = CENTRO_Y + 43
        elif self.origen == "IZQUIERDA":  # De este a oeste
            self.orientacion = "IZQUIERDA"
            self.rect.size = (self.LARGO, self.ANCHO)
            self.rect.left = ANCHO_VIRTUAL + 10 if posicion is None else posicion
            self.rect.centery = CENTRO_Y - 43
        elif self.origen == "ABAJO":     # De norte a sur
            self.orientacion = "ABAJO"
            self.rect.size = (self.ANCHO, self.LARGO)
            self.rect.centerx = CENTRO_X - 43
            self.rect.top = -self.LARGO - 10 if posicion is None else posicion
        else:                            # De sur a norte
            self.orientacion = "ARRIBA"
            self.rect.size = (self.ANCHO, self.LARGO)
            self.rect.centerx = CENTRO_X + 43
            self.rect.top = ALTO_VIRTUAL + 10 if posicion is None else posicion

    def _eje(self):
        return "H" if self.orientacion in ("DERECHA", "IZQUIERDA") else "V"

    def _distancia_parada(self):
        if self.orientacion == "DERECHA":
            return X_IZQ - self.rect.right
        if self.orientacion == "IZQUIERDA":
            return self.rect.left - X_DER
        if self.orientacion == "ABAJO":
            return Y_ARRIBA - self.rect.bottom
        return self.rect.top - Y_ABAJO

    def _debe_parar_por_semaforo(self, semaforo):
        if self.ha_girado or CRUCE_RECT.colliderect(self.rect):
            return False

        luz = semaforo.luz(self._eje())
        d = self._distancia_parada()

        if luz in ("ROJO", "AMARILLO") and -5 <= d <= 95:
            return True
        return False

    def _coche_bloqueando_cruce(self, todos):
        if CRUCE_RECT.colliderect(self.rect) or self.ha_girado:
            return False

        d = self._distancia_parada()
        if d > 35 or d < -10:
            return False

        for otro in todos:
            if otro is self:
                continue
            if CRUCE_RECT.colliderect(otro.rect):
                if otro._eje() != self._eje():
                    return True
                if otro.velocidad < 20:
                    return True
        return False

    def _cambiar(self, orientacion, centerx, centery):
        self.orientacion = orientacion
        if orientacion in ("DERECHA", "IZQUIERDA"):
            self.rect.size = (self.LARGO, self.ANCHO)
        else:
            self.rect.size = (self.ANCHO, self.LARGO)
        self.rect.center = (centerx, centery)
        self.ha_girado = True

    def _evaluar_giro(self):
        if self.ha_girado or self.intencion == "FRENTE":
            return

        if self.orientacion == "DERECHA" and self.rect.centerx >= CENTRO_X - 10:
            if self.intencion == "DERECHA":
                self._cambiar("ABAJO", CENTRO_X - 43, Y_ABAJO + 25)
            else:
                self._cambiar("ARRIBA", CENTRO_X + 43, Y_ARRIBA - 25)

        elif self.orientacion == "IZQUIERDA" and self.rect.centerx <= CENTRO_X + 10:
            if self.intencion == "DERECHA":
                self._cambiar("ARRIBA", CENTRO_X + 43, Y_ARRIBA - 25)
            else:
                self._cambiar("ABAJO", CENTRO_X - 43, Y_ABAJO + 25)

        elif self.orientacion == "ABAJO" and self.rect.centery >= CENTRO_Y - 10:
            if self.intencion == "DERECHA":
                self._cambiar("IZQUIERDA", X_IZQ - 25, CENTRO_Y - 43)
            else:
                self._cambiar("DERECHA", X_DER + 25, CENTRO_Y + 43)

        elif self.orientacion == "ARRIBA" and self.rect.centery <= CENTRO_Y + 10:
            if self.intencion == "DERECHA":
                self._cambiar("DERECHA", X_DER + 25, CENTRO_Y + 43)
            else:
                self._cambiar("IZQUIERDA", X_IZQ - 25, CENTRO_Y - 43)

    def actualizar(self, dt, semaforo, todos):
        self.tick += dt
        self.velocidad = self.velocidad_base

        # 1. Distancia de seguridad
        dist_minima = 9999
        for otro in todos:
            if otro is self or otro.orientacion != self.orientacion:
                continue
            gap = 9999
            if self.orientacion == "DERECHA" and abs(otro.rect.centery - self.rect.centery) < 20 and otro.rect.left >= self.rect.right:
                gap = otro.rect.left - self.rect.right
            elif self.orientacion == "IZQUIERDA" and abs(otro.rect.centery - self.rect.centery) < 20 and otro.rect.right <= self.rect.left:
                gap = self.rect.left - otro.rect.right
            elif self.orientacion == "ABAJO" and abs(otro.rect.centerx - self.rect.centerx) < 20 and otro.rect.top >= self.rect.bottom:
                gap = otro.rect.top - self.rect.bottom
            elif self.orientacion == "ARRIBA" and abs(otro.rect.centerx - self.rect.centerx) < 20 and otro.rect.bottom <= self.rect.top:
                gap = self.rect.top - otro.rect.bottom

            if gap < dist_minima:
                dist_minima = gap

        if dist_minima < 50:
            self.velocidad = min(self.velocidad, max(0.0, (dist_minima - 12) * 3.5))

        # 2. Detención semáforo / antibloqueo
        if self._debe_parar_por_semaforo(semaforo) or self._coche_bloqueando_cruce(todos):
            d = self._distancia_parada()
            if d <= 3:
                self.velocidad = 0
            else:
                self.velocidad = min(self.velocidad, max(0.0, d * 3.0))

        if self.velocidad <= 0.1:
            self.velocidad = 0
            return

        # 3. Movimiento y Hitbox futura
        self._evaluar_giro()
        paso = self.velocidad * dt

        futuro_rect = self.rect.copy()
        if self.orientacion == "DERECHA":
            futuro_rect.x += math.ceil(paso) + 3
        elif self.orientacion == "IZQUIERDA":
            futuro_rect.x -= math.ceil(paso) + 3
        elif self.orientacion == "ABAJO":
            futuro_rect.y += math.ceil(paso) + 3
        elif self.orientacion == "ARRIBA":
            futuro_rect.y -= math.ceil(paso) + 3

        for otro in todos:
            if otro is not self and futuro_rect.colliderect(otro.rect):
                self.velocidad = 0
                return

        if self.orientacion == "DERECHA":
            self.rect.x += paso
        elif self.orientacion == "IZQUIERDA":
            self.rect.x -= paso
        elif self.orientacion == "ABAJO":
            self.rect.y += paso
        elif self.orientacion == "ARRIBA":
            self.rect.y -= paso

    def fuera_pantalla(self):
        return (self.rect.left > ANCHO_VIRTUAL + 80 or self.rect.right < -80 or
                self.rect.top > ALTO_VIRTUAL + 80 or self.rect.bottom < -80)

    def dibujar(self, pantalla):
        r = self.rect
        pygame.draw.rect(pantalla, (15, 17, 19), r.move(2, 4), border_radius=6)
        pygame.draw.rect(pantalla, self.color, r, border_radius=6)
        pygame.draw.rect(pantalla, tuple(max(0, c - 35) for c in self.color), r, 2, border_radius=6)

        if self.orientacion in ("DERECHA", "IZQUIERDA"):
            ventana = pygame.Rect(r.x + r.width * 0.30, r.y + 4, r.width * 0.38, r.height - 8)
            pygame.draw.rect(pantalla, (28, 43, 54), ventana, border_radius=4)
            pygame.draw.line(pantalla, (112, 145, 158), (ventana.x + 4, ventana.y + 2),
                             (ventana.right - 4, ventana.bottom - 2), 1)
            if self.orientacion == "DERECHA":
                pygame.draw.circle(pantalla, (255, 244, 190), (r.right - 4, r.top + 5), 2)
                pygame.draw.circle(pantalla, (255, 244, 190), (r.right - 4, r.bottom - 5), 2)
                pygame.draw.circle(pantalla, (255, 55, 55), (r.left + 3, r.top + 5), 2)
                pygame.draw.circle(pantalla, (255, 55, 55), (r.left + 3, r.bottom - 5), 2)
            else:
                pygame.draw.circle(pantalla, (255, 244, 190), (r.left + 4, r.top + 5), 2)
                pygame.draw.circle(pantalla, (255, 244, 190), (r.left + 4, r.bottom - 5), 2)
                pygame.draw.circle(pantalla, (255, 55, 55), (r.right - 3, r.top + 5), 2)
                pygame.draw.circle(pantalla, (255, 55, 55), (r.right - 3, r.bottom - 5), 2)
        else:
            ventana = pygame.Rect(r.x + 4, r.y + r.height * 0.30, r.width - 8, r.height * 0.38)
            pygame.draw.rect(pantalla, (28, 43, 54), ventana, border_radius=4)
            if self.orientacion == "ABAJO":
                pygame.draw.circle(pantalla, (255, 244, 190), (r.left + 5, r.bottom - 4), 2)
                pygame.draw.circle(pantalla, (255, 244, 190), (r.right - 5, r.bottom - 4), 2)
            else:
                pygame.draw.circle(pantalla, (255, 244, 190), (r.left + 5, r.top + 4), 2)
                pygame.draw.circle(pantalla, (255, 244, 190), (r.right - 5, r.top + 4), 2)

        if not self.ha_girado and self.intencion != "FRENTE" and int(self.tick * 3.5) % 2 == 0:
            if self.orientacion == "DERECHA":
                p = (r.right - 5, r.bottom - 4) if self.intencion == "DERECHA" else (r.right - 5, r.top + 4)
            elif self.orientacion == "IZQUIERDA":
                p = (r.left + 5, r.top + 4) if self.intencion == "DERECHA" else (r.left + 5, r.bottom - 4)
            elif self.orientacion == "ABAJO":
                p = (r.right - 4, r.bottom - 6) if self.intencion == "DERECHA" else (r.left + 4, r.bottom - 6)
            else:
                p = (r.left + 4, r.top + 6) if self.intencion == "DERECHA" else (r.right - 4, r.top + 6)
            pygame.draw.circle(pantalla, AMARILLO, p, 3)


class Simulador:
    def __init__(self):
        self.semaforo = Semaforo()
        self.vehiculos = []
        self.ejecutando = True
        self.pausado = False
        self.generacion = 0.0
        self.intervalo_generacion = 1.3
        self.fps_mostrados = 0
        self._reiniciar_trafico()

    def _reiniciar_trafico(self):
        self.vehiculos.clear()
        for origen in ("DERECHA", "IZQUIERDA", "ABAJO", "ARRIBA"):
            for i in range(3):
                v = Vehiculo(origen)
                if origen == "DERECHA":
                    v.rect.left = -i * 100 - 50
                elif origen == "IZQUIERDA":
                    v.rect.left = ANCHO_VIRTUAL + i * 100
                elif origen == "ABAJO":
                    v.rect.top = -i * 100 - 50
                else:
                    v.rect.top = ALTO_VIRTUAL + i * 100
                self.vehiculos.append(v)

    def _crear_vehiculo(self, origen):
        for v in self.vehiculos:
            if v.origen != origen or v.ha_girado:
                continue
            if origen == "DERECHA" and v.rect.left < 75:
                return
            if origen == "IZQUIERDA" and v.rect.right > ANCHO_VIRTUAL - 75:
                return
            if origen == "ABAJO" and v.rect.top < 75:
                return
            if origen == "ARRIBA" and v.rect.bottom > ALTO_VIRTUAL - 75:
                return
        self.vehiculos.append(Vehiculo(origen))

    def dibujar_mapa(self, lienzo):
        lienzo.fill(GRAMA)
        for x in range(20, ANCHO_VIRTUAL, 90):
            for y in range(18, ALTO_VIRTUAL, 85):
                pygame.draw.circle(lienzo, (38, 64, 52), (x + (y % 17), y), 2)

        pygame.draw.rect(lienzo, BORDE, (0, Y_ARRIBA - 4, ANCHO_VIRTUAL, ANCHO_CALLE + 8))
        pygame.draw.rect(lienzo, BORDE, (X_IZQ - 4, 0, ANCHO_CALLE + 8, ALTO_VIRTUAL))
        pygame.draw.rect(lienzo, CALLE, (0, Y_ARRIBA, ANCHO_VIRTUAL, ANCHO_CALLE))
        pygame.draw.rect(lienzo, CALLE, (X_IZQ, 0, ANCHO_CALLE, ALTO_VIRTUAL))

        for x in range(0, ANCHO_VIRTUAL, 38):
            if not X_IZQ - 5 <= x <= X_DER:
                pygame.draw.line(lienzo, LINEA, (x, CENTRO_Y), (x + 20, CENTRO_Y), 2)
        for y in range(0, ALTO_VIRTUAL, 38):
            if not Y_ARRIBA - 5 <= y <= Y_ABAJO:
                pygame.draw.line(lienzo, LINEA, (CENTRO_X, y), (CENTRO_X, y + 20), 2)

        pygame.draw.line(lienzo, (90, 94, 98), (0, CENTRO_Y - 1), (X_IZQ, CENTRO_Y - 1), 1)
        pygame.draw.line(lienzo, (90, 94, 98), (X_DER, CENTRO_Y + 1), (ANCHO_VIRTUAL, CENTRO_Y + 1), 1)
        pygame.draw.line(lienzo, (90, 94, 98), (CENTRO_X - 1, 0), (CENTRO_X - 1, Y_ARRIBA), 1)
        pygame.draw.line(lienzo, (90, 94, 98), (CENTRO_X + 1, Y_ABAJO), (CENTRO_X + 1, ALTO_VIRTUAL), 1)

        for i in range(7):
            xx = X_IZQ + 8 + i * 23
            pygame.draw.rect(lienzo, (185, 187, 182), (xx, Y_ARRIBA - 19, 13, 13))
            pygame.draw.rect(lienzo, (185, 187, 182), (xx, Y_ABAJO + 6, 13, 13))
            yy = Y_ARRIBA + 8 + i * 23
            pygame.draw.rect(lienzo, (185, 187, 182), (X_IZQ - 19, yy, 13, 13))
            pygame.draw.rect(lienzo, (185, 187, 182), (X_DER + 6, yy, 13, 13))

    def dibujar_hud(self, lienzo):
        panel = pygame.Surface((ANCHO_VIRTUAL, 44), pygame.SRCALPHA)
        panel.fill((13, 17, 20, 215))
        lienzo.blit(panel, (0, 0))
        estado = "PAUSADO" if self.pausado else "EN MARCHA"
        color_estado = AMARILLO if self.pausado else VERDE
        lienzo.blit(FUENTE_TITULO.render("TRÁFICO URBANO", True, BLANCO), (16, 9))
        lienzo.blit(FUENTE.render(f"Vehículos: {len(self.vehiculos)}", True, BLANCO), (235, 12))
        lienzo.blit(FUENTE.render(f"FPS: {self.fps_mostrados}", True,
                    VERDE if self.fps_mostrados >= 55 else AMARILLO), (385, 12))
        lienzo.blit(FUENTE.render(f"Semáforo: {self.semaforo.estado.replace('_', ' ')}", True, BLANCO), (485, 12))
        lienzo.blit(FUENTE.render(estado, True, color_estado), (790, 12))
        ayuda = "ESPACIO: pausar  |  R: reiniciar tráfico  |  ESC: salir"
        lienzo.blit(FUENTE_PEQUENA.render(ayuda, True, (225, 228, 220)), (16, ALTO_VIRTUAL - 25))

    def actualizar(self, dt):
        self.semaforo.actualizar(dt)
        self.generacion += dt
        if self.generacion >= self.intervalo_generacion:
            self.generacion = 0.0
            self._crear_vehiculo(random.choice(("DERECHA", "IZQUIERDA", "ABAJO", "ARRIBA")))

        for v in sorted(self.vehiculos, key=lambda x: (x.orientacion, x.rect.x, x.rect.y)):
            v.actualizar(dt, self.semaforo, self.vehiculos)

        self.vehiculos = [v for v in self.vehiculos if not v.fuera_pantalla()]

    def ejecutar(self):
        while self.ejecutando:
            dt = min(RELOJ.tick(FPS_OBJETIVO) / 1000.0, 0.033)
            self.fps_mostrados = int(RELOJ.get_fps())

            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    self.ejecutando = False
                elif evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_ESCAPE:
                        self.ejecutando = False
                    elif evento.key == pygame.K_SPACE:
                        self.pausado = not self.pausado
                    elif evento.key == pygame.K_r:
                        self._reiniciar_trafico()

            if not self.pausado:
                self.actualizar(dt)

            # 1. Dibujar todo el contenido en el lienzo virtual
            self.dibujar_mapa(CANVAS_VIRTUAL)
            self.semaforo.dibujar(CANVAS_VIRTUAL)
            for vehiculo in self.vehiculos:
                vehiculo.dibujar(CANVAS_VIRTUAL)
            self.dibujar_hud(CANVAS_VIRTUAL)

            # 2. Calcular el escalado responsivo manteniendo el aspect ratio en la ventana real
            ancho_win, alto_win = PANTALLA_REAL.get_size()
            escala = min(ancho_win / ANCHO_VIRTUAL, alto_win / ALTO_VIRTUAL)
            ancho_escalado = int(ANCHO_VIRTUAL * escala)
            alto_escalado = int(ALTO_VIRTUAL * escala)

            # Centrar el lienzo escalado en la pantalla
            off_x = (ancho_win - ancho_escalado) // 2
            off_y = (alto_win - alto_escalado) // 2

            canvas_escalado = pygame.transform.smoothscale(CANVAS_VIRTUAL, (ancho_escalado, alto_escalado))

            PANTALLA_REAL.fill((10, 12, 14))  # Barras negras/fondo lateral
            PANTALLA_REAL.blit(canvas_escalado, (off_x, off_y))

            pygame.display.flip()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Simulador().ejecutar()

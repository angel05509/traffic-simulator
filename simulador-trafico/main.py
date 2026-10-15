"""
Simulador de Tráfico - Fase 4: Giro en Intersecciones
=====================================================
Novedades:
    - Respeto de Carril: Los vehículos circulan por la derecha.
    - Direcciones/Giros: Capacidad de girar a la DERECHA, IZQUIERDA o continuar FRENTE.
    - Luces Direccionales: Indicadores visuales intermitentes al aproximarse al cruce.
"""

import random
import sys
import pygame


# ──────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────
ANCHO, ALTO = 900, 600
FPS = 60
TITULO = "Simulador de Tráfico - Fase 4: Giros y Direccionales"


class Paleta:
    """Colores del sistema (modo oscuro)."""

    FONDO = (28, 28, 30)          # systemGray6
    CALLE = (44, 44, 46)          # systemGray5
    BORDE_CALLE = (58, 58, 60)    # systemGray4
    LINEA_CARRIL = (99, 99, 102)  # systemGray2

    # Colores para vehículos
    AUTO_HORIZONTAL = (100, 210, 255)  # systemTeal
    AUTO_VERTICAL = (255, 149, 0)      # systemOrange
    AUTO_SOMBRA = (0, 0, 0)

    # Semáforos e Luces
    SEMAFORO_CAJA = (20, 20, 22)
    LUZ_VERDE = (48, 209, 88)
    LUZ_AMARILLA = (255, 214, 10)
    LUZ_ROJA = (255, 69, 58)
    LUZ_APAGADA = (50, 50, 50)
    LUZ_DIRECCIONAL = (255, 204, 0)


class ConfigCalle:
    ANCHO_CALLE = 100
    GROSOR_BORDE = 2
    LARGO_RAYA = 20
    SEPARACION_RAYA = 16
    GROSOR_RAYA = 4

    X_CENTRO = (ANCHO - ANCHO_CALLE) // 2  # 350
    Y_CENTRO = (ALTO - ANCHO_CALLE) // 2   # 250


class ConfigAuto:
    ANCHO = 40
    ALTO = 20
    RADIO_ESQUINA = 5


# ──────────────────────────────────────────────
# Entidades
# ──────────────────────────────────────────────
class Semaforo:
    """Controlador de tiempo para los semáforos del cruce."""

    def __init__(self, tiempo_verde=240, tiempo_amarillo=60):
        self.tiempo_verde = tiempo_verde
        self.tiempo_amarillo = tiempo_amarillo
        self.cronometro = 0
        self.estado = "HORIZONTAL_VERDE"

    def actualizar(self):
        self.cronometro += 1

        if self.estado == "HORIZONTAL_VERDE":
            if self.cronometro >= self.tiempo_verde:
                self.estado = "HORIZONTAL_AMARILLO"
                self.cronometro = 0

        elif self.estado == "HORIZONTAL_AMARILLO":
            if self.cronometro >= self.tiempo_amarillo:
                self.estado = "VERTICAL_VERDE"
                self.cronometro = 0

        elif self.estado == "VERTICAL_VERDE":
            if self.cronometro >= self.tiempo_verde:
                self.estado = "VERTICAL_AMARILLO"
                self.cronometro = 0

        elif self.estado == "VERTICAL_AMARILLO":
            if self.cronometro >= self.tiempo_amarillo:
                self.estado = "HORIZONTAL_VERDE"
                self.cronometro = 0

    def obtener_luz(self, eje):
        if eje == "H":
            if self.estado == "HORIZONTAL_VERDE":
                return "VERDE"
            elif self.estado == "HORIZONTAL_AMARILLO":
                return "AMARILLO"
            else:
                return "ROJO"
        else:
            if self.estado == "VERTICAL_VERDE":
                return "VERDE"
            elif self.estado == "VERTICAL_AMARILLO":
                return "AMARILLO"
            else:
                return "ROJO"

    def dibujar(self, pantalla):
        x_c = ConfigCalle.X_CENTRO
        y_c = ConfigCalle.Y_CENTRO
        w_c = ConfigCalle.ANCHO_CALLE

        posiciones = [
            (x_c - 25, y_c - 55, "H"),
            (x_c + w_c + 5, y_c - 55, "V"),
            (x_c - 25, y_c + w_c + 5, "V"),
            (x_c + w_c + 5, y_c + w_c + 5, "H")
        ]

        for x, y, eje in posiciones:
            pygame.draw.rect(pantalla, Paleta.SEMAFORO_CAJA, (x, y, 20, 50), border_radius=4)
            luz = self.obtener_luz(eje)

            c_rojo = Paleta.LUZ_ROJA if luz == "ROJO" else Paleta.LUZ_APAGADA
            c_amarillo = Paleta.LUZ_AMARILLA if luz == "AMARILLO" else Paleta.LUZ_APAGADA
            c_verde = Paleta.LUZ_VERDE if luz == "VERDE" else Paleta.LUZ_APAGADA

            pygame.draw.circle(pantalla, c_rojo, (x + 10, y + 10), 6)
            pygame.draw.circle(pantalla, c_amarillo, (x + 10, y + 25), 6)
            pygame.draw.circle(pantalla, c_verde, (x + 10, y + 40), 6)


class Vehiculo:
    """Vehículo con lógica de navegación por carriles y giros en la intersección."""

    def __init__(self, origen, velocidad=2.0, color=Paleta.AUTO_HORIZONTAL):
        self.origen = origen  # "DERECHA", "IZQUIERDA", "ARRIBA", "ABAJO"
        self.orientacion = origen
        self.velocidad = velocidad
        self.color = color

        # Elección aleatoria de giro en la intersección
        self.intencion_giro = random.choice(["FRENTE", "DERECHA", "IZQUIERDA"])
        self.ha_girado = False
        self.parpadeo_tick = 0

        self.rect = pygame.Rect(0, 0, ConfigAuto.ANCHO, ConfigAuto.ALTO)
        self._posicionar_en_origen()

    def _posicionar_en_origen(self):
        """Asigna la posición inicial respetando el carril de la derecha."""
        x_c = ConfigCalle.X_CENTRO
        y_c = ConfigCalle.Y_CENTRO
        w_c = ConfigCalle.ANCHO_CALLE

        if self.origen == "DERECHA":  # Viene desde la izquierda avanzando a la derecha
            self.rect.width, self.rect.height = ConfigAuto.ANCHO, ConfigAuto.ALTO
            self.rect.x = -ConfigAuto.ANCHO
            self.rect.y = y_c + (w_c * 0.75) - (ConfigAuto.ALTO // 2)

        elif self.origen == "IZQUIERDA":  # Viene desde la derecha avanzando a la izquierda
            self.rect.width, self.rect.height = ConfigAuto.ANCHO, ConfigAuto.ALTO
            self.rect.x = ANCHO + ConfigAuto.ANCHO
            self.rect.y = y_c + (w_c * 0.25) - (ConfigAuto.ALTO // 2)

        elif self.origen == "ABAJO":  # Viene desde arriba avanzando hacia abajo
            self.rect.width, self.rect.height = ConfigAuto.ALTO, ConfigAuto.ANCHO
            self.rect.x = x_c + (w_c * 0.25) - (ConfigAuto.ALTO // 2)
            self.rect.y = -ConfigAuto.ANCHO

        elif self.origen == "ARRIBA":  # Viene desde abajo avanzando hacia arriba
            self.rect.width, self.rect.height = ConfigAuto.ALTO, ConfigAuto.ANCHO
            self.rect.x = x_c + (w_c * 0.75) - (ConfigAuto.ALTO // 2)
            self.rect.y = ALTO + ConfigAuto.ANCHO

    def _debe_frenar(self, semaforo):
        if self.ha_girado:
            return False

        x_c = ConfigCalle.X_CENTRO
        y_c = ConfigCalle.Y_CENTRO
        w_c = ConfigCalle.ANCHO_CALLE
        margen = 15

        if self.orientacion == "DERECHA":
            if semaforo.obtener_luz("H") in ("ROJO", "AMARILLO"):
                if x_c - margen <= self.rect.right <= x_c:
                    return True

        elif self.orientacion == "IZQUIERDA":
            if semaforo.obtener_luz("H") in ("ROJO", "AMARILLO"):
                if x_c + w_c <= self.rect.left <= x_c + w_c + margen:
                    return True

        elif self.orientacion == "ABAJO":
            if semaforo.obtener_luz("V") in ("ROJO", "AMARILLO"):
                if y_c - margen <= self.rect.bottom <= y_c:
                    return True

        elif self.orientacion == "ARRIBA":
            if semaforo.obtener_luz("V") in ("ROJO", "AMARILLO"):
                if y_c + w_c <= self.rect.top <= y_c + w_c + margen:
                    return True

        return False

    def _evaluar_giro(self):
        """Ejecuta la rotación y realineación al carril correspondiente."""
        if self.ha_girado or self.intencion_giro == "FRENTE":
            return

        x_c = ConfigCalle.X_CENTRO
        y_c = ConfigCalle.Y_CENTRO
        w_c = ConfigCalle.ANCHO_CALLE

        # Puntos de maniobra en la intersección según intención
        if self.orientacion == "DERECHA":
            if self.intencion_giro == "DERECHA" and self.rect.right >= x_c + (w_c * 0.25):
                self._cambiar_orientacion("ABAJO", x_c + (w_c * 0.25) - (ConfigAuto.ALTO // 2), self.rect.y)
            elif self.intencion_giro == "IZQUIERDA" and self.rect.right >= x_c + (w_c * 0.75):
                self._cambiar_orientacion("ARRIBA", x_c + (w_c * 0.75) - (ConfigAuto.ALTO // 2), self.rect.y)

        elif self.orientacion == "IZQUIERDA":
            if self.intencion_giro == "DERECHA" and self.rect.left <= x_c + (w_c * 0.75):
                self._cambiar_orientacion("ARRIBA", x_c + (w_c * 0.75) - (ConfigAuto.ALTO // 2), self.rect.y)
            elif self.intencion_giro == "IZQUIERDA" and self.rect.left <= x_c + (w_c * 0.25):
                self._cambiar_orientacion("ABAJO", x_c + (w_c * 0.25) - (ConfigAuto.ALTO // 2), self.rect.y)

        elif self.orientacion == "ABAJO":
            if self.intencion_giro == "DERECHA" and self.rect.bottom >= y_c + (w_c * 0.25):
                self._cambiar_orientacion("IZQUIERDA", self.rect.x, y_c + (w_c * 0.25) - (ConfigAuto.ALTO // 2))
            elif self.intencion_giro == "IZQUIERDA" and self.rect.bottom >= y_c + (w_c * 0.75):
                self._cambiar_orientacion("DERECHA", self.rect.x, y_c + (w_c * 0.75) - (ConfigAuto.ALTO // 2))

        elif self.orientacion == "ARRIBA":
            if self.intencion_giro == "DERECHA" and self.rect.top <= y_c + (w_c * 0.75):
                self._cambiar_orientacion("DERECHA", self.rect.x, y_c + (w_c * 0.75) - (ConfigAuto.ALTO // 2))
            elif self.intencion_giro == "IZQUIERDA" and self.rect.top <= y_c + (w_c * 0.25):
                self._cambiar_orientacion("IZQUIERDA", self.rect.x, y_c + (w_c * 0.25) - (ConfigAuto.ALTO // 2))

    def _cambiar_orientacion(self, nueva_orientacion, nuevo_x, nuevo_y):
        self.orientacion = nueva_orientacion
        self.rect.width, self.rect.height = self.rect.height, self.rect.width
        self.rect.x = nuevo_x
        self.rect.y = nuevo_y
        self.ha_girado = True

    def actualizar(self, semaforo):
        self.parpadeo_tick += 1

        if self._debe_frenar(semaforo):
            return

        self._evaluar_giro()

        # Movimiento continuo
        if self.orientacion == "DERECHA":
            self.rect.x += self.velocidad
            if self.rect.left > ANCHO:
                self._reiniciar()

        elif self.orientacion == "IZQUIERDA":
            self.rect.x -= self.velocidad
            if self.rect.right < 0:
                self._reiniciar()

        elif self.orientacion == "ABAJO":
            self.rect.y += self.velocidad
            if self.rect.top > ALTO:
                self._reiniciar()

        elif self.orientacion == "ARRIBA":
            self.rect.y -= self.velocidad
            if self.rect.bottom < 0:
                self._reiniciar()

    def _reiniciar(self):
        self.orientacion = self.origen
        self.intencion_giro = random.choice(["FRENTE", "DERECHA", "IZQUIERDA"])
        self.ha_girado = False
        self._posicionar_en_origen()

    def dibujar(self, pantalla):
        # Sombra
        sombra = self.rect.move(0, 3)
        pygame.draw.rect(
            pantalla, Paleta.AUTO_SOMBRA, sombra,
            border_radius=ConfigAuto.RADIO_ESQUINA,
        )
        # Cuerpo
        pygame.draw.rect(
            pantalla, self.color, self.rect,
            border_radius=ConfigAuto.RADIO_ESQUINA,
        )

        # Luz direccional intermitente
        if not self.ha_girado and self.intencion_giro != "FRENTE":
            if (self.parpadeo_tick // 15) % 2 == 0:
                self._dibujar_direccional(pantalla)

    def _dibujar_direccional(self, pantalla):
        """Dibuja un destello amarillo en la esquina correspondiente del vehículo."""
        r = self.rect
        pos = None

        if self.orientacion == "DERECHA":
            pos = (r.right - 4, r.top + 3) if self.intencion_giro == "IZQUIERDA" else (r.right - 4, r.bottom - 3)
        elif self.orientacion == "IZQUIERDA":
            pos = (r.left + 4, r.bottom - 3) if self.intencion_giro == "IZQUIERDA" else (r.left + 4, r.top + 3)
        elif self.orientacion == "ABAJO":
            pos = (r.left + 3, r.bottom - 4) if self.intencion_giro == "IZQUIERDA" else (r.right - 3, r.bottom - 4)
        elif self.orientacion == "ARRIBA":
            pos = (r.right - 3, r.top + 4) if self.intencion_giro == "IZQUIERDA" else (r.left + 3, r.top + 4)

        if pos:
            pygame.draw.circle(pantalla, Paleta.LUZ_DIRECCIONAL, pos, 3)


class Interseccion:
    """Diseño y señalización de la calzada."""

    def __init__(self):
        self.rect_h = pygame.Rect(0, ConfigCalle.Y_CENTRO, ANCHO, ConfigCalle.ANCHO_CALLE)
        self.rect_v = pygame.Rect(ConfigCalle.X_CENTRO, 0, ConfigCalle.ANCHO_CALLE, ALTO)

    def dibujar(self, pantalla):
        pygame.draw.rect(pantalla, Paleta.CALLE, self.rect_h)
        pygame.draw.rect(pantalla, Paleta.CALLE, self.rect_v)

        self._dibujar_bordes(pantalla)
        self._dibujar_lineas_discontinuas(pantalla)
        self._dibujar_lineas_detencion(pantalla)

    def _dibujar_bordes(self, pantalla):
        g = ConfigCalle.GROSOR_BORDE
        x_c = ConfigCalle.X_CENTRO
        y_c = ConfigCalle.Y_CENTRO
        w_c = ConfigCalle.ANCHO_CALLE

        pygame.draw.rect(pantalla, Paleta.BORDE_CALLE, (0, y_c, x_c, g))
        pygame.draw.rect(pantalla, Paleta.BORDE_CALLE, (x_c + w_c, y_c, ANCHO - (x_c + w_c), g))
        pygame.draw.rect(pantalla, Paleta.BORDE_CALLE, (0, y_c + w_c - g, x_c, g))
        pygame.draw.rect(pantalla, Paleta.BORDE_CALLE, (x_c + w_c, y_c + w_c - g, ANCHO - (x_c + w_c), g))

        pygame.draw.rect(pantalla, Paleta.BORDE_CALLE, (x_c, 0, g, y_c))
        pygame.draw.rect(pantalla, Paleta.BORDE_CALLE, (x_c, y_c + w_c, g, ALTO - (y_c + w_c)))
        pygame.draw.rect(pantalla, Paleta.BORDE_CALLE, (x_c + w_c - g, 0, g, y_c))
        pygame.draw.rect(pantalla, Paleta.BORDE_CALLE, (x_c + w_c - g, y_c + w_c, g, ALTO - (y_c + w_c)))

    def _dibujar_lineas_discontinuas(self, pantalla):
        paso = ConfigCalle.LARGO_RAYA + ConfigCalle.SEPARACION_RAYA
        x_c = ConfigCalle.X_CENTRO
        y_c = ConfigCalle.Y_CENTRO
        w_c = ConfigCalle.ANCHO_CALLE

        y_h = y_c + w_c // 2 - ConfigCalle.GROSOR_RAYA // 2
        for x in range(0, ANCHO, paso):
            if x < x_c or x > x_c + w_c - ConfigCalle.LARGO_RAYA:
                pygame.draw.rect(
                    pantalla, Paleta.LINEA_CARRIL,
                    (x, y_h, ConfigCalle.LARGO_RAYA, ConfigCalle.GROSOR_RAYA),
                    border_radius=2,
                )

        x_v = x_c + w_c // 2 - ConfigCalle.GROSOR_RAYA // 2
        for y in range(0, ALTO, paso):
            if y < y_c or y > y_c + w_c - ConfigCalle.LARGO_RAYA:
                pygame.draw.rect(
                    pantalla, Paleta.LINEA_CARRIL,
                    (x_v, y, ConfigCalle.GROSOR_RAYA, ConfigCalle.LARGO_RAYA),
                    border_radius=2,
                )

    def _dibujar_lineas_detencion(self, pantalla):
        x_c = ConfigCalle.X_CENTRO
        y_c = ConfigCalle.Y_CENTRO
        w_c = ConfigCalle.ANCHO_CALLE
        g = 4

        pygame.draw.rect(pantalla, Paleta.LINEA_CARRIL, (x_c - g, y_c + w_c // 2, g, w_c // 2))
        pygame.draw.rect(pantalla, Paleta.LINEA_CARRIL, (x_c + w_c, y_c, g, w_c // 2))
        pygame.draw.rect(pantalla, Paleta.LINEA_CARRIL, (x_c, y_c - g, w_c // 2, g))
        pygame.draw.rect(pantalla, Paleta.LINEA_CARRIL, (x_c + w_c // 2, y_c + w_c, w_c // 2, g))


# ──────────────────────────────────────────────
# Simulador
# ──────────────────────────────────────────────
class Simulador:
    """Orquesta la ventana y el bucle principal."""

    def __init__(self):
        pygame.init()
        self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption(TITULO)
        self.reloj = pygame.time.Clock()
        self.ejecutando = True

        self.interseccion = Interseccion()
        self.semaforo = Semaforo(tiempo_verde=240, tiempo_amarillo=60)

        # Un vehículo generado para cada carril
        self.vehiculos = [
            Vehiculo(origen="DERECHA", velocidad=2.2, color=Paleta.AUTO_HORIZONTAL),
            Vehiculo(origen="IZQUIERDA", velocidad=2.0, color=Paleta.AUTO_HORIZONTAL),
            Vehiculo(origen="ABAJO", velocidad=2.1, color=Paleta.AUTO_VERTICAL),
            Vehiculo(origen="ARRIBA", velocidad=1.9, color=Paleta.AUTO_VERTICAL),
        ]

    def _manejar_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.ejecutando = False

    def _actualizar(self):
        self.semaforo.actualizar()
        for vehiculo in self.vehiculos:
            vehiculo.actualizar(self.semaforo)

    def _dibujar(self):
        self.pantalla.fill(Paleta.FONDO)
        self.interseccion.dibujar(self.pantalla)
        self.semaforo.dibujar(self.pantalla)
        for vehiculo in self.vehiculos:
            vehiculo.dibujar(self.pantalla)
        pygame.display.flip()

    def ejecutar(self):
        while self.ejecutando:
            self._manejar_eventos()
            self._actualizar()
            self._dibujar()
            self.reloj.tick(FPS)
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Simulador().ejecutar()

"""
Simulador de Tráfico - Fase 2: Intersección Vial
================================================
Novedades:
    - Carretera: Ahora dibuja una intersección en cruz (calle horizontal y vertical).
    - Vehiculo: Soporta movimiento en 4 direcciones (derecha, izquierda, abajo, arriba).
    - Múltiples Vehículos: Flujo vehicular en ambos ejes (horizontal y vertical).
"""

import sys
import pygame


# ──────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────
ANCHO, ALTO = 800, 600
FPS = 60
TITULO = "Simulador de Tráfico - Fase 2: Intersección"


class Paleta:
    """Colores del sistema (modo oscuro)."""

    FONDO = (28, 28, 30)          # systemGray6
    CALLE = (44, 44, 46)          # systemGray5
    BORDE_CALLE = (58, 58, 60)    # systemGray4
    LINEA_CARRIL = (99, 99, 102)  # systemGray2

    # Colores para vehículos según dirección o carril
    AUTO_HORIZONTAL = (100, 210, 255)  # systemTeal
    AUTO_VERTICAL = (255, 149, 0)      # systemOrange
    AUTO_SOMBRA = (0, 0, 0)


class ConfigCalle:
    ANCHO_CALLE = 100
    GROSOR_BORDE = 2
    LARGO_RAYA = 20
    SEPARACION_RAYA = 16
    GROSOR_RAYA = 4

    # Posiciones centradas para la intersección
    X_CENTRO = (ANCHO - ANCHO_CALLE) // 2  # 350
    Y_CENTRO = (ALTO - ANCHO_CALLE) // 2   # 250


class ConfigAuto:
    ANCHO = 40
    ALTO = 20
    RADIO_ESQUINA = 5


# ──────────────────────────────────────────────
# Entidades
# ──────────────────────────────────────────────
class Vehiculo:
    """Vehículo con capacidad de movimiento en cualquier dirección cardinal."""

    def __init__(self, x, y, velocidad, direccion="DERECHA", color=Paleta.AUTO_HORIZONTAL):
        self.direccion = direccion  # "DERECHA", "IZQUIERDA", "ABAJO", "ARRIBA"
        self.velocidad = velocidad
        self.color = color

        # Ajustar dimensiones del Rect según la orientación
        if self.direccion in ("DERECHA", "IZQUIERDA"):
            self.rect = pygame.Rect(x, y, ConfigAuto.ANCHO, ConfigAuto.ALTO)
        else:
            self.rect = pygame.Rect(x, y, ConfigAuto.ALTO, ConfigAuto.ANCHO)

    def actualizar(self):
        # Desplazamiento según dirección
        if self.direccion == "DERECHA":
            self.rect.x += self.velocidad
            if self.rect.left > ANCHO:
                self.rect.right = 0

        elif self.direccion == "IZQUIERDA":
            self.rect.x -= self.velocidad
            if self.rect.right < 0:
                self.rect.left = ANCHO

        elif self.direccion == "ABAJO":
            self.rect.y += self.velocidad
            if self.rect.top > ALTO:
                self.rect.bottom = 0

        elif self.direccion == "ARRIBA":
            self.rect.y -= self.velocidad
            if self.rect.bottom < 0:
                self.rect.top = ALTO

    def dibujar(self, pantalla):
        # Sombra suave
        sombra = self.rect.move(0, 3)
        pygame.draw.rect(
            pantalla, Paleta.AUTO_SOMBRA, sombra,
            border_radius=ConfigAuto.RADIO_ESQUINA,
        )
        pygame.draw.rect(
            pantalla, self.color, self.rect,
            border_radius=ConfigAuto.RADIO_ESQUINA,
        )


class Interseccion:
    """Representa el cruce de dos carreteras (horizontal y vertical)."""

    def __init__(self):
        self.rect_h = pygame.Rect(0, ConfigCalle.Y_CENTRO, ANCHO, ConfigCalle.ANCHO_CALLE)
        self.rect_v = pygame.Rect(ConfigCalle.X_CENTRO, 0, ConfigCalle.ANCHO_CALLE, ALTO)

    def dibujar(self, pantalla):
        # 1. Dibujar el asfalto de ambas calles
        pygame.draw.rect(pantalla, Paleta.CALLE, self.rect_h)
        pygame.draw.rect(pantalla, Paleta.CALLE, self.rect_v)

        # 2. Señalización y bordes
        self._dibujar_bordes(pantalla)
        self._dibujar_lineas_discontinuas(pantalla)

    def _dibujar_bordes(self, pantalla):
        g = ConfigCalle.GROSOR_BORDE
        x_c = ConfigCalle.X_CENTRO
        y_c = ConfigCalle.Y_CENTRO
        w_c = ConfigCalle.ANCHO_CALLE

        # Bordes de la calle horizontal (excluyendo el centro del cruce)
        pygame.draw.rect(pantalla, Paleta.BORDE_CALLE, (0, y_c, x_c, g))
        pygame.draw.rect(pantalla, Paleta.BORDE_CALLE, (x_c + w_c, y_c, ANCHO - (x_c + w_c), g))
        pygame.draw.rect(pantalla, Paleta.BORDE_CALLE, (0, y_c + w_c - g, x_c, g))
        pygame.draw.rect(pantalla, Paleta.BORDE_CALLE, (x_c + w_c, y_c + w_c - g, ANCHO - (x_c + w_c), g))

        # Bordes de la calle vertical (excluyendo el centro del cruce)
        pygame.draw.rect(pantalla, Paleta.BORDE_CALLE, (x_c, 0, g, y_c))
        pygame.draw.rect(pantalla, Paleta.BORDE_CALLE, (x_c, y_c + w_c, g, ALTO - (y_c + w_c)))
        pygame.draw.rect(pantalla, Paleta.BORDE_CALLE, (x_c + w_c - g, 0, g, y_c))
        pygame.draw.rect(pantalla, Paleta.BORDE_CALLE, (x_c + w_c - g, y_c + w_c, g, ALTO - (y_c + w_c)))

    def _dibujar_lineas_discontinuas(self, pantalla):
        paso = ConfigCalle.LARGO_RAYA + ConfigCalle.SEPARACION_RAYA
        x_c = ConfigCalle.X_CENTRO
        y_c = ConfigCalle.Y_CENTRO
        w_c = ConfigCalle.ANCHO_CALLE

        # Línea central horizontal
        y_h = y_c + w_c // 2 - ConfigCalle.GROSOR_RAYA // 2
        for x in range(0, ANCHO, paso):
            if x < x_c or x > x_c + w_c - ConfigCalle.LARGO_RAYA:
                pygame.draw.rect(
                    pantalla, Paleta.LINEA_CARRIL,
                    (x, y_h, ConfigCalle.LARGO_RAYA, ConfigCalle.GROSOR_RAYA),
                    border_radius=2,
                )

        # Línea central vertical
        x_v = x_c + w_c // 2 - ConfigCalle.GROSOR_RAYA // 2
        for y in range(0, ALTO, paso):
            if y < y_c or y > y_c + w_c - ConfigCalle.LARGO_RAYA:
                pygame.draw.rect(
                    pantalla, Paleta.LINEA_CARRIL,
                    (x_v, y, ConfigCalle.GROSOR_RAYA, ConfigCalle.LARGO_RAYA),
                    border_radius=2,
                )


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

        # Configuración de carriles (respetando la mano derecha)
        # Carril horizontal inferior -> avanza a la DERECHA (y = 310)
        # Carril horizontal superior -> avanza a la IZQUIERDA (y = 270)
        # Carril vertical izquierdo  -> avanza hacia ABAJO (x = 360)
        # Carril vertical derecho    -> avanza hacia ARRIBA (x = 400)
        self.vehiculos = [
            Vehiculo(x=50, y=310, velocidad=2.5, direccion="DERECHA", color=Paleta.AUTO_HORIZONTAL),
            Vehiculo(x=700, y=270, velocidad=2.0, direccion="IZQUIERDA", color=Paleta.AUTO_HORIZONTAL),
            Vehiculo(x=360, y=50, velocidad=2.2, direccion="ABAJO", color=Paleta.AUTO_VERTICAL),
            Vehiculo(x=400, y=500, velocidad=1.8, direccion="ARRIBA", color=Paleta.AUTO_VERTICAL),
        ]

    def _manejar_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.ejecutando = False

    def _actualizar(self):
        for vehiculo in self.vehiculos:
            vehiculo.actualizar()

    def _dibujar(self):
        self.pantalla.fill(Paleta.FONDO)
        self.interseccion.dibujar(self.pantalla)
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

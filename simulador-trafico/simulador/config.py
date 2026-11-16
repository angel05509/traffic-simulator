"""Configuración global: constantes, geometría de la intersección, física y paleta."""
import os


TITULO = "Simulador de Tráfico - Fase 6"
ANCHO_V, ALTO_V = 1000, 700          # lienzo virtual (se escala a la ventana)
FPS = 120

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # carpeta del proyecto
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


# Orígenes, giros y etiquetas
ORIGENES = ("OESTE", "ESTE", "NORTE", "SUR")
GIROS = ("FRENTE", "DERECHA", "IZQUIERDA")
DIRS = {"OESTE": (1, 0), "ESTE": (-1, 0), "NORTE": (0, 1), "SUR": (0, -1)}
ETIQ = {"OESTE": "Oeste", "ESTE": "Este", "NORTE": "Norte", "SUR": "Sur",
        "FRENTE": "Frente", "DERECHA": "Derecha", "IZQUIERDA": "Izquierda"}

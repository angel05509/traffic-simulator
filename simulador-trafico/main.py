import pygame
import sys

pygame.init()

ANCHO, ALTO = 800, 600
pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Simulador de Tráfico - Fase 1")

COLOR_FONDO = (50, 50, 50)       
COLOR_CALLE = (100, 100, 100)    
COLOR_AUTO = (0, 255, 200)       

# Posición inicial del auto
auto_x = 50
auto_y = 280
velocidad_auto = 2

# Bucle principal del simulador
reloj = pygame.time.Clock()

while True:
    # Cerrar ventana
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    # Mover auto 
    auto_x += velocidad_auto
    if auto_x > ANCHO:
        auto_x = -50 

    # Dibujar en pantalla
    pantalla.fill(COLOR_FONDO)
    
    # Dibujar la carretera 
    pygame.draw.rect(pantalla, COLOR_CALLE, (0, 250, ANCHO, 100))
    
    # Dibujar el vehículo
    pygame.draw.rect(pantalla, COLOR_AUTO, (auto_x, auto_y, 40, 20))

    # Actualizar pantalla
    pygame.display.flip()
    
    # Mantener a 60 fotogramas por segundo
    reloj.tick(60)
"""Aplicación: bucle principal y flujo MENÚ → SIMULACIÓN → GRÁFICAS."""
import math
import os
import sys

import pygame

from .config import *
from .graficas import HAY_MPL, guardar_pdf
from .historial import cargar_historial, guardar_historial
from .pantallas import PantallaGraficas, dibujar_menu
from .simulacion import Simulacion
from .ui import Boton, CANVAS, RELOJ, presentar


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

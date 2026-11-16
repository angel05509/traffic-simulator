"""Pantallas: ventana de gráficas y ventana de inicio."""
import os

import pygame

from .config import *
from .escenario import recurso_velo
from .graficas import HAY_MPL, NOMBRE_VISTA, figura_a_superficie, figura_pantalla, guardar_pdf
from .historial import abrir_carpeta, guardar_historial
from .ui import (Boton, F_BTN, F_BTN_S, F_PEQ, F_SEC, F_SUB, F_TITULO, F_TXT, tarjeta, texto)


class PantallaGraficas:
    def __init__(self):
        self.hist = []
        self.idx = 0
        self.vista = 0
        self.cache = {}
        self.mensaje = ""
        self.msg_color = VERDE
        gris = (70, 82, 94)
        self.b_ant = Boton((20, 646, 118, 44), "< Anterior", gris, F_BTN_S)
        self.b_sig = Boton((146, 646, 118, 44), "Siguiente >", gris, F_BTN_S)
        self.b_vista = Boton((272, 646, 190, 44), "", (110, 90, 190), F_BTN_S)
        self.b_pdf = Boton((470, 646, 150, 44), "Guardar PDF", (46, 160, 100), F_BTN_S)
        self.b_carpeta = Boton((628, 646, 156, 44), "Abrir carpeta", gris, F_BTN_S)
        self.b_menu = Boton((792, 646, 90, 44), "Menú", (90, 100, 110), F_BTN_S)
        self.b_repetir = Boton((890, 646, 90, 44), "Repetir", ACENTO, F_BTN_S)
        self.b_menu_solo = Boton((400, 420, 200, 52), "Volver al menú", (90, 100, 110))

    def abrir(self, hist, idx=None, mensaje="", color=VERDE):
        self.hist = hist
        self.idx = (len(hist) - 1) if idx is None else idx
        self.vista = 0
        self.cache = {}
        self.mensaje, self.msg_color = mensaje, color

    def _superficie(self):
        clave = (self.idx, self.vista)
        if clave not in self.cache:
            fig = figura_pantalla(self.hist[self.idx], self.hist, self.idx, self.vista)
            self.cache[clave] = figura_a_superficie(fig)
        return self.cache[clave]

    def _guardar_pdf(self):
        if not HAY_MPL:
            self.mensaje, self.msg_color = "Falta matplotlib:  pip install matplotlib", AMARILLO
            return
        try:
            ruta = guardar_pdf(self.hist[self.idx], self.hist, self.idx)
            guardar_historial(self.hist)
            self.mensaje, self.msg_color = f"PDF guardado: reportes/{os.path.basename(ruta)}", VERDE
        except Exception as e:  # noqa
            self.mensaje, self.msg_color = f"No se pudo guardar el PDF: {e}", ROJO

    def _ir(self, nuevo):
        if 0 <= nuevo < len(self.hist):
            self.idx = nuevo
            self.mensaje = ""

    def manejar(self, ev):
        if not self.hist:
            return "menu" if self.b_menu_solo.clic(ev) else None
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_LEFT:
                self._ir(self.idx - 1)
            elif ev.key == pygame.K_RIGHT:
                self._ir(self.idx + 1)
            elif ev.key == pygame.K_TAB:
                self.vista = 1 - self.vista
            elif ev.key == pygame.K_g:
                self._guardar_pdf()
            elif ev.key == pygame.K_ESCAPE:
                return "menu"
        self.b_ant.habilitado = self.idx > 0
        self.b_sig.habilitado = self.idx < len(self.hist) - 1
        if self.b_ant.clic(ev):
            self._ir(self.idx - 1)
        elif self.b_sig.clic(ev):
            self._ir(self.idx + 1)
        elif self.b_vista.clic(ev):
            self.vista = 1 - self.vista
        elif self.b_pdf.clic(ev):
            self._guardar_pdf()
        elif self.b_carpeta.clic(ev):
            abrir_carpeta(CARPETA_PDF)
        elif self.b_menu.clic(ev):
            return "menu"
        elif self.b_repetir.clic(ev):
            return "repetir"
        return None

    def dibujar(self, c):
        c.fill(FONDO)
        texto(c, "ANÁLISIS DE RESULTADOS", F_SEC, BLANCO, (24, 14))
        if not self.hist:
            texto(c, "Aún no hay simulaciones guardadas.", F_SUB, GRIS, (ANCHO_V // 2, 330), centro=True)
            texto(c, "Vuelve al menú y pulsa «Iniciar simulación».", F_TXT, GRIS, (ANCHO_V // 2, 365), centro=True)
            self.b_menu_solo.dibujar(c)
            return
        res = self.hist[self.idx]
        texto(c, f"Corrida {self.idx + 1} de {len(self.hist)}   ·   {res['fecha']}   ·   "
                 f"Tráfico {res['trafico']}   ·   {res['duracion_s']:g} s simulados", F_TXT, GRIS, (24, 52))
        kpis = [("Generados", str(res["generados"]), BLANCO), ("Cruzaron", str(res["cruzaron"]), VERDE),
                ("Espera promedio", f"{res['espera_prom']:.1f} s", BLANCO),
                ("Espera máxima", f"{res['espera_max']:.1f} s", BLANCO),
                ("Cola máxima", f"{res['cola_max']} veh.", AMARILLO if res["cola_max"] > 8 else BLANCO),
                ("Flujo", f"{res['flujo_veh_min']} veh/min", ACENTO)]
        for i, (lab, val, col) in enumerate(kpis):
            tarjeta(c, 25 + i * 160, 82, 150, 56, lab, val, col)

        if HAY_MPL:
            try:
                c.blit(self._superficie(), (20, 146))
            except Exception as e:  # noqa
                texto(c, f"Error al generar las gráficas: {e}", F_TXT, ROJO, (30, 300))
        else:
            pygame.draw.rect(c, PANEL, (20, 146, 960, 470), border_radius=12)
            texto(c, "Para ver las gráficas y generar PDF instala matplotlib:", F_SUB, BLANCO,
                  (ANCHO_V // 2, 350), centro=True)
            texto(c, "pip install matplotlib", F_BTN, AMARILLO, (ANCHO_V // 2, 395), centro=True)

        if self.mensaje:
            texto(c, self.mensaje, F_PEQ, self.msg_color, (24, 622))
        elif res.get("pdf"):
            texto(c, f"Reporte: reportes/{res['pdf']}", F_PEQ, GRIS, (24, 622))
        texto(c, "← → cambiar corrida   |   TAB cambiar vista   |   G guardar PDF", F_PEQ, GRIS,
              (ANCHO_V - 24, 622), derecha=True)

        self.b_ant.habilitado = self.idx > 0
        self.b_sig.habilitado = self.idx < len(self.hist) - 1
        self.b_vista.etiqueta = f"Vista: {NOMBRE_VISTA[self.vista]} ({self.vista + 1}/2)"
        for b in (self.b_ant, self.b_sig, self.b_vista, self.b_pdf, self.b_carpeta, self.b_menu, self.b_repetir):
            b.dibujar(c)


def dibujar_menu(c, demo, botones, hist_n):
    demo.renderizar(c, hud=False)
    c.blit(recurso_velo(), (0, 0))
    panel = pygame.Rect(280, 60, 440, 580)
    pygame.draw.rect(c, PANEL, panel, border_radius=20)
    pygame.draw.rect(c, (52, 64, 72), panel, width=2, border_radius=20)
    texto(c, "SIMULADOR", F_TITULO, BLANCO, (ANCHO_V // 2, 112), centro=True)
    texto(c, "DE TRÁFICO", F_TITULO, ACENTO, (ANCHO_V // 2, 154), centro=True)
    texto(c, "Intersección con semáforo y giros", F_SUB, GRIS, (ANCHO_V // 2, 196), centro=True)
    for b in botones:
        b.dibujar(c)
    estado_mpl = "" if HAY_MPL else "   ·   ¡falta matplotlib!"
    texto(c, f"Corridas guardadas: {hist_n}{estado_mpl}", F_PEQ, AMARILLO if not HAY_MPL else GRIS,
          (ANCHO_V // 2, 574), centro=True)
    texto(c, "Los reportes PDF se guardan en la carpeta «reportes»", F_PEQ, GRIS,
          (ANCHO_V // 2, 600), centro=True)

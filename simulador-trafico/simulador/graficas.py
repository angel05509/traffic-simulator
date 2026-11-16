"""Gráficas con matplotlib (pantalla en tema oscuro, PDF en tema claro) y reporte PDF."""
import math
import os
import textwrap

import pygame

try:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.figure import Figure
    from matplotlib.patches import Patch, Rectangle
    HAY_MPL = True
except ImportError:  # el simulador funciona, pero sin gráficas ni PDF
    HAY_MPL = False

from .config import *


TEMAS = {
    "oscuro": dict(fig="#12181c", ax="#1b242a", txt="#e8ebe6", sub="#9aa5ab", grid="#33404a"),
    "claro": dict(fig="#ffffff", ax="#fbfcfd", txt="#1b2328", sub="#5b666d", grid="#d9dee2"),
}
HEX_ORIGEN = {"OESTE": "#41bef5", "ESTE": "#46dcbe", "NORTE": "#ff9b41", "SUR": "#f55f69"}
HEX_GIRO = {"FRENTE": "#78aae6", "DERECHA": "#5ae696", "IZQUIERDA": "#ffbe50"}
HEX_NIVEL = {"Bajo": "#4cc38a", "Medio": "#f0b53c", "Alto": "#ef5b5b"}
HEX_ACENTO, HEX_AMAR = "#3d93f0", "#e8a820"


def _estilo(ax, T, titulo, fs, xlabel=None, ylabel=None):
    ax.set_facecolor(T["ax"])
    ax.set_title(titulo, fontsize=fs + 1.5, color=T["txt"], weight="bold", loc="left", pad=6)
    ax.tick_params(colors=T["sub"], labelsize=fs - 0.5, length=2)
    for sp in ax.spines.values():
        sp.set_color(T["grid"])
    ax.grid(True, color=T["grid"], linewidth=0.5, alpha=0.8)
    ax.set_axisbelow(True)
    if xlabel:
        ax.set_xlabel(xlabel, color=T["sub"], fontsize=fs)
    if ylabel:
        ax.set_ylabel(ylabel, color=T["sub"], fontsize=fs)


def _leyenda(ax, T, fs, **kw):
    leg = ax.legend(fontsize=fs - 1, frameon=True, facecolor=T["ax"], edgecolor=T["grid"],
                    labelcolor=T["txt"], **kw)
    leg.get_frame().set_alpha(0.9)


def _vacio(ax, T, fs, msg="Sin datos"):
    ax.text(0.5, 0.5, msg, ha="center", va="center", transform=ax.transAxes, color=T["sub"], fontsize=fs + 1)


def g_flujo(ax, res, hist, idx, T, fs):
    cr = res["serie"]["cruces"]
    paso = 5 if len(cr) <= 90 else 10
    _estilo(ax, T, f"Cruces cada {paso} s", fs, "Tiempo (s)", "Vehículos")
    if not cr:
        return _vacio(ax, T, fs)

    def acum(tt):
        return 0 if tt <= 0 else cr[min(tt, len(cr)) - 1]

    n = math.ceil(len(cr) / paso)
    vals = [acum((i + 1) * paso) - acum(i * paso) for i in range(n)]
    xs = [i * paso + paso / 2 for i in range(n)]
    ax.bar(xs, vals, width=paso * 0.82, color=HEX_ACENTO)
    media = sum(vals) / len(vals)
    ax.axhline(media, color=HEX_AMAR, ls="--", lw=1.2, label=f"Media {media:.1f}")
    _leyenda(ax, T, fs, loc="upper right")


def g_colas(ax, res, hist, idx, T, fs):
    _estilo(ax, T, "Cola por acceso (vehículos detenidos)", fs, "Tiempo (s)", "Vehículos")
    s = res["serie"]
    if not s["t"]:
        return _vacio(ax, T, fs)
    for o in ORIGENES:
        ax.plot(s["t"], s["cola"][o], color=HEX_ORIGEN[o], lw=1.6, label=ETIQ[o])
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    _leyenda(ax, T, fs, loc="upper left", ncol=2)


def _barras(ax, T, fs, claves, valores, colores, fmt):
    ax.bar(range(len(claves)), valores, color=colores, width=0.62)
    ax.set_xticks(range(len(claves)))
    ax.set_xticklabels([ETIQ[k] for k in claves])
    tope = max(valores) if valores and max(valores) > 0 else 1
    ax.set_ylim(0, tope * 1.22)
    for i, v in enumerate(valores):
        ax.text(i, v + tope * 0.02, fmt(v), ha="center", va="bottom", fontsize=fs, color=T["txt"])


def g_espera(ax, res, hist, idx, T, fs):
    _estilo(ax, T, "Espera promedio por acceso", fs, None, "Segundos")
    vals = [res["por_origen"][o]["espera_prom"] for o in ORIGENES]
    _barras(ax, T, fs, ORIGENES, vals, [HEX_ORIGEN[o] for o in ORIGENES], lambda v: f"{v:.1f}")


def g_cruces_origen(ax, res, hist, idx, T, fs):
    _estilo(ax, T, "Vehículos que cruzaron por acceso", fs, None, "Vehículos")
    vals = [res["por_origen"][o]["cruzaron"] for o in ORIGENES]
    _barras(ax, T, fs, ORIGENES, vals, [HEX_ORIGEN[o] for o in ORIGENES], lambda v: f"{v:d}")


def g_giros(ax, res, hist, idx, T, fs):
    _estilo(ax, T, "Maniobras de los que cruzaron", fs)
    ax.grid(False)
    claves = [g for g in GIROS if res["giros"].get(g, 0) > 0]
    total = sum(res["giros"].values())
    if not claves:
        return _vacio(ax, T, fs)
    vals = [res["giros"][g] for g in claves]
    _, _, auto = ax.pie(
        vals, labels=[ETIQ[g] for g in claves], colors=[HEX_GIRO[g] for g in claves],
        autopct=lambda p: f"{p:.0f}%" if p >= 6 else "", pctdistance=0.78, startangle=90, counterclock=False,
        wedgeprops=dict(width=0.45, edgecolor=T["ax"], linewidth=1.5), textprops=dict(fontsize=fs, color=T["txt"]))
    for a in auto:
        a.set_color("#0e1215")
        a.set_weight("bold")
        a.set_fontsize(fs - 0.5)
    ax.text(0, 0, f"{total}\ncruces", ha="center", va="center", color=T["txt"], fontsize=fs, weight="bold")


def g_velocidad(ax, res, hist, idx, T, fs):
    _estilo(ax, T, "Velocidad media y vehículos en vía", fs, "Tiempo (s)", "km/h")
    s = res["serie"]
    if not s["t"]:
        return _vacio(ax, T, fs)
    l1, = ax.plot(s["t"], s["vel_kmh"], color=HEX_ACENTO, lw=1.8, label="Velocidad media (km/h)")
    ax.set_ylim(bottom=0)
    ax.set_xlim(left=0)
    ax2 = ax.twinx()
    l2, = ax2.plot(s["t"], s["en_via"], color=HEX_AMAR, lw=1.3, ls="--", label="Vehículos en vía")
    ax2.tick_params(colors=T["sub"], labelsize=fs - 0.5, length=2)
    for sp in ax2.spines.values():
        sp.set_color(T["grid"])
    ax2.set_ylabel("Vehículos", color=T["sub"], fontsize=fs)
    ax2.set_ylim(bottom=0)
    leg = ax.legend([l1, l2], [l1.get_label(), l2.get_label()], fontsize=fs - 1, loc="lower right",
                    frameon=True, facecolor=T["ax"], edgecolor=T["grid"], labelcolor=T["txt"])
    leg.get_frame().set_alpha(0.9)


def _ventana(hist, idx):
    base = max(0, idx - 11)
    return base, hist[base: idx + 1]


def g_comp_cruces(ax, res, hist, idx, T, fs):
    _estilo(ax, T, "Cruces por corrida", fs, "Corrida", "Vehículos")
    base, vent = _ventana(hist, idx)
    if not vent:
        return _vacio(ax, T, fs)
    for k, r in enumerate(vent):
        actual = (k == len(vent) - 1)
        ax.bar(k, r["cruzaron"], color=HEX_NIVEL.get(r["trafico"], HEX_ACENTO), width=0.7,
               edgecolor=T["txt"] if actual else "none", linewidth=1.8 if actual else 0)
    ax.set_xticks(range(len(vent)))
    ax.set_xticklabels([f"#{base + k + 1}" for k in range(len(vent))])
    niveles = [n for n in HEX_NIVEL if any(r["trafico"] == n for r in vent)]
    _leyenda(ax, T, fs, handles=[Patch(color=HEX_NIVEL[n], label=f"Tráfico {n}") for n in niveles],
             loc="upper left")
    ax.set_ylim(0, max(r["cruzaron"] for r in vent) * 1.35 + 1)


def g_comp_espera(ax, res, hist, idx, T, fs):
    _estilo(ax, T, "Espera promedio por corrida", fs, "Corrida", "Segundos")
    base, vent = _ventana(hist, idx)
    if not vent:
        return _vacio(ax, T, fs)
    xs = list(range(len(vent)))
    ys = [r["espera_prom"] for r in vent]
    ax.plot(xs, ys, color=HEX_ACENTO, lw=1.6, zorder=2)
    ax.scatter(xs, ys, c=[HEX_NIVEL.get(r["trafico"], HEX_ACENTO) for r in vent], s=46, zorder=3,
               edgecolors=T["txt"], linewidths=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"#{base + k + 1}" for k in xs])
    ax.set_ylim(0, max(ys + [1]) * 1.25)


VISTAS = {
    0: [g_flujo, g_colas, g_espera, g_giros],
    1: [g_cruces_origen, g_velocidad, g_comp_cruces, g_comp_espera],
}
NOMBRE_VISTA = {0: "Principal", 1: "Detalle"}


def _rellenar(fig, gs, res, hist, idx, vista, T, fs):
    for i, fn in enumerate(VISTAS[vista]):
        fn(fig.add_subplot(gs[i // 2, i % 2]), res, hist, idx, T, fs)


def figura_pantalla(res, hist, idx, vista):
    T = TEMAS["oscuro"]
    fig = Figure(figsize=(9.6, 4.7), dpi=100, facecolor=T["fig"])
    FigureCanvasAgg(fig)
    gs = fig.add_gridspec(2, 2, left=0.06, right=0.985, top=0.93, bottom=0.095, hspace=0.72, wspace=0.27)
    _rellenar(fig, gs, res, hist, idx, vista, T, 7.5)
    return fig


def observaciones(res):
    po = res["por_origen"]
    if res["cruzaron"] == 0:
        return ["No cruzó ningún vehículo durante la corrida."]
    peor = max(ORIGENES, key=lambda o: po[o]["espera_prom"])
    mejor = min(ORIGENES, key=lambda o: po[o]["espera_prom"])
    top = max(ORIGENES, key=lambda o: po[o]["cruzaron"])
    giro = max(GIROS, key=lambda g: res["giros"].get(g, 0))
    cr = res["serie"]["cruces"]
    pico = ""
    if len(cr) >= 10:
        mejor_i, mejor_v = 0, -1
        for i in range(0, len(cr) - 9, 5):
            v = cr[i + 9] - (cr[i - 1] if i > 0 else 0)
            if v > mejor_v:
                mejor_i, mejor_v = i, v
        pico = f"El intervalo de 10 s con más flujo fue {mejor_i + 1}-{mejor_i + 10} s ({mejor_v} cruces). "
    ratio = res["cruzaron"] / res["generados"] * 100 if res["generados"] else 0
    return [
        f"• Mayor espera promedio en el acceso {ETIQ[peor]} ({po[peor]['espera_prom']:.1f} s) y menor en el acceso "
        f"{ETIQ[mejor]} ({po[mejor]['espera_prom']:.1f} s).",
        f"• El acceso con más cruces fue {ETIQ[top]} ({po[top]['cruzaron']} de {res['cruzaron']} vehículos). "
        f"La maniobra más frecuente fue «{ETIQ[giro].lower()}».",
        f"• Cruzó el {ratio:.0f}% de los vehículos generados; la cola máxima fue de {res['cola_max']} vehículos y la "
        f"velocidad media de {res['vel_media_kmh']} km/h.",
        f"• {pico}Ciclo del semáforo: verde 10 s, amarillo 2.5 s y todo rojo 1.2 s por eje.",
    ]


def figura_pdf(res, hist, idx, vista):
    T = TEMAS["claro"]
    fig = Figure(figsize=(8.27, 11.69), dpi=100, facecolor=T["fig"])
    FigureCanvasAgg(fig)
    fig.text(0.07, 0.955, "Reporte de simulación de tráfico", fontsize=19, weight="bold", color=T["txt"])
    fig.text(0.07, 0.930, f"{res['fecha']}   ·   Tráfico {res['trafico']}   ·   "
             f"Duración {res['duracion_s']:g} s simulados", fontsize=9.5, color=T["sub"])
    fig.add_artist(Rectangle((0.07, 0.918), 0.86, 0.0018, transform=fig.transFigure,
                             facecolor=HEX_ACENTO, edgecolor="none"))
    if vista == 0:
        kp = [("Vehículos generados", str(res["generados"])), ("Vehículos que cruzaron", str(res["cruzaron"])),
              ("Espera promedio", f"{res['espera_prom']:.1f} s"), ("Espera máxima", f"{res['espera_max']:.1f} s"),
              ("Cola máxima", f"{res['cola_max']} veh."), ("Flujo", f"{res['flujo_veh_min']} veh/min")]
        for i, (lab, val) in enumerate(kp):
            x, y, w, h = 0.07 + (i % 3) * 0.2933, 0.80 - (i // 3) * 0.10, 0.2733, 0.08
            fig.add_artist(Rectangle((x, y), w, h, transform=fig.transFigure, facecolor="#f1f4f7",
                                     edgecolor=T["grid"], linewidth=0.8))
            fig.text(x + 0.015, y + h - 0.027, lab, fontsize=8.5, color=T["sub"])
            fig.text(x + 0.015, y + 0.016, val, fontsize=16, weight="bold", color=T["txt"])
    else:
        fig.text(0.07, 0.885, "Observaciones", fontsize=12, weight="bold", color=T["txt"])
        y = 0.858
        for linea in observaciones(res):
            partes = textwrap.wrap(linea, 98, subsequent_indent="   ")
            for p in partes:
                fig.text(0.07, y, p, fontsize=9, color=T["txt"])
                y -= 0.0205
            y -= 0.006
    gs = fig.add_gridspec(2, 2, left=0.09, right=0.95, top=0.635, bottom=0.095, hspace=0.62, wspace=0.34)
    _rellenar(fig, gs, res, hist, idx, vista, T, 8)
    fig.text(0.07, 0.028, "Simulador de Tráfico · Fase 6", fontsize=8, color=T["sub"])
    fig.text(0.93, 0.028, f"Página {vista + 1}/2", fontsize=8, color=T["sub"], ha="right")
    return fig


def guardar_pdf(res, hist, idx):
    """Guarda el reporte en reportes/reporte_AAAA-MM-DD_HH-MM-SS.pdf y devuelve la ruta."""
    os.makedirs(CARPETA_PDF, exist_ok=True)
    nombre = f"reporte_{res['fecha_archivo']}.pdf"
    ruta = os.path.join(CARPETA_PDF, nombre)
    with PdfPages(ruta) as pdf:
        info = pdf.infodict()
        info["Title"] = f"Reporte de simulación de tráfico - {res['fecha']}"
        info["Author"] = "Simulador de Tráfico"
        for vista in (0, 1):
            pdf.savefig(figura_pdf(res, hist, idx, vista))
    res["pdf"] = nombre
    return ruta


def figura_a_superficie(fig):
    canvas = fig.canvas
    canvas.draw()
    w, h = canvas.get_width_height()
    return pygame.image.frombuffer(bytes(canvas.buffer_rgba()), (w, h), "RGBA").convert()

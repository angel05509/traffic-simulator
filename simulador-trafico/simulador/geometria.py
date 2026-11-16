"""Rutas de los vehículos (polilíneas con curvas Bézier) y detección de conflictos en el cruce."""
import math
from bisect import bisect_right

from .config import *


def girar(d, giro):
    dx, dy = d
    if giro == "DERECHA":
        return (-dy, dx)
    if giro == "IZQUIERDA":
        return (dy, -dx)
    return d


class Ruta:
    PASOS_CURVA = 40

    def __init__(self, origen, giro):
        self.origen, self.giro = origen, giro
        d = DIRS[origen]
        d2 = girar(d, giro)
        self.dir_entrada, self.dir_salida = d, d2
        self.eje = "H" if d[0] != 0 else "V"

        rv = (-d[1], d[0])
        rv2 = (-d2[1], d2[0])
        ext = ANCHO_V // 2 if d[0] != 0 else ALTO_V // 2
        ext2 = ANCHO_V // 2 if d2[0] != 0 else ALTO_V // 2

        inicio = (CENTRO_X + rv[0] * CARRIL - d[0] * (ext + MARGEN_FUERA),
                  CENTRO_Y + rv[1] * CARRIL - d[1] * (ext + MARGEN_FUERA))
        p_in = (CENTRO_X + rv[0] * CARRIL - d[0] * MITAD, CENTRO_Y + rv[1] * CARRIL - d[1] * MITAD)
        p_out = (CENTRO_X + rv2[0] * CARRIL + d2[0] * MITAD, CENTRO_Y + rv2[1] * CARRIL + d2[1] * MITAD)
        fin = (CENTRO_X + rv2[0] * CARRIL + d2[0] * (ext2 + MARGEN_FUERA),
               CENTRO_Y + rv2[1] * CARRIL + d2[1] * (ext2 + MARGEN_FUERA))

        pts = [inicio, p_in]
        if giro != "FRENTE":
            c = (p_out[0], p_in[1]) if d[0] != 0 else (p_in[0], p_out[1])
            n = self.PASOS_CURVA
            for i in range(1, n):
                t = i / n
                u = 1 - t
                pts.append((u * u * p_in[0] + 2 * u * t * c[0] + t * t * p_out[0],
                            u * u * p_in[1] + 2 * u * t * c[1] + t * t * p_out[1]))
        pts += [p_out, fin]

        self.pts = pts
        self.acum = [0.0]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            self.acum.append(self.acum[-1] + math.hypot(x1 - x0, y1 - y0))
        self.largo = self.acum[-1]
        self.s_linea = self.acum[1]
        self.s_parada = self.s_linea - DIST_PARADA
        self.s_salida = self.acum[-2]
        self.s_fin_cruce = self.s_salida + 40
        self.p_salida = p_out

    def punto(self, s):
        s = 0.0 if s < 0 else self.largo if s > self.largo else s
        i = bisect_right(self.acum, s) - 1
        i = min(max(i, 0), len(self.pts) - 2)
        seg = self.acum[i + 1] - self.acum[i]
        t = (s - self.acum[i]) / seg if seg > 0 else 0.0
        x0, y0 = self.pts[i]
        x1, y1 = self.pts[i + 1]
        return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t

    def muestra(self, s):
        x, y = self.punto(s)
        xa, ya = self.punto(s + 7)
        xb, yb = self.punto(s - 7)
        hx, hy = xa - xb, ya - yb
        n = math.hypot(hx, hy)
        if n < 1e-6:
            return x, y, float(self.dir_entrada[0]), float(self.dir_entrada[1])
        return x, y, hx / n, hy / n


RUTAS = {(o, g): Ruta(o, g) for o in ORIGENES for g in GIROS}
_CONFLICTOS = {}


def en_conflicto(ra, rb):
    clave = (ra.origen, ra.giro, rb.origen, rb.giro)
    res = _CONFLICTOS.get(clave)
    if res is None:
        def muestras(r):
            lst, s = [], r.s_linea - 10
            while s <= r.s_salida + 30:
                lst.append(r.punto(s))
                s += 6
            return lst
        a, b = muestras(ra), muestras(rb)
        u2 = UMBRAL_CONFLICTO ** 2
        res = any((ax - bx) ** 2 + (ay - by) ** 2 < u2 for ax, ay in a for bx, by in b)
        _CONFLICTOS[clave] = res
    return res

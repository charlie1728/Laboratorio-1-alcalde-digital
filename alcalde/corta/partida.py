"""Reglas de Corta la mentira (sin pygame: se puede probar y correr igual en todos los computadores).

Todo pasa en un campo lógico de 1280 x 720. Las publicaciones salen desde abajo, suben y caen.
  * Cortar una falsa: puntos y combo.
  * Cortar una verdadera: el barrio de abajo pierde confianza.
  * Si una falsa vuelve a caer sin cortar, enferma el barrio donde cae; los barrios muy enfermos
    contagian a sus vecinos por las calles del mapa (grafo de la ciudad).
  * Algunas falsas son el ORIGEN de un rumor: si llegan arriba sin cortar, se copian en dos
    (árbol de mutaciones). Cortar el origen tumba todas sus copias de una vez (se poda el subárbol).
La misma semilla da las mismas publicaciones: así varios jugadores compiten con lo mismo.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

from ..estructuras.arbol_mutaciones import ArbolMutaciones, NodoMutacion
from ..modelo.mapa import ZONAS, crear_mapa
from .contenido import ESPECIALES, FALSAS, VERDADERAS

ANCHO, ALTO = 1280, 720
GRAVEDAD = 560.0
DIAS = 5
DIA_SEG = 50.0
COMBO_SEG = 1.4
FIEBRE_COMBO = 8
FIEBRE_SEG = 7.0
NIVEL_MAX = 3

# Los barrios de izquierda a derecha en el horizonte (ordenados por su x en el mapa).
BARRIOS = sorted(ZONAS, key=lambda z: (ZONAS[z]["pos"][0], ZONAS[z]["pos"][1]))
ANCHO_BARRIO = ANCHO / len(BARRIOS)

# Dificultad por día: (segundos entre tandas, publicaciones por tanda, % falsas, nivel máximo de las falsas)
DIFICULTAD = {1: (1.5, (1, 2), 0.6, 1), 2: (1.35, (1, 3), 0.62, 2), 3: (1.2, (2, 3), 0.64, 2),
              4: (1.05, (2, 3), 0.66, 3), 5: (0.95, (2, 4), 0.68, 3)}


@dataclass
class Pub:
    id: int
    tipo: str                 # "falsa" | "verdad" | "especial"
    fuente: str
    texto: str
    x: float
    y: float
    vx: float
    vy: float
    rot: float = 0.0
    vrot: float = 0.0
    nivel: int = 1
    pista: str = ""
    autor: int = 0            # qué vecino la publicó (para su cara)
    especial: str = ""
    vida: int = 1             # cortes que necesita (las virales necesitan varios)
    viral: bool = False
    caso: Optional[int] = None
    nodo: Optional[int] = None
    origen: bool = False
    subio: bool = False       # ya pasó por lo más alto
    copia: bool = False
    golpe: float = 0.0        # destello al recibir un corte que no la rompe

    @property
    def ancho(self):
        return 110 if self.tipo == "especial" else (320 if self.viral else 290)

    @property
    def alto(self):
        return 110 if self.tipo == "especial" else (104 if self.viral else 92)


@dataclass
class Jugador:
    nombre: str
    rol: str
    look: dict
    color: tuple
    puntos: int = 0
    cortadas: int = 0
    errores: int = 0
    mejor_combo: int = 0
    pistas: list = field(default_factory=list)


class Partida:
    def __init__(self, jugadores: list[dict], semilla: Optional[int] = None, dias: int = DIAS,
                 dia_seg: float = DIA_SEG):
        self.semilla = semilla if semilla is not None else random.randrange(1 << 30)
        self.rng = random.Random(self.semilla)
        self.jugadores = [Jugador(j["nombre"], j["rol"], j.get("look") or {}, tuple(j.get("color", (255, 194, 61))))
                          for j in jugadores]
        self.dias, self.dia_seg = dias, dia_seg
        self.dia = 1
        self.turno = 0                     # qué jugador tiene el mouse (modo por turnos)
        self.reloj = 0.0
        self.tiempo = 0.0
        self.estado = "jugando"            # jugando | fin_dia | fin
        self.pubs: list[Pub] = []
        self.nivel = {z: 0 for z in BARRIOS}      # qué tan enfermo está cada barrio (0..3)
        self.mapa = crear_mapa()
        self.arboles: dict[int, ArbolMutaciones] = {}
        self.combo = 0
        self.ultimo_corte = -10.0
        self.fiebre = 0.0
        self.lento = 0.0
        self.escudo = 0.0
        self.prox_tanda = 1.5
        self.prox_contagio = 6.0
        self.eventos: list[dict] = []      # para la pantalla (sonidos, textos, partículas)
        self._sig = 1
        self._sig_caso = 1
        self._mazo_f, self._mazo_v = [], []
        self.hoy = self._hoy_vacio()
        self.resumen: Optional[dict] = None

    @staticmethod
    def _hoy_vacio():
        return dict(cortadas=0, errores=0, caidas=0, puntos=0, pistas=[], equivocadas=[])

    # -------------------------------------------------------------- utilidades
    @property
    def jugador(self) -> Jugador:
        return self.jugadores[self.turno % len(self.jugadores)]

    def salud(self) -> int:
        """Salud de la ciudad: 100 si ningún barrio está enfermo, 0 si todos lo están del todo."""
        total = sum(self.nivel.values())
        return max(0, round(100 - total * 100 / (len(BARRIOS) * NIVEL_MAX)))

    def barrio_en(self, x: float) -> str:
        i = int(max(0, min(len(BARRIOS) - 1, x // ANCHO_BARRIO)))
        return BARRIOS[i]

    def evento(self, **kw):
        kw["t"] = self.tiempo
        self.eventos.append(kw)

    def _sacar(self, mazo, fuente_lista, filtro=None):
        if not mazo:
            mazo.extend(fuente_lista)
            self.rng.shuffle(mazo)
        for i, item in enumerate(mazo):
            if filtro is None or filtro(item):
                return mazo.pop(i)
        return mazo.pop()

    # -------------------------------------------------------------- lanzar publicaciones
    def _lanzar(self, tipo, x=None, **kw) -> Pub:
        x = x if x is not None else self.rng.uniform(170, ANCHO - 170)
        vx = (ANCHO / 2 - x) * self.rng.uniform(0.05, 0.2) + self.rng.uniform(-35, 35)
        vy = -self.rng.uniform(780, 900)
        p = Pub(self._sig, tipo, kw.pop("fuente", ""), kw.pop("texto", ""), x, ALTO + 70, vx, vy,
                rot=self.rng.uniform(-5, 5), vrot=self.rng.uniform(-6, 6), autor=self.rng.randrange(24), **kw)
        self._sig += 1
        self.pubs.append(p)
        return p

    def _tanda(self):
        espera, (a, b), pf, nmax = DIFICULTAD[min(self.dia, 5)]
        cuantas = self.rng.randint(a, b)
        carriles = self.rng.sample(range(4), min(4, cuantas))
        xs = [190 + c * (ANCHO - 380) / 3 + self.rng.uniform(-40, 40) for c in carriles]
        for x in xs:
            r = self.rng.random()
            if self.dia >= 2 and r < 0.05:
                e = self.rng.choice(list(ESPECIALES))
                self._lanzar("especial", x, especial=e, texto=ESPECIALES[e]["texto"])
            elif self.rng.random() < pf:
                f, t, nivel, pista = self._sacar(self._mazo_f, FALSAS, lambda it: it[2] <= nmax)
                viral = self.dia >= 3 and self.rng.random() < 0.08
                origen = not viral and self.dia >= 2 and self.rng.random() < 0.22
                p = self._lanzar("falsa", x, fuente=f, texto=t, nivel=nivel, pista=pista,
                                 vida=3 if viral else 1, viral=viral, origen=origen)
                if origen or viral:
                    raiz = NodoMutacion(t, f"vecino{p.autor}", self.dia, alcance=0)
                    self.arboles[self._sig_caso] = ArbolMutaciones(t, raiz)
                    p.caso, p.nodo = self._sig_caso, raiz.id
                    self._sig_caso += 1
            else:
                f, t = self._sacar(self._mazo_v, VERDADERAS)
                self._lanzar("verdad", x, fuente=f, texto=t)
        self.prox_tanda = espera * self.rng.uniform(0.8, 1.2)

    def _copiar(self, p: Pub):
        """Un origen que llegó arriba sin cortar se copia en dos (hijos en el árbol del rumor)."""
        arbol = self.arboles.get(p.caso)
        if arbol is None or p.nodo not in arbol:
            return
        for lado in (-1, 1):
            hijo = arbol.insertar(p.nodo, NodoMutacion(p.texto, f"copia{p.id}", self.dia, alcance=0))
            c = Pub(self._sig, "falsa", p.fuente, p.texto, p.x, p.y, p.vx + lado * 170, -220,
                    rot=p.rot, vrot=lado * 8, nivel=p.nivel, pista=p.pista, autor=self.rng.randrange(24),
                    caso=p.caso, nodo=hijo.id, copia=True, subio=True)
            self._sig += 1
            self.pubs.append(c)
        self.evento(t_="copia", x=p.x, y=p.y)

    # -------------------------------------------------------------- cortar
    def cortar(self, a, b) -> int:
        """Un trazo del mouse de a a b (en el campo lógico). Devuelve cuántas cosas cortó."""
        if self.estado != "jugando":
            return 0
        cortadas = []
        for p in list(self.pubs):
            if p not in self.pubs or not _toca(a, b, p):
                continue
            if p.vida > 1:
                p.vida -= 1
                p.golpe = 0.25
                self.evento(t_="golpe", x=p.x, y=p.y, id=p.id)
                continue
            cortadas.append(p)
            self._cortar(p, (b[0] - a[0], b[1] - a[1]))
        falsas = [p for p in cortadas if p.tipo == "falsa"]
        if len(falsas) >= 2:
            extra = 15 * (len(falsas) - 1) * (2 if self.jugador.rol == "influencer" else 1)
            self._sumar(extra)
            self.evento(t_="multi", n=len(falsas), x=falsas[-1].x, y=falsas[-1].y, puntos=extra)
        return len(cortadas)

    def _sumar(self, pts):
        j = self.jugador
        mult = 2 if self.fiebre > 0 else 1
        j.puntos += pts * mult
        self.hoy["puntos"] += pts * mult
        return pts * mult

    def _cortar(self, p: Pub, direccion):
        self.pubs.remove(p)
        j = self.jugador
        if p.tipo == "especial":
            self._especial(p)
            self.evento(t_="corte", pub=p, dir=direccion, bien=True)
            return
        if p.tipo == "verdad":
            z = self.barrio_en(p.x)
            self.nivel[z] = min(NIVEL_MAX, self.nivel[z] + 1)
            self.combo = 0
            j.errores += 1
            self.hoy["errores"] += 1
            self.hoy["equivocadas"].append((p.fuente, p.texto))
            self.evento(t_="corte", pub=p, dir=direccion, bien=False, barrio=z)
            self.evento(t_="error", x=p.x, y=p.y, texto="¡Era verdad!", sub=f"Venía de: {p.fuente}")
            return
        # falsa
        if self.tiempo - self.ultimo_corte < COMBO_SEG:
            self.combo += 1
        else:
            self.combo = 1
        self.ultimo_corte = self.tiempo
        j.mejor_combo = max(j.mejor_combo, self.combo)
        pts = self._sumar(10 + 5 * min(self.combo - 1, 10) + (30 if p.viral else 0) + 5 * (p.nivel - 1))
        j.cortadas += 1
        self.hoy["cortadas"] += 1
        if p.pista and p.pista not in j.pistas:
            j.pistas.append(p.pista)
            self.hoy["pistas"].append(p.pista)
        self.evento(t_="corte", pub=p, dir=direccion, bien=True, puntos=pts, combo=self.combo)
        if self.combo == FIEBRE_COMBO:
            self.fiebre = FIEBRE_SEG
            self.evento(t_="fiebre")
        if p.caso is not None:
            self._podar(p)

    def _podar(self, p: Pub):
        """Cortar un rumor tumba todo lo que se copió de él: se poda su subárbol."""
        arbol = self.arboles.get(p.caso)
        if arbol is None or p.nodo not in arbol:
            return
        ids = {n.id for n in arbol.podar(p.nodo)}
        caidas = [q for q in self.pubs if q.caso == p.caso and q.nodo in ids]
        for q in caidas:
            self.pubs.remove(q)
            self.evento(t_="corte", pub=q, dir=(0, 1), bien=True, cadena=True)
        if caidas:
            extra = self._sumar(20 * len(caidas))
            self.jugador.cortadas += len(caidas)
            self.hoy["cortadas"] += len(caidas)
            self.evento(t_="cadena", n=len(caidas), x=p.x, y=p.y, puntos=extra)

    def _especial(self, p: Pub):
        e = p.especial
        if e == "lupa":
            self.lento = 9.0 if self.jugador.rol == "periodista" else 6.0
        elif e == "megafono":
            falsas = [q for q in self.pubs if q.tipo == "falsa"]
            for q in falsas:
                self.pubs.remove(q)
                self.evento(t_="corte", pub=q, dir=(0, -1), bien=True, cadena=True)
            self._sumar(10 * len(falsas))
        elif e == "escudo":
            self.escudo = 15.0 if self.jugador.rol == "candidato" else 10.0
        elif e == "corazon":
            peor = max(BARRIOS, key=lambda z: self.nivel[z])
            self.nivel[peor] = 0
            self.evento(t_="sana", barrio=peor)
        self.evento(t_="poder", especial=e, x=p.x, y=p.y)

    # -------------------------------------------------------------- caer sobre la ciudad
    def _cae(self, p: Pub):
        z = self.barrio_en(p.x)
        if p.tipo == "falsa":
            if self.escudo > 0:
                self.evento(t_="bloqueo", x=p.x, barrio=z)
                return
            self.nivel[z] = min(NIVEL_MAX, self.nivel[z] + (2 if p.viral else 1))
            self.combo = 0
            self.hoy["caidas"] += 1
            self.evento(t_="cae", x=p.x, barrio=z, viral=p.viral)
        elif p.tipo == "verdad":
            # Una noticia verdadera que llega a la gente la tranquiliza.
            if self.nivel[z] > 0:
                self.nivel[z] = max(0, self.nivel[z] - (2 if self.jugador.rol == "ciudadano" else 1))
                self.evento(t_="sana", barrio=z)
            self._sumar(3)

    def _contagio(self):
        """Los barrios muy enfermos contagian a uno de sus vecinos (aristas del grafo de la ciudad)."""
        enfermos = [z for z in BARRIOS if self.nivel[z] >= NIVEL_MAX]
        for z in enfermos:
            vecinos = [v for v in self.mapa.vecinos(z) if self.nivel[v] < 2]
            if vecinos:
                v = self.rng.choice(sorted(vecinos))
                self.nivel[v] += 1
                self.evento(t_="contagio", de=z, a=v)

    # -------------------------------------------------------------- bucle
    def actualizar(self, dt: float):
        if self.estado != "jugando":
            return
        dt = min(dt, 0.05)
        escala = 0.4 if self.lento > 0 else 1.0
        self.tiempo += dt
        self.reloj += dt
        for k in ("fiebre", "lento", "escudo"):
            setattr(self, k, max(0.0, getattr(self, k) - dt))
        if self.tiempo - self.ultimo_corte > COMBO_SEG and self.combo:
            self.combo = 0
        mdt = dt * escala
        for p in list(self.pubs):
            p.vy += GRAVEDAD * mdt
            p.x += p.vx * mdt
            p.y += p.vy * mdt
            p.rot += p.vrot * mdt
            p.golpe = max(0.0, p.golpe - dt)
            if p.x < 60 or p.x > ANCHO - 60:
                p.vx = -p.vx * 0.6
                p.x = max(60, min(ANCHO - 60, p.x))
            if not p.subio and p.vy >= 0:
                p.subio = True
                if p.origen:
                    self._copiar(p)
            if p.subio and p.y > ALTO + 80:
                self.pubs.remove(p)
                self._cae(p)
        if self.reloj < self.dia_seg - 3:
            self.prox_tanda -= dt
            if self.prox_tanda <= 0:
                self._tanda()
        self.prox_contagio -= dt
        if self.prox_contagio <= 0:
            self._contagio()
            self.prox_contagio = max(6.0, 11.0 - self.dia)
        if self.salud() <= 0:
            self._terminar(perdio=True)
        elif self.reloj >= self.dia_seg and not self.pubs:
            self._fin_dia()

    def _fin_dia(self):
        self.resumen = dict(dia=self.dia, jugador=self.jugador.nombre, salud=self.salud(), **self.hoy)
        if self.dia >= self.dias:
            self._terminar(perdio=False)
        else:
            self.estado = "fin_dia"

    def siguiente_dia(self):
        if self.estado != "fin_dia":
            return
        self.dia += 1
        self.turno += 1
        self.reloj = 0.0
        self.prox_tanda = 1.5
        self.combo = 0
        self.hoy = self._hoy_vacio()
        self.estado = "jugando"
        # La noche calma un poco cada barrio.
        for z in BARRIOS:
            self.nivel[z] = max(0, self.nivel[z] - 1)

    def _terminar(self, perdio: bool):
        if self.resumen is None or self.resumen.get("dia") != self.dia:
            self.resumen = dict(dia=self.dia, jugador=self.jugador.nombre, salud=self.salud(), **self.hoy)
        self.perdio = perdio
        self.estado = "fin"


def _toca(a, b, p: Pub) -> bool:
    """¿El trazo a-b atraviesa la tarjeta (rectángulo girado)? Liang-Barsky en coordenadas de la tarjeta."""
    ang = math.radians(p.rot)
    c, s = math.cos(-ang), math.sin(-ang)

    def local(q):
        dx, dy = q[0] - p.x, q[1] - p.y
        return dx * c - dy * s, dx * s + dy * c

    (x0, y0), (x1, y1) = local(a), local(b)
    hw, hh = p.ancho / 2, p.alto / 2
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, x0 + hw), (dx, hw - x0), (-dy, y0 + hh), (dy, hh - y0)):
        if pp == 0:
            if qq < 0:
                return False
            continue
        r = qq / pp
        if pp < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
        if t0 > t1:
            return False
    return True

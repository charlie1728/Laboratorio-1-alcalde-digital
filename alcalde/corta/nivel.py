"""Un nivel de Corta la mentira: un día en un barrio de Ciudad Nova (sin pygame).

Campo lógico de 1280 x 720. Las publicaciones salen desde abajo (o en bus, o las lanza el jefe).
  * Cortar lo falso da puntos, combo y carga el poder del personaje.
  * Cortar lo verdadero le quita confianza al barrio.
  * Lo falso que vuelve a caer le quita confianza al barrio; lo verdadero que cae se guarda en el
    Archivo de hechos (un árbol AVL) y tranquiliza a la gente.
  * Un ORIGEN que llega arriba sin cortar se reenvía a los seguidores de su autor (aristas de salida
    del grafo social). Esas copias son hijos en el árbol del rumor; cortar el origen poda el subárbol.
La misma semilla da el mismo nivel: así dos jugadores en red compiten con lo mismo.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

from ..estructuras.arbol_mutaciones import ArbolMutaciones, NodoMutacion
from .contenido import BARRIOS_JUEGO, ESPECIALES, FALSAS, VERDADERAS

ANCHO, ALTO = 1280, 720
DURACION = 55.0
COMBO_SEG = 1.6
FIEBRE_COMBO = 8
FIEBRE_SEG = 7.0
SALUD_MAX = 100


@dataclass(frozen=True)
class Version:
    """Lo que dice una publicación (el árbol del rumor guarda una por nodo)."""
    texto: str
    distorsiones: tuple = ()


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
    senales: tuple = ()
    hecho: str = ""
    autor: str = ""
    look: dict = field(default_factory=dict)
    especial: str = ""
    vida: int = 1
    viral: bool = False
    origen: bool = False
    copia_de: str = ""
    enviado_por: str = ""     # en duelo: quién te la mandó
    marca: bool = False       # en el tutorial viene marcada (córtala / déjala)
    bus: bool = False         # va de lado a lado sin caer
    del_jefe: bool = False
    caso: Optional[int] = None
    nodo: Optional[int] = None
    subio: bool = False
    golpe: float = 0.0
    edad: float = 0.0

    @property
    def ancho(self):
        if self.tipo == "especial":
            return 100
        return 330 if self.viral else 300

    @property
    def alto(self):
        if self.tipo == "especial":
            return 100
        return 112 if self.viral else 100


def _parametros(regla: str, infeccion: int) -> dict:
    p = dict(intervalo=1.55, maximo=3, falsas=0.6, nivel_max=1, velocidad=1.0, origen=0.15, viral=0.0,
             grupo=1, buses=0.0, viento=False, dano=12, combo_x=1)
    if regla == "tutorial":
        p.update(intervalo=1.9, maximo=2, origen=0.0, dano=7)
    elif regla == "cadenas":
        p.update(origen=0.5, nivel_max=2)
    elif regla == "grupos":
        p.update(grupo=3, intervalo=3.4, maximo=5, nivel_max=2)
    elif regla == "recreo":
        p.update(velocidad=1.22, intervalo=1.3, nivel_max=2)
    elif regla == "viento":
        p.update(viento=True, nivel_max=2)
    elif regla == "buses":
        p.update(buses=0.35, nivel_max=3)
    elif regla == "avalancha":
        p.update(intervalo=0.75, maximo=6, combo_x=2, nivel_max=3)
    elif regla == "cero":
        p.update(dano=24, maximo=2, intervalo=1.7, nivel_max=3)
    elif regla == "jefe":
        p.update(nivel_max=3, intervalo=3.0, maximo=2, falsas=0.0)
    # La infección del barrio (cuánto rumor le llegó por el mapa) lo pone más difícil.
    p["maximo"] += infeccion
    p["intervalo"] = max(0.6, p["intervalo"] - 0.12 * infeccion)
    p["nivel_max"] = min(3, p["nivel_max"] + (1 if infeccion >= 2 else 0))
    p["viral"] = 0.05 * infeccion
    return p


class Nivel:
    def __init__(self, zona: str, jugador: dict, semilla: Optional[int] = None, red=None, mejoras=None,
                 infeccion: int = 0, duracion: float = DURACION, tranquilo: bool = False):
        self.zona = zona
        self.regla = BARRIOS_JUEGO.get(zona, BARRIOS_JUEGO["PLAZA"])["regla"]
        self.jugador = dict(jugador)
        self.rol = jugador.get("rol", "periodista")
        self.semilla = semilla if semilla is not None else random.randrange(1 << 30)
        self.rng = random.Random(self.semilla)
        self.red = red
        self.mejoras = dict(mejoras or {})
        self.infeccion = infeccion
        self.duracion = duracion
        self.tranquilo = tranquilo
        self.p = _parametros(self.regla, infeccion)
        self.calma = 1.0 - 0.08 * self.mejoras.get("calma", 0) - (0.18 if tranquilo else 0.0)
        self.salud_max = SALUD_MAX + 10 * self.mejoras.get("corazon", 0)
        self.salud = self.salud_max
        self.tiempo = 0.0
        self.reloj = 0.0
        self.estado = "jugando"       # jugando | ganado | perdido
        self.pubs: list[Pub] = []
        self.eventos: list[dict] = []
        self.arboles: dict[int, ArbolMutaciones] = {}
        self.combo = 0
        self.mejor_combo = 0
        self.ultimo_corte = -10.0
        self.fiebre = 0.0
        self.lento = 0.0
        self.escudo = 0
        self.energia = 0.0
        self.viento = 0.0
        self.prox_viento = 4.0
        self.prox = 1.2
        self.prox_especial = 9.0
        self.puntos = 0
        self.monedas = 0
        self.cortadas = 0
        self.errores = 0
        self.caidas = 0
        self.salvadas = 0
        self.senales_vistas: list[str] = []
        self.hechos: list[str] = []
        self.ataques_enviados = 0
        self._sig = 1
        self._sig_caso = 1
        self._marcadas = 0
        self._mazo_f, self._mazo_v = [], []
        self.jefe = dict(hp=100.0, x=ANCHO / 2, y=235.0, fase=1, t=0.0, golpe=0.0, apagon=0.0, prox_apagon=14.0,
                         prox=1.5) if self.regla == "jefe" else None

    # -------------------------------------------------------------- utilidades
    def evento(self, **kw):
        kw["t"] = self.tiempo
        self.eventos.append(kw)

    def _autor(self):
        """Quién publica: un vecino de este barrio (o de cualquier parte) en la red social."""
        if self.red is not None:
            gente = [v for v in self.red.vertices() if self.red.dato(v).jugador is None and not self.red.dato(v).bot]
            del_barrio = [v for v in gente if self.red.dato(v).zona == self.zona]
            v = self.rng.choice(del_barrio if del_barrio and self.rng.random() < 0.7 else gente)
            return v, self.red.dato(v).look
        return "", {}

    def _carta(self, mazo, lista, filtro):
        candidatas = [c for c in lista if filtro(c)]
        if not mazo:
            mazo.extend(range(len(lista)))
            self.rng.shuffle(mazo)
        for i, k in enumerate(mazo):
            if lista[k] in candidatas:
                return lista[mazo.pop(i)]
        return lista[mazo.pop()]

    def _nueva(self, tipo, x=None, y=None, vx=None, vy=None, **kw) -> Pub:
        vel = self.p["velocidad"] * self.calma
        if x is None:
            carril = self.rng.randrange(4)
            x = 190 + carril * (ANCHO - 380) / 3 + self.rng.uniform(-50, 50)
        if vx is None:
            vx = (ANCHO / 2 - x) * self.rng.uniform(0.03, 0.12) + self.rng.uniform(-25, 25)
        if vy is None:
            vy = -self.rng.uniform(700, 770)
        p = Pub(self._sig, tipo, kw.pop("fuente", ""), kw.pop("texto", ""), x, ALTO + 70 if y is None else y,
                vx * vel, vy * vel, rot=self.rng.uniform(-4, 4), vrot=self.rng.uniform(-4, 4), **kw)
        if not p.autor and tipo != "especial":
            p.autor, p.look = self._autor()
        self._sig += 1
        self.pubs.append(p)
        return p

    def _lanzar_falsa(self, x=None, **kw):
        nmax = self.p["nivel_max"]
        f, t, nivel, senales, barrio = self._carta(
            self._mazo_f, FALSAS, lambda c: c[2] <= nmax and (c[4] in (None, self.zona) or self.rng.random() < 0.3))
        viral = self.rng.random() < self.p["viral"]
        origen = not viral and self.rng.random() < self.p["origen"]
        marca = self.regla == "tutorial" and self._marcadas < 8
        p = self._nueva("falsa", x, fuente=f, texto=t, nivel=nivel, senales=senales, vida=3 if viral else 1,
                        viral=viral, origen=origen, marca=marca, **kw)
        self._marcadas += marca
        if origen or viral:
            raiz = NodoMutacion(Version(t, ("falsa",)), p.autor or "anónimo", 0, alcance=0)
            self.arboles[self._sig_caso] = ArbolMutaciones(t, raiz)
            p.caso, p.nodo = self._sig_caso, raiz.id
            self._sig_caso += 1
        return p

    def _lanzar_verdad(self, x=None, **kw):
        f, t, hecho, barrio = self._carta(self._mazo_v, VERDADERAS,
                                          lambda c: c[3] in (None, self.zona) or self.rng.random() < 0.3)
        marca = self.regla == "tutorial" and self._marcadas < 8
        self._marcadas += marca
        return self._nueva("verdad", x, fuente=f, texto=t, hecho=hecho, marca=marca, **kw)

    def _tanda(self):
        vivas = sum(1 for p in self.pubs if p.tipo != "especial")
        if vivas >= self.p["maximo"]:
            self.prox = 0.3
            return
        n = min(self.p["grupo"], self.p["maximo"] - vivas)
        carriles = self.rng.sample(range(4), min(4, n))
        for c in carriles:
            x = 190 + c * (ANCHO - 380) / 3 + self.rng.uniform(-40, 40)
            if self.p["buses"] and self.rng.random() < self.p["buses"]:
                self._bus()
                continue
            if self.rng.random() < self.p["falsas"]:
                self._lanzar_falsa(x)
            else:
                self._lanzar_verdad(x)
        self.prox = self.p["intervalo"] * self.rng.uniform(0.8, 1.2) / max(0.6, self.calma)

    def _bus(self):
        lado = self.rng.choice((-1, 1))
        y = self.rng.uniform(250, 430)
        x = -180 if lado > 0 else ANCHO + 180
        vel = 150 * self.calma
        if self.rng.random() < 0.65:
            p = self._lanzar_falsa(x, y=y, vx=lado * vel, vy=0.0)
        else:
            p = self._lanzar_verdad(x, y=y, vx=lado * vel, vy=0.0)
        p.bus, p.subio, p.rot, p.vrot = True, True, 0.0, 0.0

    def _especial(self):
        e = self.rng.choice(list(ESPECIALES))
        self._nueva("especial", especial=e, texto=ESPECIALES[e]["texto"])

    def recibir_ataque(self, de: str):
        """En el duelo: un rival hizo un combo y te mandó un rumor extra."""
        p = self._lanzar_falsa(enviado_por=de)
        p.nivel = max(p.nivel, 2)
        self.evento(t_="ataque_recibido", de=de, x=p.x)

    # -------------------------------------------------------------- cortar
    def cortar(self, a, b) -> int:
        if self.estado != "jugando":
            return 0
        margen = 6 * self.mejoras.get("filo", 0)
        cortadas = []
        for p in list(self.pubs):
            if p not in self.pubs or not _toca(a, b, p, margen):
                continue
            if p.vida > 1:
                p.vida -= 1
                p.golpe = 0.25
                self.evento(t_="golpe", x=p.x, y=p.y)
                continue
            cortadas.append(p)
            self._cortar(p, (b[0] - a[0], b[1] - a[1]))
        falsas = [p for p in cortadas if p.tipo == "falsa"]
        if len(falsas) >= 2:
            extra = 15 * (len(falsas) - 1) * (2 if self.rol == "influencer" else 1)
            self._sumar(extra)
            self.evento(t_="multi", n=len(falsas), x=falsas[-1].x, y=falsas[-1].y, puntos=extra)
        return len(cortadas)

    def _sumar(self, pts):
        pts = pts * (2 if self.fiebre > 0 else 1)
        self.puntos += pts
        return pts

    def _cortar(self, p: Pub, direccion):
        self.pubs.remove(p)
        if p.tipo == "especial":
            self._usar_especial(p)
            self.evento(t_="corte", pub=p, dir=direccion, bien=True)
            return
        if p.tipo == "verdad":
            self._dano(10, p.x)
            self.combo = 0
            self.errores += 1
            self.evento(t_="corte", pub=p, dir=direccion, bien=False)
            self.evento(t_="error", x=p.x, y=p.y, fuente=p.fuente)
            return
        if self.tiempo - self.ultimo_corte < COMBO_SEG:
            self.combo += 1
        else:
            self.combo = 1
        self.ultimo_corte = self.tiempo
        self.mejor_combo = max(self.mejor_combo, self.combo)
        base = 10 + 5 * min(self.combo - 1, 10) * self.p["combo_x"] + (30 if p.viral else 0) + 5 * (p.nivel - 1)
        pts = self._sumar(base)
        self.cortadas += 1
        self.energia = min(1.0, self.energia + 0.12 * (1 + 0.25 * self.mejoras.get("energia", 0)))
        for s in p.senales:
            if s not in self.senales_vistas:
                self.senales_vistas.append(s)
        self.evento(t_="corte", pub=p, dir=direccion, bien=True, puntos=pts, combo=self.combo)
        if self.combo == FIEBRE_COMBO:
            self.fiebre = FIEBRE_SEG
            self.evento(t_="fiebre")
        if self.combo and self.combo % 5 == 0:
            self.ataques_enviados += 1
            self.evento(t_="ataque", combo=self.combo)
        if p.caso is not None:
            self._podar(p)
        if p.del_jefe and self.jefe:
            self._herir_jefe(10 if p.viral else 3.4)

    def _podar(self, p: Pub):
        """Cortar un rumor tumba todas las copias que salieron de él: se poda su subárbol."""
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
            self.cortadas += len(caidas)
            self.evento(t_="cadena", n=len(caidas), x=p.x, y=p.y, puntos=extra)

    def _reenviar(self, p: Pub):
        """Un ORIGEN llegó arriba sin cortar: lo reenvían sus seguidores (grafo social) y nacen hijos en el árbol."""
        arbol = self.arboles.get(p.caso)
        if arbol is None or p.nodo not in arbol:
            return
        seguidores = []
        if self.red is not None and p.autor in self.red:
            seguidores = sorted(self.red.vecinos(p.autor).items(), key=lambda x: -x[1]["peso"])
            seguidores = [v for v, _ in seguidores if self.red.dato(v).jugador is None][:2]
        while len(seguidores) < 2:
            seguidores.append("")
        for lado, quien in zip((-1, 1), seguidores):
            hijo = arbol.insertar(p.nodo, NodoMutacion(Version(p.texto, ("falsa",)), quien or "anónimo", 0, alcance=0))
            look = self.red.dato(quien).look if quien and self.red is not None else {}
            c = Pub(self._sig, "falsa", p.fuente, p.texto, p.x, p.y, p.vx + lado * 150, -180,
                    rot=p.rot, vrot=lado * 5, nivel=p.nivel, senales=p.senales, autor=quien, look=look,
                    copia_de=p.autor or "alguien", caso=p.caso, nodo=hijo.id, subio=True)
            self._sig += 1
            self.pubs.append(c)
        self.evento(t_="copia", x=p.x, y=p.y, autor=p.autor, a=[s for s in seguidores if s])

    def _usar_especial(self, p: Pub):
        e = p.especial
        if e == "moneda":
            self.monedas += 5
        elif e == "corazon":
            self.salud = min(self.salud_max, self.salud + 15)
        elif e == "reloj":
            self.lento = max(self.lento, 5.0)
        self.evento(t_="especial", especial=e, x=p.x, y=p.y)

    def usar_poder(self) -> bool:
        if self.estado != "jugando" or self.energia < 1.0:
            self.evento(t_="sin_poder")
            return False
        self.energia = 0.0
        if self.rol == "periodista":
            self.lento = 6.0
        elif self.rol == "influencer":
            falsas = [q for q in self.pubs if q.tipo == "falsa"]
            for q in falsas:
                self.pubs.remove(q)
                self.cortadas += 1
                self.evento(t_="corte", pub=q, dir=(0, -1), bien=True, cadena=True)
                if q.del_jefe and self.jefe:
                    self._herir_jefe(3)
            self._sumar(15 * len(falsas))
        elif self.rol == "ciudadano":
            self.escudo = 3
        elif self.rol == "candidato":
            self.salud = min(self.salud_max, self.salud + 30)
        self.evento(t_="poder", rol=self.rol)
        return True

    # -------------------------------------------------------------- daño y caídas
    def _dano(self, n, x):
        self.salud = max(0, self.salud - n)
        self.evento(t_="dano", n=n, x=x)

    def _cae(self, p: Pub):
        if p.tipo == "falsa":
            if self.escudo > 0:
                self.escudo -= 1
                self.evento(t_="bloqueo", x=p.x)
                return
            self.caidas += 1
            self.combo = 0
            self._dano(25 if p.viral else self.p["dano"], p.x)
            self.evento(t_="cae", x=p.x, viral=p.viral)
        elif p.tipo == "verdad":
            self.salvadas += 1
            self.salud = min(self.salud_max, self.salud + 4)
            if p.hecho and p.hecho not in self.hechos:
                self.hechos.append(p.hecho)
            self._sumar(3)
            self.evento(t_="salva", x=p.x)

    # -------------------------------------------------------------- jefe final
    def _herir_jefe(self, n):
        j = self.jefe
        j["hp"] = max(0.0, j["hp"] - n)
        j["golpe"] = 0.3
        self.evento(t_="jefe_herido", hp=j["hp"])
        if j["hp"] <= 66 and j["fase"] == 1:
            j["fase"] = 2
            self.evento(t_="jefe_fase", fase=2, texto="¡Lluvia de bots!")
        elif j["hp"] <= 33 and j["fase"] == 2:
            j["fase"] = 3
            self.evento(t_="jefe_fase", fase=3, texto="¡Apagón! Solo ves cerca del cursor")

    def _actualizar_jefe(self, dt):
        j = self.jefe
        j["t"] += dt
        j["golpe"] = max(0.0, j["golpe"] - dt)
        j["x"] = ANCHO / 2 + math.sin(j["t"] * 0.6) * 340
        j["apagon"] = max(0.0, j["apagon"] - dt)
        if j["fase"] == 3:
            j["prox_apagon"] -= dt
            if j["prox_apagon"] <= 0:
                j["apagon"] = 5.0
                j["prox_apagon"] = 13.0
                self.evento(t_="apagon")
        j["prox"] -= dt
        vivas = sum(1 for p in self.pubs if p.del_jefe)
        limite = {1: 3, 2: 5, 3: 4}[j["fase"]]
        if j["prox"] <= 0 and vivas < limite:
            n = 3 if j["fase"] == 2 else 1
            for _ in range(n):
                vx = self.rng.uniform(-230, 230)
                p = self._lanzar_falsa(j["x"] + self.rng.uniform(-40, 40), y=j["y"] + 60, vx=vx,
                                       vy=self.rng.uniform(-260, -120), del_jefe=True)
                p.subio = False
            self.evento(t_="jefe_lanza", x=j["x"])
            j["prox"] = {1: 1.5, 2: 2.6, 3: 1.2}[j["fase"]] / max(0.6, self.calma)
        if j["hp"] <= 0 and self.estado == "jugando":
            self.estado = "ganado"
            self.evento(t_="jefe_cae", x=j["x"], y=j["y"])

    # -------------------------------------------------------------- bucle
    def actualizar(self, dt: float):
        if self.estado != "jugando":
            return
        dt = min(dt, 0.05)
        self.tiempo += dt
        self.reloj += dt
        self.fiebre = max(0.0, self.fiebre - dt)
        self.lento = max(0.0, self.lento - dt)
        if self.tiempo - self.ultimo_corte > COMBO_SEG and self.combo:
            self.combo = 0
        vel = self.p["velocidad"] * self.calma
        g = 420.0 * vel * vel
        mdt = dt * (0.4 if self.lento > 0 else 1.0)
        if self.p["viento"]:
            self.prox_viento -= dt
            if self.prox_viento <= 0:
                self.viento = self.rng.choice((-1, 1)) * self.rng.uniform(70, 150)
                self.prox_viento = self.rng.uniform(5, 8)
                self.evento(t_="viento", fuerza=self.viento)
        for p in list(self.pubs):
            p.edad += dt
            p.golpe = max(0.0, p.golpe - dt)
            if not p.bus:
                p.vy += g * mdt
                p.vx += self.viento * mdt * 0.6
            p.x += p.vx * mdt
            p.y += p.vy * mdt
            p.rot += p.vrot * mdt
            if not p.bus and (p.x < 70 or p.x > ANCHO - 70):
                p.vx = -p.vx * 0.5
                p.x = max(70, min(ANCHO - 70, p.x))
            if not p.subio and p.vy >= 0:
                p.subio = True
                if p.origen:
                    self._reenviar(p)
            fuera = (p.bus and (p.x < -220 or p.x > ANCHO + 220)) or (p.subio and p.y > ALTO + 80)
            if fuera:
                self.pubs.remove(p)
                self._cae(p)
        if self.jefe:
            self._actualizar_jefe(dt)
        termina = self.reloj >= self.duracion and not self.jefe
        if not termina:
            self.prox -= dt
            if self.prox <= 0:
                if self.jefe:
                    self._lanzar_verdad()
                    self.prox = self.p["intervalo"] * self.rng.uniform(0.8, 1.3)
                else:
                    self._tanda()
            self.prox_especial -= dt
            if self.prox_especial <= 0:
                self._especial()
                self.prox_especial = self.rng.uniform(9, 14)
        if self.salud <= 0:
            self.estado = "perdido"
            self.evento(t_="perdido")
        elif termina and not any(p.tipo != "especial" for p in self.pubs):
            self.estado = "ganado"
            self.evento(t_="ganado")

    # -------------------------------------------------------------- resultado
    def estrellas(self) -> int:
        if self.estado != "ganado":
            return 0
        frac = self.salud / self.salud_max
        if frac >= 0.85 and self.errores == 0:
            return 3
        if frac >= 0.6:
            return 2
        return 1

    def resultado(self) -> dict:
        estrellas = self.estrellas()
        monedas = self.monedas + estrellas * 10 + self.puntos // 60
        monedas = round(monedas * (1 + 0.25 * self.mejoras.get("iman", 0)))
        return dict(zona=self.zona, estado=self.estado, estrellas=estrellas, puntos=self.puntos, monedas=monedas,
                    cortadas=self.cortadas, errores=self.errores, caidas=self.caidas, salvadas=self.salvadas,
                    salud=round(100 * self.salud / self.salud_max), mejor_combo=self.mejor_combo,
                    senales=list(self.senales_vistas), hechos=list(self.hechos))


def _toca(a, b, p: Pub, margen: float = 0.0) -> bool:
    """¿El trazo a-b atraviesa la tarjeta (rectángulo girado)? Liang-Barsky en coordenadas de la tarjeta."""
    ang = math.radians(p.rot)
    c, s = math.cos(-ang), math.sin(-ang)

    def local(q):
        dx, dy = q[0] - p.x, q[1] - p.y
        return dx * c - dy * s, dx * s + dy * c

    (x0, y0), (x1, y1) = local(a), local(b)
    hw, hh = p.ancho / 2 + margen, p.alto / 2 + margen
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

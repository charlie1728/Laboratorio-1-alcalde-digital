"""Simulación de Ciudad Nova en tiempo real (sin pygame: se puede correr en el servidor).

Cómo se usan las estructuras:
  * Red social (grafo dirigido y ponderado por confianza): cada vecino que tiene una publicación
    se la manda a sus seguidores cada pocos segundos. Quien ya la recibió no la vuelve a recibir,
    así que la propagación es un BFS que avanza en vivo, ola por ola.
  * Árbol de mutaciones: cada reenvío se inserta como hijo de la publicación que lo originó, y a
    veces cambia (cifra inflada, fuente inventada...). Reportar poda un subárbol; rastrear sube
    hasta la raíz.
  * Archivo de hechos (AVL): escanear una publicación busca el hecho oficial; si no estaba, se
    investiga y se inserta (con rotaciones).
  * Mapa (grafo no dirigido, minutos): los vecinos caminan de una zona a otra por la ruta más
    corta (Dijkstra) y las discusiones contagian tensión a las zonas cercanas (BFS por niveles).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

from ..estructuras.archivo_avl import ArchivoHechosAVL
from ..estructuras.arbol_mutaciones import ArbolMutaciones, NodoMutacion
from ..estructuras.grafo import Grafo
from ..modelo.afirmacion import DISTORSIONES
from ..modelo.apariencia import look_aleatorio, normalizar
from ..modelo.hechos import CANDIDATOS, catalogo
from ..modelo.mapa import ZONAS, crear_mapa, nombre_zona
from ..modelo.red_social import BOTS, Ciudadano, conectar_jugador, generar_red, residentes
from . import geometria as geo

DIAS = 5
DIA_SEG = 100.0
RADIO_ACCION = 1.35
VEL_JUGADOR = 3.4
VEL_VECINO = 1.25
VEL_PAQUETE = 5.5
T_ESCANEO = 1.0
VIRAL_SEG = 10.0
MAX_NODOS_CASO = 40
PROF_MAX = 8
FACTOR_REENVIO = {"falso": 1.5, "veraz": 0.75, "correccion": 0.6}
UMBRAL_CONFIANZA = 0.12

PODERES = {
    "periodista": dict(nombre="Rastrear origen", recarga=22.0,
                       ayuda="Sube por el árbol del rumor hasta quien lo inventó y lo tumba entero."),
    "influencer": dict(nombre="Megáfono", recarga=18.0,
                       ayuda="Una onda de verdad recorre 2 saltos de tu red y corrige a quien creía mentiras."),
    "ciudadano": dict(nombre="Alerta a mis contactos", recarga=14.0,
                      ayuda="Tus contactos dejan de creer lo falso y quedan protegidos."),
    "candidato": dict(nombre="Discurso", recarga=18.0,
                      ayuda="Calma la zona donde estás y convence a quien confía en ti."),
}

LOGROS = {
    "Primer escaneo": "Escaneaste tu primera publicación.",
    "Investigador": "Registraste un hecho nuevo en el Archivo.",
    "Poda limpia": "Tumbaste 5 o más publicaciones de un solo reporte.",
    "Sangre fría": "Frenaste un rumor viral antes de que estallara.",
    "Paciente cero": "Llegaste hasta quien inventó un rumor.",
    "Caza-bots": "Hiciste que Civitas suspendiera una cuenta bot.",
    "Voz de la verdad": "Lo que compartiste le llegó a 6 o más personas.",
    "Mano limpia": "Terminaste sin compartir nada falso.",
}


@dataclass
class Vecino:
    nombre: str
    x: float
    y: float
    ruta: list = field(default_factory=list)
    espera: float = 0.0
    dir: int = 1
    paso: float = 0.0
    moviendo: bool = False
    enojo: float = 0.0          # segundos que le quedan de discusión
    destello: tuple = None      # (tipo, segundos)


@dataclass
class Jugador:
    idx: int
    nombre: str
    rol: str
    color: tuple
    look: dict
    x: float
    y: float
    puntos: int = 0
    recarga: float = 0.0
    dir: int = 1
    paso: float = 0.0
    moviendo: bool = False
    escaneo: float = 0.0
    objetivo: Optional[str] = None
    candidato: Optional[str] = None
    logros: list = field(default_factory=list)
    stats: dict = field(default_factory=lambda: dict(escaneos=0, reportes=0, falsos=0, corregidos=0,
                                                     compartidos=0, poderes=0))
    entrada: dict = field(default_factory=lambda: dict(dx=0.0, dy=0.0, escanear=False))
    espera: float = 0.0          # pausa corta entre botones para que no se repitan solos

    def logro(self, nombre) -> bool:
        if nombre not in self.logros:
            self.logros.append(nombre)
            return True
        return False


@dataclass
class Caso:
    id: int
    hecho: object
    arbol: ArbolMutaciones
    receptores: dict = field(default_factory=dict)     # visitados del BFS: quién la recibió y por qué nodo
    creencia: dict = field(default_factory=dict)       # "falso" | "veraz" | "duda" | "corregido"
    activo: bool = True
    revelado: bool = False                             # alguien ya descubrió si es verdad o mentira
    compartido_por: set = field(default_factory=set)

    def creyentes_falso(self):
        return [c for c, e in self.creencia.items() if e == "falso"]


@dataclass
class Portador:
    """Un vecino que tiene una publicación y la va a mandar a sus seguidores cuando se le acabe el tiempo."""
    caso: int
    nodo: int
    falta: float
    total: float
    viral: bool = False


@dataclass
class Paquete:
    """Una publicación viajando por una arista de la red social."""
    caso: int
    nodo: int
    de: str
    a: str
    t: float
    dur: float
    factor: float = 1.0
    jugador: Optional[int] = None


class Mundo:
    def __init__(self, config: list, semilla: Optional[int] = None, dias: int = DIAS, dia_seg: float = DIA_SEG):
        self.rng = random.Random(semilla)
        self.dias, self.dia_seg = dias, dia_seg
        self.dia = 1
        self.reloj = 0.0
        self.tiempo = 0.0
        self.estado = "jugando"          # jugando | noche | eleccion
        self.mapa = crear_mapa()
        nombres = [c["nombre"] for c in config]
        self.red: Grafo = generar_red(self.rng, self.mapa, set(nombres))
        self.vecinos: dict[str, Vecino] = {}
        for v in self.red.vertices():
            d = self.red.dato(v)
            x, y = self.rng.choice(geo.ESPERA[d.zona])
            self.vecinos[v] = Vecino(v, x + self.rng.uniform(-0.2, 0.2), y + self.rng.uniform(-0.2, 0.2),
                                     espera=self.rng.uniform(0.5, 4))
        self.jugadores: list[Jugador] = []
        libres = [c[0] for c in CANDIDATOS]
        for i, c in enumerate(config):
            look = normalizar(c.get("look")) if c.get("look") else look_aleatorio(self.rng, i % 2 == 0)
            cz = conectar_jugador(self.red, self.mapa, self.rng, c["nombre"], i, c["rol"], look)
            x, y = geo.ESPERA[cz.zona][-1]
            j = Jugador(i, c["nombre"], c["rol"], tuple(c.get("color", (255, 194, 61))), look, x, y)
            if j.rol == "candidato" and libres:
                j.candidato = libres.pop(0)
            self.jugadores.append(j)
        self.hechos = {h.id: h for h in catalogo()}
        self.archivo = ArchivoHechosAVL()
        for h in self.hechos.values():
            if h.en_archivo:
                self.archivo.insertar(h.id, h)
        self.archivo.bitacora.clear()
        self.casos: list[Caso] = []
        self.portadores: dict[str, Portador] = {}
        self.paquetes: list[Paquete] = []
        self.prevenidos: dict[str, float] = {}           # vecino -> segundos protegido
        self.tension_extra = {z: 0.0 for z in ZONAS}
        self.aristas_rotas: list[tuple] = []
        self.apoyo_zona = {z: {c[0]: 0.0 for c in CANDIDATOS} for z in ZONAS}
        self.indicadores = dict(info_verificada=50, confianza=60, convivencia=70, bienestar=65,
                                desinformacion=10, conflictos=10)
        self.historial = []
        self.fx: list[dict] = []         # efectos para la pantalla (los consume el dibujo)
        self.log_items: list[dict] = []  # mensajes para el jugador
        self.viral: Optional[str] = None
        self.prox_evento = 9.0
        self._sig_caso = 1
        self._bots = 0
        self.resumen_dia: Optional[dict] = None
        self.eleccion: Optional[dict] = None
        self._recalc = 0.0
        self._empezar_dia()
        self._nuevo_caso(falso=True)
        self._nuevo_caso(falso=False)
        self._recalcular()

    def _empezar_dia(self):
        self.hoy = dict(escaneos=0, retiradas=0, corregidos=0, estallidos=0, falsos_regados=0, bots=0)
        self._puntos_dia = {j.nombre: j.puntos for j in self.jugadores}

    # ------------------------------------------------------------------ utilidades
    def log(self, texto, tipo="info", jugador=None):
        self.log_items.append(dict(texto=texto, tipo=tipo, t=self.tiempo, jugador=jugador))
        del self.log_items[:-30]

    def efecto(self, **kw):
        kw["t"] = self.tiempo
        self.fx.append(kw)

    def es_npc(self, v):
        d = self.red.dato(v) if v in self.red else None
        return d is not None and d.jugador is None

    def npcs(self):
        return [v for v in self.red.vertices() if self.es_npc(v) and not self.red.dato(v).bot]

    def caso(self, cid) -> Optional[Caso]:
        for c in self.casos:
            if c.id == cid:
                return c
        return None

    def nodo(self, cid, nid) -> Optional[NodoMutacion]:
        c = self.caso(cid)
        return c.arbol.buscar(nid) if c and c.arbol.raiz else None

    def pos(self, nombre):
        """Dónde está alguien (vecino o jugador)."""
        if nombre in self.vecinos:
            v = self.vecinos[nombre]
            return v.x, v.y
        for j in self.jugadores:
            if j.nombre == nombre:
                return j.x, j.y
        return None

    def jugador(self, nombre) -> Optional[Jugador]:
        for j in self.jugadores:
            if j.nombre == nombre:
                return j
        return None

    def estado_vecino(self, v) -> str:
        """Qué cree un vecino: falso domina, luego corregido, luego veraz."""
        estados = [c.creencia.get(v) for c in self.casos]
        for e in ("falso", "corregido", "veraz", "duda"):
            if e in estados:
                return e
        return "nada"

    @staticmethod
    def tipo_nodo(n: NodoMutacion) -> str:
        return "correccion" if n.es_correccion else "veraz" if n.es_veraz else "falso"

    # ------------------------------------------------------------------ casos y propagación
    def casos_activos(self):
        return [c for c in self.casos if c.activo and c.arbol.raiz is not None]

    def _nuevo_caso(self, falso: bool, sobre_candidato=False, autor=None, viral=False) -> Optional[Caso]:
        usados = {c.hecho.id for c in self.casos_activos()}
        libres = [h for h in self.hechos.values() if h.id not in usados]
        if sobre_candidato:
            libres = [h for h in libres if any(c[0] in s for s in h.sujetos_falsos for c in CANDIDATOS)] or libres
        if not libres:
            return None
        hecho = self.rng.choice(libres)
        af = hecho.afirmacion_real()
        dist = None
        if falso:
            ops = af.posibles_distorsiones(hecho)
            if sobre_candidato and "atribucion" in ops:
                elegidas = ["atribucion"] + self.rng.sample([o for o in ops if o != "atribucion"], 1)
            else:
                elegidas = self.rng.sample(ops, min(2, len(ops)))
            for d in elegidas:
                af = af.mutar(d, hecho, self.rng)
            dist = "+".join(af.distorsiones)
        if autor is None:
            gente = [v for v in self.npcs() if v not in self.portadores]
            if not gente:
                return None
            pesos = [(self.red.dato(v).credulidad if falso else 0.5) * (1 + self.red.grado_salida(v)) for v in gente]
            autor = self.rng.choices(gente, pesos)[0]
        raiz = NodoMutacion(af, autor, self.dia, distorsion=dist, alcance=0)
        caso = Caso(self._sig_caso, hecho, ArbolMutaciones(hecho.titulo, raiz))
        self._sig_caso += 1
        caso.receptores[autor] = raiz.id
        caso.creencia[autor] = "falso" if falso else "veraz"
        self.casos.append(caso)
        self._dar(autor, caso, raiz, viral=viral, primera=True)
        self.efecto(t_="nuevo", quien=autor)
        return caso

    def _intervalo(self, v) -> float:
        d = self.red.dato(v)
        if d.bot:
            return 4.0
        return 5.0 + (1.0 - d.actividad) * 6.0 + self.rng.uniform(0, 1.5)

    def _dar(self, v, caso: Caso, nodo: NodoMutacion, viral=False, primera=False):
        """El vecino v queda con la publicación y la mandará a sus seguidores cuando se le acabe el tiempo."""
        if v in self.portadores or v not in self.red:
            return
        t = VIRAL_SEG if viral else self._intervalo(v) * (1.4 if primera else 1.0)
        self.portadores[v] = Portador(caso.id, nodo.id, t, t, viral)
        if viral:
            self.viral = v

    def _publicar(self, v, p: Portador):
        """El vecino manda la publicación a todos sus seguidores (un paso del BFS)."""
        caso = self.caso(p.caso)
        nodo = caso.arbol.buscar(p.nodo) if caso and caso.arbol.raiz else None
        if nodo is None or v not in self.red:
            return
        nodo.entregado = True
        factor = 2.5 if p.viral else 1.0
        enviados = 0
        for w, a in sorted(self.red.vecinos(v).items(), key=lambda x: -x[1]["peso"]):
            if w in caso.receptores:
                continue
            caso.receptores[w] = nodo.id
            self._enviar(caso, nodo, v, w, factor)
            enviados += 1
        if p.viral:
            self.viral = None
            self.efecto(t_="estallido", quien=v)
            self.hoy["estallidos"] += 1
            self.log(f"¡El rumor viral de {v} estalló y le llegó a {enviados} personas!", "malo")
            self.indicadores["desinformacion"] = min(100, self.indicadores["desinformacion"] + 4)

    def _enviar(self, caso, nodo, de, a, factor=1.0, jugador=None):
        pa, pb = self.pos(de), self.pos(a)
        dist = math.hypot(pa[0] - pb[0], pa[1] - pb[1]) if pa and pb else 3
        self.paquetes.append(Paquete(caso.id, nodo.id, de, a, 0.0, max(0.45, dist / VEL_PAQUETE), factor, jugador))

    def _recibir(self, pq: Paquete):
        caso = self.caso(pq.caso)
        if caso is None or caso.arbol.raiz is None:
            return
        nodo = caso.arbol.buscar(pq.nodo)
        v = pq.a
        if nodo is None or v not in self.red:
            return
        nodo.alcance += 1
        tipo = self.tipo_nodo(nodo)
        d = self.red.dato(v)
        if d.jugador is not None:
            return
        if tipo == "correccion":
            if caso.creencia.get(v) in ("falso", None, "duda"):
                caso.creencia[v] = "corregido"
                self._destello(v, "corrige")
            return
        if v in self.prevenidos:
            caso.creencia[v] = "corregido" if tipo == "falso" else "veraz"
            self._destello(v, "escudo")
            return
        peso = self.red.peso(pq.de, v) if self.red.tiene_arista(pq.de, v) else 0.5
        if tipo == "veraz":
            caso.creencia[v] = "veraz"
            self._destello(v, "veraz")
        else:
            cree = self.rng.random() < d.credulidad * (0.7 + 0.5 * peso)
            caso.creencia[v] = "falso" if cree else "duda"
            self._destello(v, "cree" if cree else "duda")
            if not cree:
                return
        if nodo.inmune or nodo.profundidad + 1 >= PROF_MAX or len(caso.arbol) >= MAX_NODOS_CASO:
            return
        p = min(0.92, peso * (0.35 + d.actividad) * FACTOR_REENVIO[tipo] * pq.factor)
        if v not in self.portadores and self.rng.random() < p:
            hijo = self._reenviar(caso, nodo, v, 0.12 + 0.3 * d.credulidad)
            if hijo is not None:
                self._dar(v, caso, hijo)
                if pq.factor > 1.5:
                    self.portadores[v].falta = min(self.portadores[v].falta, 1.2)

    def _reenviar(self, caso, padre, autor, prob_mutar=0.3, sin_mutar=False) -> Optional[NodoMutacion]:
        if len(caso.arbol) >= MAX_NODOS_CASO:
            return None
        af, dist = padre.afirmacion, None
        if not sin_mutar and not padre.es_correccion and self.rng.random() < prob_mutar:
            ops = af.posibles_distorsiones(caso.hecho)
            if ops:
                dist = self.rng.choice(ops)
                af = af.mutar(dist, caso.hecho, self.rng)
        hijo = NodoMutacion(af, autor, self.dia, dist, 0, es_correccion=padre.es_correccion)
        return caso.arbol.insertar(padre.id, hijo)

    def _destello(self, v, tipo):
        if v in self.vecinos:
            self.vecinos[v].destello = (tipo, 0.8)

    # ------------------------------------------------------------------ jugadores
    def cerca(self, j: Jugador, radio=RADIO_ACCION) -> Optional[str]:
        """El vecino con publicación más cercano al jugador (al que le apunta)."""
        mejor, dmin = None, radio
        for v, p in self.portadores.items():
            if v not in self.vecinos:
                continue
            ve = self.vecinos[v]
            d = math.hypot(ve.x - j.x, ve.y - j.y)
            if d < dmin:
                mejor, dmin = v, d
        return mejor

    def tiempo_escaneo(self, j: Jugador, v: str) -> float:
        p = self.portadores.get(v)
        caso = self.caso(p.caso) if p else None
        base = T_ESCANEO * (0.5 if j.rol == "periodista" else 1.0)
        if caso and caso.hecho.id not in self.archivo:
            base *= 2.2          # hay que investigar: el hecho todavía no está en el Archivo
        return base

    def _actualizar_jugador(self, j: Jugador, dt):
        e = j.entrada
        dx, dy = e.get("dx", 0.0), e.get("dy", 0.0)
        n = math.hypot(dx, dy)
        j.moviendo = n > 0.1
        if j.moviendo:
            dx, dy = dx / max(1, n), dy / max(1, n)
            j.x, j.y = geo.mover(j.x, j.y, dx * VEL_JUGADOR * dt, dy * VEL_JUGADOR * dt)
            sx = dx - dy
            if abs(sx) > 0.05:
                j.dir = 1 if sx > 0 else -1
            j.paso += dt * 10
        j.recarga = max(0.0, j.recarga - dt)
        j.espera = max(0.0, j.espera - dt)
        objetivo = self.cerca(j)
        if objetivo != j.objetivo:
            j.escaneo = 0.0
        j.objetivo = objetivo
        if e.get("escanear") and objetivo:
            p = self.portadores[objetivo]
            nodo = self.nodo(p.caso, p.nodo)
            if nodo is not None and not nodo.verificado:
                j.escaneo += dt / self.tiempo_escaneo(j, objetivo)
                if j.escaneo >= 1.0:
                    j.escaneo = 0.0
                    self._escanear(j, objetivo)
        else:
            j.escaneo = max(0.0, j.escaneo - dt * 2)

    def accion(self, idx: int, que: str):
        """Botones de un toque: 'reportar', 'compartir' o 'poder'."""
        if self.estado != "jugando" or not 0 <= idx < len(self.jugadores):
            return
        j = self.jugadores[idx]
        if j.espera > 0:
            return
        j.espera = 0.35
        if que == "poder":
            return self._poder(j)
        v = self.cerca(j)
        if v is None:
            self.efecto(t_="nada", jugador=idx)
            return
        if que == "reportar":
            self._reportar(j, v)
        elif que == "compartir":
            self._compartir(j, v)

    def _escanear(self, j: Jugador, v: str):
        p = self.portadores[v]
        caso = self.caso(p.caso)
        nodo = caso.arbol.buscar(p.nodo)
        hecho, comps, ruta = self.archivo.buscar(caso.hecho.id)
        if hecho is None:
            self.archivo.insertar(caso.hecho.id, caso.hecho)
            rot = "; ".join(self.archivo.bitacora[-2:]) or "sin rotaciones"
            self.archivo.bitacora.clear()
            self.log(f"{j.nombre} investigó «{caso.hecho.titulo}» y lo registró en el Archivo ({rot}).", "evento", j.idx)
            j.puntos += 3
            self._logro(j, "Investigador")
            hecho, comps, ruta = self.archivo.buscar(caso.hecho.id)
        nodo.verificado = True
        caso.revelado = True
        j.puntos += 2
        j.stats["escaneos"] += 1
        self._logro(j, "Primer escaneo")
        dif = nodo.afirmacion.comparar_con(hecho)
        es_falso = bool(dif) and not nodo.es_correccion
        self.hoy["escaneos"] += 1
        self.efecto(t_="escaneo", quien=v, jugador=j.idx, falso=es_falso, avl=ruta,
                    trucos=[DISTORSIONES[d] for d in dif] if es_falso else [])
        if es_falso:
            trucos = ", ".join(DISTORSIONES[d] for d in dif)
            self.log(f"¡FALSO! {trucos}. Lo real: {hecho.afirmacion_real().texto()}", "malo", j.idx)
        else:
            self.log(f"Es VERDAD: coincide con el Archivo ({comps} comparaciones). ¡Compártela!", "bueno", j.idx)

    def _quitar_portadores(self, caso: Caso, ids: set):
        for v in [v for v, p in self.portadores.items() if p.caso == caso.id and p.nodo in ids]:
            if self.viral == v:
                self.viral = None
            del self.portadores[v]
        self.paquetes = [pq for pq in self.paquetes if not (pq.caso == caso.id and pq.nodo in ids)]

    def _podar(self, caso: Caso, nodo: NodoMutacion) -> tuple[list, int]:
        """Poda el subárbol: quienes recibieron esas versiones reciben el aviso de Civitas."""
        eliminados = caso.arbol.podar(nodo.id)
        ids = {n.id for n in eliminados}
        avisados = []
        for c, nid in caso.receptores.items():
            if nid in ids and caso.creencia.get(c) == "falso":
                caso.creencia[c] = "corregido"
                avisados.append(c)
        for n in eliminados:
            if caso.creencia.get(n.autor) == "falso":
                caso.creencia[n.autor] = "corregido"
                avisados.append(n.autor)
        self._quitar_portadores(caso, ids)
        for a in avisados:
            self._destello(a, "corrige")
        self.hoy["retiradas"] += len(eliminados)
        self.hoy["corregidos"] += len(set(avisados))
        if caso.arbol.raiz is None:
            caso.activo = False
        return eliminados, len(set(avisados))

    def _reportar(self, j: Jugador, v: str):
        p = self.portadores[v]
        caso = self.caso(p.caso)
        nodo = caso.arbol.buscar(p.nodo)
        caso.revelado = True
        if nodo.es_veraz:
            nodo.verificado = True
            j.puntos -= 5
            self._confianza(j.nombre, -0.05)
            self.vecinos[v].enojo = 2.0
            self.efecto(t_="rechazo", quien=v, jugador=j.idx)
            self.log(f"Civitas revisó el reporte de {j.nombre}: ¡era VERDAD! −5. Reportar lo cierto también hace daño.",
                     "malo", j.idx)
            return
        viral = self.viral == v
        autores = [n.autor for n in caso.arbol.preorden(nodo)]
        eliminados, avisados = self._podar(caso, nodo)
        pts = 5 + 2 * len(eliminados)
        j.puntos += pts
        j.stats["reportes"] += 1
        j.stats["corregidos"] += avisados
        self.efecto(t_="poda", quien=v, autores=autores, jugador=j.idx)
        self.log(f"{j.nombre} reportó: Civitas retiró {len(eliminados)} publicaciones y avisó a {avisados} personas. +{pts}",
                 "bueno", j.idx)
        if len(eliminados) >= 5:
            self._logro(j, "Poda limpia")
        if viral:
            j.puntos += 8
            self._logro(j, "Sangre fría")
            self.log(f"¡{j.nombre} frenó el rumor viral a tiempo! +8", "logro", j.idx)
        for bot in {n.autor for n in eliminados if self.red.dato(n.autor) and self.red.dato(n.autor).bot}:
            self._suspender_bot(bot, j)

    def _suspender_bot(self, bot, j):
        seguidores = self.red.grado_salida(bot)
        donde = self.pos(bot)
        self.red.eliminar_vertice(bot)
        self.portadores.pop(bot, None)
        self.vecinos.pop(bot, None)
        self.efecto(t_="bot_fuera", quien=bot, mundo=donde)
        self.hoy["bots"] += 1
        j.puntos += 8
        self._logro(j, "Caza-bots")
        self.log(f"Civitas suspendió la cuenta bot {bot}: ya no le llega nada a sus {seguidores} seguidores. +8",
                 "logro", j.idx)

    def _compartir(self, j: Jugador, v: str):
        p = self.portadores[v]
        caso = self.caso(p.caso)
        nodo = caso.arbol.buscar(p.nodo)
        if j.nombre in caso.compartido_por:
            self.log("Ya compartiste esta noticia: a tus seguidores ya les llegó.", "info", j.idx)
            return
        caso.compartido_por.add(j.nombre)
        nuevo = self._reenviar(caso, nodo, j.nombre, sin_mutar=True)
        if nuevo is None:
            self.log("Ese rumor ya está saturado: nadie más lo ve.", "info", j.idx)
            return
        nuevo.inmune = nodo.inmune
        nuevo.entregado = True
        caso.receptores.setdefault(j.nombre, nodo.id)
        enviados = 0
        for w in sorted(self.red.vecinos(j.nombre), key=lambda w: -self.red.peso(j.nombre, w)):
            if w in caso.receptores:
                continue
            caso.receptores[w] = nuevo.id
            self._enviar(caso, nuevo, j.nombre, w, 1.0, j.idx)
            enviados += 1
        j.stats["compartidos"] += 1
        self.efecto(t_="compartir", jugador=j.idx, falso=not nodo.es_veraz)
        if nodo.es_veraz:
            pts = 4 + 2 * enviados
            j.puntos += pts
            self._confianza(j.nombre, 0.04)
            self.log(f"{j.nombre} compartió una noticia VERDADERA con {enviados} seguidores. +{pts}", "bueno", j.idx)
            if enviados >= 6:
                self._logro(j, "Voz de la verdad")
        else:
            nodo.verificado = nuevo.verificado = True
            caso.revelado = True
            pts = 6 + enviados
            j.puntos -= pts
            j.stats["falsos"] += 1
            self.hoy["falsos_regados"] += 1
            self._confianza(j.nombre, -0.06)
            self.log(f"¡{j.nombre} regó un rumor FALSO a {enviados} seguidores! −{pts}. Escanea antes de compartir.",
                     "malo", j.idx)

    def _confianza(self, origen, delta):
        for w in list(self.red.vecinos(origen)):
            self.red.ajustar_peso(origen, w, delta)

    def _corregir(self, gente, prevenir=False) -> list:
        corregidos = []
        for v in gente:
            if not self.es_npc(v):
                continue
            for c in self.casos:
                if c.creencia.get(v) == "falso":
                    c.creencia[v] = "corregido"
                    if v not in corregidos:
                        corregidos.append(v)
            if prevenir:
                self.prevenidos[v] = 35.0
            self._destello(v, "corrige" if v in corregidos else "escudo")
        return corregidos

    def _poder(self, j: Jugador):
        if j.recarga > 0:
            self.efecto(t_="recargando", jugador=j.idx)
            return
        ok = getattr(self, "_p_" + j.rol)(j)
        if ok:
            j.recarga = PODERES[j.rol]["recarga"]
            j.stats["poderes"] += 1

    def _p_periodista(self, j):
        v = self.cerca(j, RADIO_ACCION * 1.3)
        if v is None:
            self.log("Rastrear: acércate a alguien que tenga un rumor.", "info", j.idx)
            return False
        p = self.portadores[v]
        caso = self.caso(p.caso)
        nodo = caso.arbol.buscar(p.nodo)
        camino = caso.arbol.camino_a_raiz(nodo.id)
        ruta = [n.autor for n in reversed(camino)]
        caso.revelado = True
        puntos = caso.arbol.punto_de_mutacion(nodo.id)
        if nodo.es_veraz:
            for n in camino:
                n.verificado = True
            self.efecto(t_="rastreo", ruta=ruta, jugador=j.idx, falso=False)
            self.log(f"Rastreo: {len(camino)} saltos hasta el origen y nada torcido. Es una noticia real.", "bueno", j.idx)
            j.puntos += 2
            return True
        origen = min(puntos.values(), key=lambda n: n.profundidad) if puntos else caso.arbol.raiz
        autores = [n.autor for n in caso.arbol.preorden(origen)]
        eliminados, avisados = self._podar(caso, origen)
        if self.es_npc(origen.autor):
            self._confianza(origen.autor, -0.2)
        pts = 6 + 2 * len(eliminados)
        j.puntos += pts
        j.stats["corregidos"] += avisados
        self._logro(j, "Paciente cero")
        self.efecto(t_="rastreo", ruta=ruta, jugador=j.idx, falso=True, autores=autores, origen=origen.autor)
        donde = "desde el ORIGEN" if origen.padre is None else f"en el reenvío de {origen.autor}"
        self.log(f"{j.nombre} rastreó el rumor: se torció {donde}. Cayeron {len(eliminados)} publicaciones. +{pts}",
                 "logro", j.idx)
        return True

    def _p_influencer(self, j):
        niveles = self.red.bfs_niveles(j.nombre, max_nivel=2)
        gente = [v for nivel in niveles[1:] for v in nivel]
        corregidos = self._corregir(gente)
        # Lo que viajaba hacia ellos y ya se sabe que es falso, se frena.
        for c in self.casos_activos():
            ids = [n.id for n in c.arbol.preorden() if n.verificado and not n.es_veraz and n.autor in gente]
            for nid in ids:
                n = c.arbol.buscar(nid)
                if n is not None:
                    c.arbol.inmunizar(nid)
        pts = 4 + 2 * len(corregidos)
        j.puntos += pts
        j.stats["corregidos"] += len(corregidos)
        self.efecto(t_="ondas", jugador=j.idx, niveles=niveles)
        self.log(f"Megáfono de {j.nombre}: la verdad llegó a {len(gente)} personas en 2 saltos y {len(corregidos)} "
                 f"dejaron de creer mentiras. +{pts}", "bueno", j.idx)
        return True

    def _p_ciudadano(self, j):
        contactos = sorted(self.red.contactos(j.nombre), key=str)
        corregidos = self._corregir(contactos, prevenir=True)
        pts = 3 + 2 * len(corregidos)
        j.puntos += pts
        j.stats["corregidos"] += len(corregidos)
        self.efecto(t_="alerta", jugador=j.idx, a=contactos)
        self.log(f"{j.nombre} alertó a sus {len(contactos)} contactos: {len(corregidos)} dejaron de creer el rumor "
                 "y todos quedan protegidos un rato. +" + str(pts), "bueno", j.idx)
        return True

    def _p_candidato(self, j):
        zona = geo.zona_de(j.x, j.y)
        self.tension_extra[zona] = max(0.0, self.tension_extra[zona] - 25)
        if j.candidato:
            self.apoyo_zona[zona][j.candidato] += 6
        confianza, prev = self.red.confianza_maxima(j.nombre)
        gente = [v for v in self.npcs() if confianza.get(v, 0) >= UMBRAL_CONFIANZA] + residentes(self.red, zona)
        corregidos = self._corregir(gente)
        rutas = {v: Grafo.reconstruir(prev, v) for v in corregidos if v in prev}
        pts = 4 + 2 * len(corregidos)
        j.puntos += pts
        j.stats["corregidos"] += len(corregidos)
        self.efecto(t_="discurso", jugador=j.idx, zona=zona, rutas=rutas)
        self.log(f"Discurso de {j.nombre} en {nombre_zona(zona)}: la zona se calma y {len(corregidos)} personas "
                 f"que confían en ti dejaron de creer mentiras. +{pts}", "bueno", j.idx)
        return True

    def _logro(self, j, nombre):
        if j.logro(nombre):
            self.efecto(t_="logro", jugador=j.idx, nombre=nombre)
            self.log(f"¡Logro de {j.nombre}: {nombre}!", "logro", j.idx)

    # ------------------------------------------------------------------ eventos al azar
    def _evento(self):
        hay_portadores = [v for v in self.portadores if self.es_npc(v)]
        opciones = [("falsa", 3), ("candidato", 2), ("verdad", 2), ("discusion", 1.5), ("campana", 1),
                    ("reporte", 1)]
        if hay_portadores and self.viral is None:
            opciones.append(("viral", 2))
        if self._bots < 2:
            opciones.append(("bot", 1.2))
        tipo = self.rng.choices([o[0] for o in opciones], [o[1] for o in opciones])[0]
        getattr(self, "_ev_" + tipo)()

    def _anunciar(self, tipo, titulo, texto, zona=None):
        self.efecto(t_="evento", tipo=tipo, titulo=titulo, texto=texto, zona=zona)
        self.log(f"{titulo}: {texto}", "evento")

    def _ev_falsa(self):
        c = self._nuevo_caso(falso=True)
        if c:
            self._anunciar("falsa", "Apareció un rumor", f"Algo empezó a circular en {nombre_zona(self.red.dato(c.arbol.raiz.autor).zona)}.",
                           self.red.dato(c.arbol.raiz.autor).zona)

    def _ev_candidato(self):
        c = self._nuevo_caso(falso=True, sobre_candidato=True)
        if c:
            self._anunciar("candidato", "Rumor sobre un candidato", "Alguien inventó algo sobre la campaña.",
                           self.red.dato(c.arbol.raiz.autor).zona)

    def _ev_verdad(self):
        c = self._nuevo_caso(falso=False)
        if c:
            self._anunciar("verdad", "Noticia verdadera", "Una noticia real empieza a circular: ayúdala a llegar lejos.",
                           self.red.dato(c.arbol.raiz.autor).zona)

    def _ev_viral(self):
        candidatos = [v for v, p in self.portadores.items() if self.es_npc(v) and not p.viral]
        if not candidatos:
            return self._ev_falsa()
        v = max(candidatos, key=lambda w: self.red.grado_salida(w))
        p = self.portadores[v]
        p.viral, p.falta, p.total = True, VIRAL_SEG, VIRAL_SEG
        self.viral = v
        self._anunciar("viral", "¡ALERTA VIRAL!", f"La publicación de {v} se está regando muy rápido. ¡10 segundos!",
                       self.red.dato(v).zona)

    def _ev_discusion(self):
        zonas = list(ZONAS)
        zona = self.rng.choices(zonas, [1 + self.tension(z) for z in zonas])[0]
        gente = residentes(self.red, zona)
        pares = [(a, b) for a in gente for b in gente if a < b and self.red.tiene_arista(a, b)]
        if not pares:
            pares = [(a, b) for a in gente for b in self.red.vecinos(a) if self.es_npc(b) and a < b]
        extra = ""
        if pares:
            a, b = self.rng.choice(pares)
            antes = len(self.red.componentes_conexas())
            for u, w in ((a, b), (b, a)):
                if self.red.tiene_arista(u, w):
                    self.aristas_rotas.append((u, w, self.red.peso(u, w)))
                    self.red.eliminar_arista(u, w)
            for x in (a, b):
                if x in self.vecinos:
                    self.vecinos[x].enojo = 4.0
            self.efecto(t_="discusion", a=a, b=b)
            extra = f" {a} y {b} dejaron de seguirse."
            if len(self.red.componentes_conexas()) > antes:
                extra += " ¡Se formó una burbuja aislada!"
        _, nivel, _ = self.mapa.bfs(zona, max_nivel=2)
        for z, d in nivel.items():
            self.tension_extra[z] += (24, 12, 6)[d]
        self._anunciar("discusion", "Discusión en " + nombre_zona(zona), "La tensión se contagia a las zonas vecinas." + extra,
                       zona)

    def _ev_campana(self):
        zona = self.rng.choice(list(ZONAS))
        _, nivel, _ = self.mapa.bfs(zona, max_nivel=2)
        for z, d in nivel.items():
            self.tension_extra[z] = max(0.0, self.tension_extra[z] - (20, 10, 5)[d])
        reparadas = 0
        for u, w, p in list(self.aristas_rotas):
            if u in self.red and w in self.red:
                self.red.agregar_arista(u, w, p, tipo="amistad")
                self.aristas_rotas.remove((u, w, p))
                reparadas += 1
        self._anunciar("campana", "Campaña de convivencia digital",
                       f"En {nombre_zona(zona)} la gente se calma." + (" Se reconciliaron amistades." if reparadas else ""),
                       zona)

    def _ev_reporte(self):
        falsos = [(c, n) for c in self.casos_activos() for n in c.arbol.hojas()
                  if not n.es_veraz and not n.es_raiz]
        if not falsos:
            return self._ev_campana()
        c, n = self.rng.choice(falsos)
        quien = self.rng.choice(self.npcs())
        autores = [x.autor for x in c.arbol.preorden(n)]
        self._podar(c, n)
        self.efecto(t_="poda", quien=n.autor, autores=autores, jugador=None)
        self._anunciar("reporte", "Un vecino reportó", f"{quien} reportó una publicación falsa y Civitas la retiró.")

    def _ev_bot(self):
        nombre = next((b for b in BOTS if b not in self.red), None)
        if nombre is None:
            return self._ev_falsa()
        zona = self.rng.choice(list(ZONAS))
        self.red.agregar_vertice(nombre, Ciudadano(nombre, zona, credulidad=1.0, actividad=1.0,
                                                   look={}, bot=True))
        gente = self.npcs()
        for v in self.rng.sample(gente, min(7, len(gente))):
            self.red.agregar_arista(nombre, v, round(self.rng.uniform(0.35, 0.6), 2), tipo="seguimiento")
        x, y = self.rng.choice(geo.ESPERA[zona])
        self.vecinos[nombre] = Vecino(nombre, x, y, espera=999)
        self._bots += 1
        self._nuevo_caso(falso=True, autor=nombre)
        self._anunciar("bot", "Apareció una cuenta bot", f"{nombre} publica mentiras sin parar en {nombre_zona(zona)}. "
                       "Repórtala para que Civitas la suspenda.", zona)

    # ------------------------------------------------------------------ vecinos que caminan
    def _actualizar_vecino(self, v: Vecino, dt):
        if v.enojo > 0:
            v.enojo -= dt
        if v.destello:
            tipo, t = v.destello
            v.destello = (tipo, t - dt) if t - dt > 0 else None
        d = self.red.dato(v.nombre) if v.nombre in self.red else None
        if d is None or d.bot:
            v.moviendo = False
            return
        if v.ruta:
            tx, ty = v.ruta[0]
            dx, dy = tx - v.x, ty - v.y
            dist = math.hypot(dx, dy)
            paso = VEL_VECINO * dt
            if dist <= paso:
                v.x, v.y = tx, ty
                v.ruta.pop(0)
                if not v.ruta:
                    v.espera = self.rng.uniform(2.5, 6.0)
            else:
                nx, ny = geo.mover(v.x, v.y, dx / dist * paso, dy / dist * paso, 0.15)
                if (nx, ny) == (v.x, v.y):          # atascado: salta al siguiente punto
                    v.x, v.y = tx, ty
                    v.ruta.pop(0)
                else:
                    v.x, v.y = nx, ny
                sx = dx - dy
                if abs(sx) > 0.05:
                    v.dir = 1 if sx > 0 else -1
                v.paso += dt * 9
            v.moviendo = True
            return
        v.moviendo = False
        v.espera -= dt
        if v.espera > 0 or v.enojo > 0:
            return
        actual = geo.zona_de(v.x, v.y)
        if actual != d.zona and self.rng.random() < 0.7:
            destino = d.zona                      # vuelve a casa
        elif self.rng.random() < 0.35:
            destino = self.rng.choice(sorted(geo.VECINAS[actual]))
        else:
            destino = actual
        if destino == actual:
            v.ruta = [self.rng.choice(geo.ESPERA[actual])]
        else:
            _, prev = self.mapa.dijkstra(actual)
            zonas = Grafo.reconstruir(prev, destino)[1:]
            v.ruta = [geo.PUERTA[z] for z in zonas[:-1]] + [self.rng.choice(geo.ESPERA[destino])]
        v.ruta = [(x + self.rng.uniform(-0.25, 0.25), y + self.rng.uniform(-0.25, 0.25)) for x, y in v.ruta]

    # ------------------------------------------------------------------ indicadores
    def tension(self, zona) -> int:
        gente = residentes(self.red, zona)
        frac = sum(1 for v in gente if any(c.creencia.get(v) == "falso" for c in self.casos)) / max(1, len(gente))
        return max(0, min(100, round(frac * 70 + self.tension_extra.get(zona, 0))))

    def _recalcular(self):
        gente = self.npcs()
        n = max(1, len(gente))
        falsos = sum(1 for v in gente if self.estado_vecino(v) == "falso")
        bien = sum(1 for v in gente if self.estado_vecino(v) in ("veraz", "corregido"))
        nodos = [nd for c in self.casos_activos() for nd in c.arbol.preorden()]
        verif = sum(1 for nd in nodos if nd.verificado)
        pesos = [a["peso"] for _, _, a in self.red.aristas()]
        conf = sum(pesos) / max(1, len(pesos))
        tension = sum(self.tension(z) for z in ZONAS) / len(ZONAS)
        ind = self.indicadores
        ind["desinformacion"] = round(min(100, 100 * falsos / n * 0.9 + 3 * len(self.portadores_falsos())))
        ind["info_verificada"] = round(min(100, 25 + 45 * verif / max(1, len(nodos)) + 30 * bien / n))
        ind["confianza"] = round(min(100, max(0, (conf - 0.3) / 0.5 * 100)))
        ind["convivencia"] = round(max(0, 100 - tension))
        ind["conflictos"] = round(min(100, 8 * len(self.aristas_rotas) + tension * 0.6))
        ind["bienestar"] = round((ind["convivencia"] + (100 - ind["desinformacion"]) + ind["confianza"]) / 3)

    def portadores_falsos(self):
        res = []
        for v, p in self.portadores.items():
            n = self.nodo(p.caso, p.nodo)
            if n is not None and not n.es_veraz:
                res.append(v)
        return res

    def salud(self) -> int:
        i = self.indicadores
        bueno = (i["info_verificada"] + i["confianza"] + i["convivencia"] + i["bienestar"]) / 4
        malo = (i["desinformacion"] + i["conflictos"]) / 2
        return max(0, min(100, round(bueno * 0.7 + (100 - malo) * 0.3)))

    # ------------------------------------------------------------------ bucle
    def actualizar(self, dt: float):
        if self.estado != "jugando":
            return
        dt = min(dt, 0.1)
        self.tiempo += dt
        self.reloj += dt
        for v in list(self.vecinos.values()):
            self._actualizar_vecino(v, dt)
        for j in self.jugadores:
            self._actualizar_jugador(j, dt)
        for v in list(self.portadores):
            p = self.portadores.get(v)
            if p is None:
                continue
            p.falta -= dt
            if p.falta <= 0:
                del self.portadores[v]
                self._publicar(v, p)
        vivos = []
        for pq in self.paquetes:
            pq.t += dt
            if pq.t >= pq.dur:
                self._recibir(pq)
            else:
                vivos.append(pq)
        self.paquetes = vivos
        for v in list(self.prevenidos):
            self.prevenidos[v] -= dt
            if self.prevenidos[v] <= 0:
                del self.prevenidos[v]
        for z in ZONAS:
            self.tension_extra[z] = max(0.0, self.tension_extra[z] - dt * 0.4)
        self.prox_evento -= dt
        if self.prox_evento <= 0:
            self._evento()
            self.prox_evento = self.rng.uniform(16, 24)
        # Si se apagan todos los rumores, aparece otro: la ciudad nunca se queda quieta.
        if len(self.casos_activos()) < 2 or not self.portadores:
            self._nuevo_caso(falso=self.rng.random() < 0.65)
        self._recalc -= dt
        if self._recalc <= 0:
            self._recalcular()
            self._recalc = 0.5
        if self.reloj >= self.dia_seg:
            self._fin_del_dia()

    def _fin_del_dia(self):
        self._recalcular()
        self.historial.append(dict(self.indicadores, salud=self.salud()))
        self.resumen_dia = dict(dia=self.dia, salud=self.salud(), indicadores=dict(self.indicadores),
                                puntos={j.nombre: j.puntos for j in self.jugadores}, hoy=dict(self.hoy),
                                ganados={j.nombre: j.puntos - self._puntos_dia.get(j.nombre, 0) for j in self.jugadores},
                                creen=sum(1 for v in self.npcs() if self.estado_vecino(v) == "falso"))
        if self.dia >= self.dias:
            for j in self.jugadores:
                if j.stats["falsos"] == 0:
                    self._logro(j, "Mano limpia")
            self.estado = "eleccion"
            self.eleccion = self._votar()
        else:
            self.estado = "noche"

    def siguiente_dia(self):
        if self.estado != "noche":
            return
        self.dia += 1
        self.reloj = 0.0
        self._empezar_dia()
        self.estado = "jugando"
        self.prox_evento = 6.0
        self.paquetes.clear()
        for z in ZONAS:
            self.tension_extra[z] *= 0.5
        self._nuevo_caso(falso=True)

    # ------------------------------------------------------------------ elección
    def _votar(self) -> dict:
        """Cada zona vota. Los rumores que sus vecinos creen sobre un candidato le quitan votos."""
        nombres = [c[0] for c in CANDIDATOS]
        resultado = {}
        totales = {n: 0 for n in nombres}
        rng = random.Random(self.dia * 97 + len(self.casos))
        for z, info in ZONAS.items():
            gente = residentes(self.red, z)
            apoyo = {}
            for n in nombres:
                base = 25 + rng.uniform(-6, 6) + self.apoyo_zona[z][n]
                for c in self.casos:
                    for v in gente:
                        if c.creencia.get(v) == "falso":
                            nodo = c.arbol.buscar(c.receptores.get(v, -1)) if c.arbol.raiz else None
                            if nodo is not None and n in nodo.afirmacion.sujeto:
                                base -= 6
                base -= self.tension(z) * 0.05
                apoyo[n] = max(1.0, base)
            suma = sum(apoyo.values())
            votos = {n: round(info["poblacion"] * a / suma) for n, a in apoyo.items()}
            resultado[z] = votos
            for n, k in votos.items():
                totales[n] += k
        for j in self.jugadores:
            if j.candidato:
                totales[j.candidato] += j.puntos * 40
        ganador = max(totales, key=totales.get)
        return dict(zonas=resultado, totales=totales, ganador=ganador)

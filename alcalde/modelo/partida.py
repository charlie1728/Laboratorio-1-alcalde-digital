from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from ..estructuras.arbol_mutaciones import ArbolMutaciones, NodoMutacion
from ..estructuras.archivo_avl import ArchivoHechosAVL
from ..estructuras.grafo import Grafo
from .afirmacion import DISTORSIONES
from .apariencia import look_aleatorio, look_por_defecto, normalizar
from .ciudad import Ciudad
from .hechos import CANDIDATOS, Hecho, catalogo
from .mapa import MINUTOS_POR_TURNO, ZONAS, crear_mapa, nombre_zona
from .red_social import (BOTS, MAX_CIUDADANOS, RESERVA, Ciudadano, conectar_jugador,
                         generar_red, residentes)
from .roles import ROLES

ATENCION_POR_TURNO = 3
MAX_NODOS_CASO = 30
MAX_CASOS = 3
MIN_CASOS = 2
PROF_MAX = 7
# Un desmentido oficial convence a quien confía en el candidato por algún camino
# cuyo producto de confianzas supere este umbral (Dijkstra con -log del peso).
UMBRAL_CONFIANZA = 0.12
# La mentira viaja más rápido que la verdad: factor de reenvío según el contenido.
FACTOR_REENVIO = {"falso": 1.5, "veraz": 0.7, "correccion": 0.55}

LOGROS = {
    "Primer chequeo": "Verificaste tu primera publicación.",
    "Paciente cero": "Rastreaste un rumor hasta su origen.",
    "Poda limpia": "Retiraste 5 o más publicaciones de un solo reporte.",
    "Sangre fría": "Frenaste a tiempo una publicación viral falsa.",
    "Voz de la verdad": "Tu publicación verificada le llegó a 8 o más personas.",
    "Cortafuegos": "Contuviste una rama de 5 o más reenvíos.",
    "Vecino ejemplar": "Convenciste a 3 o más vecinos en una sola charla.",
    "Caza-bots": "Lograste que Civitas suspendiera una cuenta bot.",
    "Investigador": "Registraste un hecho nuevo en el Archivo.",
    "Mano limpia": "Terminaste la campaña sin compartir nada falso.",
}


@dataclass
class Jugador:
    nombre: str
    rol: str
    color: tuple
    look: dict = field(default_factory=look_por_defecto)
    puntos: int = 0
    reputacion: int = 50
    atencion: int = ATENCION_POR_TURNO
    minutos: int = MINUTOS_POR_TURNO
    zona: str = "PLAZA"
    logros: list = field(default_factory=list)
    candidato: Optional[str] = None
    stats: dict = field(default_factory=lambda: dict(
        verificados=0, falsos_compartidos=0, reportes=0, corregidos=0, rastreos=0, km=0))

    @property
    def info_rol(self) -> dict:
        return ROLES[self.rol]

    def logro(self, nombre: str) -> bool:
        if nombre not in self.logros:
            self.logros.append(nombre)
            return True
        return False


@dataclass
class Caso:
    id: int
    hecho: Hecho
    arbol: ArbolMutaciones
    abierto: bool = True
    ronda_inicio: int = 1
    # Árbol BFS sobre el grafo social: quién recibió la historia y por cuál publicación
    # (-1 = prevenido antes de que le llegara). Es el conjunto de "visitados" del BFS.
    receptores: dict = field(default_factory=dict)
    # Qué cree cada ciudadano: "falso", "veraz", "duda" o "corregido".
    creencia: dict = field(default_factory=dict)
    descubierto: bool = False
    cierre: str = ""

    def creyentes_falso(self) -> list[str]:
        return [c for c, e in self.creencia.items() if e == "falso"]


@dataclass
class Mensaje:
    texto: str
    tipo: str = "info"


@dataclass
class EventoViral:
    caso: Caso
    nodo: NodoMutacion
    jugador: Jugador
    segundos: int


def _normalizar_config(cfg) -> dict:
    if isinstance(cfg, dict):
        d = dict(cfg)
    else:
        d = dict(nombre=cfg[0], rol=cfg[1], color=tuple(cfg[2]))
        if len(cfg) > 3:
            d["look"] = cfg[3]
    d.setdefault("look", None)
    return d


class Partida:
    def __init__(self, config_jugadores: list, rondas: int = 8, semilla: Optional[int] = None):
        if not 2 <= len(config_jugadores) <= 4:
            raise ValueError("El juego es de 2 a 4 jugadores")
        self.rng = random.Random(semilla)
        self.rondas_totales = rondas
        self.ronda = 1
        self.turno_idx = 0
        self.terminada = False
        self.ciudad = Ciudad()
        self.mensajes: list[Mensaje] = []
        self._off_mensajes = 0
        self.anim: list[dict] = []
        self._seq = 0
        self.evento_viral: Optional[EventoViral] = None
        self.ultimo_resaltado: dict = {}
        self.apoyo = {c[0]: 25.0 for c in CANDIDATOS}
        self.apoyo_zona = {z: {c[0]: 0.0 for c in CANDIDATOS} for z in ZONAS}
        self.tension_extra = {z: 0.0 for z in ZONAS}
        self.aristas_rotas: list[tuple[str, str, float]] = []
        self.eleccion: Optional[dict] = None
        self._ajuste_desinfo = 0.0
        self._sig_caso = 1
        self._visitas = set()

        self.mapa = crear_mapa()
        cfgs = [_normalizar_config(c) for c in config_jugadores]
        usados = set()
        for i, c in enumerate(cfgs):
            base = (str(c["nombre"]).strip() or f"Jugador {i + 1}")[:14]
            nombre, k = base, 2
            while nombre in usados:
                nombre, k = f"{base[:12]} {k}", k + 1
            usados.add(nombre)
            c["nombre"] = nombre
        self.red: Grafo = generar_red(self.rng, self.mapa, usados)

        libres = [c[0] for c in CANDIDATOS]
        self.jugadores: list[Jugador] = []
        for i, c in enumerate(cfgs):
            look = normalizar(c["look"]) if c["look"] else look_aleatorio(self.rng, i % 2 == 1)
            j = Jugador(c["nombre"], c["rol"], tuple(c["color"]), look=look)
            if c["rol"] == "candidato" and libres:
                j.candidato = libres.pop(0)
            cz = conectar_jugador(self.red, self.mapa, self.rng, j.nombre, i, j.rol, look)
            j.zona = cz.zona
            self.jugadores.append(j)

        self.hechos = {h.id: h for h in catalogo()}
        self.archivo = ArchivoHechosAVL()
        for h in self.hechos.values():
            if h.en_archivo:
                self.archivo.insertar(h.id, h)
        self.archivo.bitacora.clear()

        self.casos: list[Caso] = []
        self._nuevo_caso(falso=True)
        self._nuevo_caso(falso=False)
        self._recalcular()
        self.ciudad.historial = [dict(self.ciudad.v)]
        self.log("Día 1: circulan las primeras publicaciones en Civitas.", "evento")

    # ------------------------------------------------------------------ utilidades
    def log(self, texto: str, tipo: str = "info") -> None:
        self.mensajes.append(Mensaje(texto, tipo))

    def total_mensajes(self) -> int:
        return self._off_mensajes + len(self.mensajes)

    def mensajes_desde(self, i: int) -> list[Mensaje]:
        return self.mensajes[max(0, i - self._off_mensajes):]

    def animar(self, **d) -> None:
        d["seq"] = self._seq
        self._seq += 1
        self.anim.append(d)
        if len(self.anim) > 120:
            del self.anim[:len(self.anim) - 120]

    @property
    def jugador_actual(self) -> Jugador:
        return self.jugadores[self.turno_idx]

    def jugador_de(self, nombre: str) -> Optional[Jugador]:
        return next((j for j in self.jugadores if j.nombre == nombre), None)

    def indice_de(self, j: Jugador) -> int:
        return self.jugadores.index(j)

    def casos_abiertos(self) -> list[Caso]:
        return [c for c in self.casos if c.abierto]

    def caso_por_id(self, cid: int) -> Optional[Caso]:
        return next((c for c in self.casos if c.id == cid), None)

    def _caso_de(self, nodo: NodoMutacion) -> Optional[Caso]:
        for c in self.casos_abiertos():
            if nodo.id in c.arbol:
                return c
        return None

    def ciudadano(self, nombre: str) -> Optional[Ciudadano]:
        return self.red.dato(nombre) if nombre in self.red else None

    def npcs(self) -> list[str]:
        return [v for v in self.red.vertices() if self.red.dato(v).es_npc and not self.red.dato(v).bot]

    def es_npc(self, nombre: str) -> bool:
        c = self.ciudadano(nombre)
        return c is not None and c.es_npc and not c.bot

    def estado_ciudadano(self, nombre: str, caso: Optional[Caso] = None) -> str:
        """Lo que cree hoy un ciudadano (en un caso o en toda la campaña)."""
        casos = [caso] if caso else self.casos
        estados = {c.creencia.get(nombre) for c in casos}
        for e in ("falso", "corregido", "veraz", "duda"):
            if e in estados:
                return e
        return "nada"

    def desinformados(self) -> list[str]:
        return [v for v in self.npcs() if any(c.creencia.get(v) == "falso" for c in self.casos)]

    def tension(self, zona: str) -> int:
        gente = residentes(self.red, zona)
        frac = sum(1 for v in gente if any(c.creencia.get(v) == "falso" for c in self.casos)) / max(1, len(gente))
        return max(0, min(100, round(frac * 70 + self.tension_extra.get(zona, 0))))

    def _sujetos_candidatos(self, af) -> list[str]:
        return [c[0] for c in CANDIDATOS if c[0] in af.sujeto]

    # ------------------------------------------------------------------ casos y propagación
    def _nuevo_caso(self, falso: bool, sobre_candidato: bool = False,
                    autor: Optional[str] = None) -> Optional[Caso]:
        usados = {c.hecho.id for c in self.casos_abiertos()}
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
                elegidas = self.rng.sample(ops, 2)
            for d in elegidas:
                af = af.mutar(d, hecho, self.rng)
            dist = "+".join(af.distorsiones)
        if autor is None:
            gente = self.npcs()
            pesos = [(self.red.dato(v).credulidad if falso else 0.5) * (1 + self.red.grado_salida(v))
                     for v in gente]
            autor = self.rng.choices(gente, pesos)[0]
        raiz = NodoMutacion(af, autor, self.ronda, distorsion=dist, alcance=0)
        caso = Caso(self._sig_caso, hecho, ArbolMutaciones(hecho.titulo, raiz), ronda_inicio=self.ronda)
        self._sig_caso += 1
        caso.receptores[autor] = raiz.id
        caso.creencia[autor] = "falso" if falso else "veraz"
        self.casos.append(caso)
        pasos, _ = self._propagar_nodo(caso, raiz, factor=1.3)
        self.animar(t="caso", caso=caso.id, autor=autor, falso=falso, pasos=pasos)
        return caso

    def _reenviar(self, caso: Caso, padre: NodoMutacion, autor: str, prob_mutar: float = 0.3,
                  sin_mutar: bool = False) -> Optional[NodoMutacion]:
        if len(caso.arbol) >= MAX_NODOS_CASO:
            return None
        af, dist = padre.afirmacion, None
        if not sin_mutar and not padre.es_correccion and self.rng.random() < prob_mutar:
            ops = af.posibles_distorsiones(caso.hecho)
            if ops:
                dist = self.rng.choice(ops)
                af = af.mutar(dist, caso.hecho, self.rng)
        hijo = NodoMutacion(af, autor, self.ronda, dist, 0, es_correccion=padre.es_correccion)
        return caso.arbol.insertar(padre.id, hijo)

    @staticmethod
    def _tipo(nodo: NodoMutacion) -> str:
        return "correccion" if nodo.es_correccion else "veraz" if nodo.es_veraz else "falso"

    def _entregar(self, caso: Caso, nodo: NodoMutacion, v: str, peso: float,
                  factor: float) -> tuple[Optional[str], Optional[NodoMutacion]]:
        """La publicación ``nodo`` le llega a ``v``. Devuelve (qué pasó, reenvío creado)."""
        cv = self.red.dato(v)
        tipo = self._tipo(nodo)
        if v in caso.receptores:
            if tipo == "correccion" and caso.creencia.get(v) == "falso":
                caso.creencia[v] = "corregido"
                return "corrige", None
            return None, None
        caso.receptores[v] = nodo.id
        nodo.alcance += 1
        if cv.jugador is not None:
            return "jugador", None
        if tipo == "correccion":
            caso.creencia[v] = "corregido"
        elif tipo == "veraz":
            caso.creencia[v] = "veraz"
        else:
            cree = self.rng.random() < cv.credulidad * (0.7 + 0.5 * peso)
            caso.creencia[v] = "falso" if cree else "duda"
            if not cree:
                return "duda", None
        if nodo.inmune or nodo.profundidad + 1 >= PROF_MAX:
            return "recibe", None
        p = min(0.9, peso * (0.3 + cv.actividad) * FACTOR_REENVIO[tipo] * factor)
        if self.rng.random() < p:
            hijo = self._reenviar(caso, nodo, v, prob_mutar=0.12 + 0.3 * cv.credulidad)
            if hijo is not None:
                return "reenvia", hijo
        return "recibe", None

    def _propagar_nodo(self, caso: Caso, nodo: NodoMutacion,
                       factor: float = 1.0) -> tuple[list, list[NodoMutacion]]:
        """Un paso de BFS: la publicación llega a todos los seguidores de su autor."""
        nodo.entregado = True
        if nodo.autor not in self.red:
            return [], []
        pasos, nuevos = [], []
        seguidores = sorted(self.red.vecinos(nodo.autor).items(), key=lambda x: -x[1]["peso"])
        for v, arista in seguidores:
            que, hijo = self._entregar(caso, nodo, v, arista["peso"], factor)
            if que is None:
                continue
            pasos.append([nodo.autor, v, caso.id, self._tipo(nodo), que])
            if hijo is not None:
                nuevos.append(hijo)
        return pasos, nuevos

    def _ola_de_propagacion(self) -> tuple[int, int]:
        """Una ola = un nivel de BFS: cada publicación de la frontera se entrega."""
        nuevos = alcanzados = 0
        pasos_totales = []
        for c in self.casos_abiertos():
            frontera = [n for nivel in c.arbol.por_niveles() for n in nivel
                        if not n.entregado and not n.inmune]
            for n in frontera:
                pasos, hijos = self._propagar_nodo(c, n, factor=2.0 if n.viral else 1.0)
                n.viral = False
                pasos_totales += pasos
                alcanzados += sum(1 for p in pasos if p[4] != "corrige")
                nuevos += len(hijos)
        self.animar(t="ola", pasos=pasos_totales, nuevos=nuevos)
        return nuevos, alcanzados

    # ------------------------------------------------------------------ indicadores
    def _recalcular(self) -> None:
        nodos = verif = 0
        for c in self.casos_abiertos():
            e = c.arbol.estadisticas()
            nodos += e["nodos"]
            verif += e["verificados"]
        gente = self.npcs()
        pct = 100 * len(self.desinformados()) / max(1, len(gente))
        self.ciudad.fijar("desinformacion", pct * 0.85 + self._ajuste_desinfo)
        base_info = (verif / nodos * 60) if nodos else 30
        self.ciudad.fijar("info_verificada", 20 + base_info + max(0, -self._ajuste_desinfo) / 2)

    def _confianza_aristas(self, origen: str, delta: float, solo_npc: bool = True) -> int:
        if origen not in self.red:
            return 0
        n = 0
        for v in list(self.red.vecinos(origen)):
            if solo_npc and not self.es_npc(v):
                continue
            self.red.ajustar_peso(origen, v, delta)
            n += 1
        return n

    # ------------------------------------------------------------------ acciones
    def acciones_para(self, nodo: Optional[NodoMutacion]) -> list[dict]:
        j = self.jugador_actual
        esp_clave, esp_nombre, esp_costo = j.info_rol["especial"]
        acciones = [
            dict(clave="verificar", nombre="Verificar", costo=1),
            dict(clave="compartir", nombre="Compartir", costo=1),
            dict(clave="reportar", nombre="Reportar", costo=1),
            dict(clave="ignorar", nombre="Ignorar", costo=1),
            dict(clave=esp_clave, nombre=esp_nombre, costo=esp_costo, especial=True),
        ]
        if nodo is not None and nodo.autor == j.nombre and not nodo.es_correccion:
            acciones.append(dict(clave="borrar", nombre="Borrar mi publicación", costo=1))
        caso = self._caso_de(nodo) if nodo is not None else None
        for a in acciones:
            a["ok"], a["motivo"] = True, ""
            if nodo is None or caso is None:
                a["ok"], a["motivo"] = False, "Elige una publicación"
            elif self.terminada:
                a["ok"], a["motivo"] = False, "La campaña terminó"
            elif j.atencion < a["costo"]:
                a["ok"], a["motivo"] = False, "Te falta atención"
            elif nodo.es_correccion and a["clave"] not in ("compartir", "ignorar"):
                a["ok"], a["motivo"] = False, "Es un desmentido"
            elif a["clave"] in ("alertar", "amplificar", "desmentir"):
                if not nodo.verificado or nodo.es_veraz:
                    a["ok"], a["motivo"] = False, "Primero verifica que es falsa"
                elif nodo.inmune:
                    a["ok"], a["motivo"] = False, "Esa rama ya está contenida"
            elif a["clave"] == "rastrear" and nodo.es_veraz and nodo.verificado:
                a["ok"], a["motivo"] = False, "Es fiel al hecho"
            elif a["clave"] == "compartir" and nodo.inmune and not nodo.es_correccion:
                a["ok"], a["motivo"] = False, "Rama contenida"
            elif a["clave"] == "compartir" and len(caso.arbol) >= MAX_NODOS_CASO:
                a["ok"], a["motivo"] = False, "Hilo saturado"
        return acciones

    def ejecutar(self, clave: str, caso: Caso, nodo: NodoMutacion,
                 gratis: bool = False) -> list[Mensaje]:
        j = self.jugador_actual
        acc = next((a for a in self.acciones_para(nodo) if a["clave"] == clave), None)
        if acc is None:
            return [Mensaje("Esa acción no está disponible", "malo")]
        if not gratis and not acc["ok"]:
            return [Mensaje(acc["motivo"], "malo")]
        antes = len(self.mensajes)
        self.ultimo_resaltado = {}
        getattr(self, "_a_" + clave)(j, caso, nodo)
        if not gratis:
            j.atencion -= acc["costo"]
        j.reputacion = max(0, min(100, j.reputacion))
        if caso.arbol.raiz is None and caso.abierto:
            caso.abierto = False
            caso.cierre = "retirado"
            self.log(f"La historia '{caso.hecho.titulo}' fue retirada de Civitas.", "evento")
        self._recalcular()
        return self.mensajes[antes:]

    def _descubrir(self, caso: Caso, nodo: NodoMutacion) -> None:
        if not nodo.es_veraz:
            caso.descubierto = True

    def _a_compartir(self, j: Jugador, caso: Caso, nodo: NodoMutacion) -> None:
        nuevo = self._reenviar(caso, nodo, autor=j.nombre, sin_mutar=True)
        if nuevo is None:
            self.log("Este hilo ya está saturado: nadie más lo ve.", "info")
            return
        nuevo.inmune = nodo.inmune
        caso.receptores.setdefault(j.nombre, nodo.id)
        pasos, hijos = self._propagar_nodo(caso, nuevo)
        alcance = nuevo.alcance
        self.animar(t="difusion", de=j.nombre, caso=caso.id, pasos=pasos)
        self.ultimo_resaltado = {"nuevos": [nuevo.id] + [h.id for h in hijos], "difusion": j.nombre}
        if nodo.es_veraz:
            if nodo.verificado or nodo.es_correccion:
                pts = min(30, 4 + 2 * alcance)
                j.puntos += pts
                j.reputacion += 4
                self.ciudad.ajustar(confianza=1 + alcance // 4, bienestar=1)
                self._confianza_aristas(j.nombre, 0.04)
                self._ajuste_desinfo -= 1 + alcance / 6
                que = "un desmentido" if nodo.es_correccion else "información verificada"
                self.log(f"{j.nombre} difundió {que}: le llegó a {alcance} personas. +{pts} pts", "bueno")
                if alcance >= 8 and j.logro("Voz de la verdad"):
                    self.log(f"Logro de {j.nombre}: Voz de la verdad", "logro")
            else:
                j.puntos += 2
                self.log(f"{j.nombre} compartió sin verificar y por suerte era cierta "
                         f"(le llegó a {alcance} personas). +2 pts", "info")
        else:
            nodo.verificado = nuevo.verificado = True
            self._descubrir(caso, nodo)
            pts = 3 + alcance
            j.puntos -= pts
            j.reputacion -= 4 + alcance // 2
            j.stats["falsos_compartidos"] += 1
            self.ciudad.ajustar(conflictos=1 + alcance // 4, confianza=-(1 + alcance // 4))
            self._confianza_aristas(j.nombre, -0.06)
            self._ajuste_desinfo += 1 + alcance / 4
            nombres = ", ".join(DISTORSIONES[d] for d in nodo.afirmacion.distorsiones)
            self.log(f"{j.nombre} difundió una versión FALSA ({nombres}) a {alcance} personas. "
                     f"-{pts} pts", "malo")

    def _a_verificar(self, j: Jugador, caso: Caso, nodo: NodoMutacion) -> None:
        hecho, comps, ruta = self.archivo.buscar(caso.hecho.id)
        self.ultimo_resaltado = {"avl_ruta": ruta, "verificado": [nodo.id]}
        if hecho is None:
            en_terreno = j.zona == caso.hecho.lugar
            if j.rol == "periodista" or en_terreno:
                n_rot = len(self.archivo.bitacora)
                self.archivo.insertar(caso.hecho.id, caso.hecho)
                nuevas = self.archivo.bitacora[n_rot:]
                rot = "; ".join(nuevas) if nuevas else "sin rotaciones"
                como = "fue al lugar de los hechos" if en_terreno and j.rol != "periodista" else "investigó"
                self.log(f"{j.nombre} {como} y registró '{caso.hecho.titulo}' en el Archivo ({rot}).", "evento")
                hecho, comps, ruta = self.archivo.buscar(caso.hecho.id)
                self.ultimo_resaltado["avl_ruta"] = ruta
                self.ultimo_resaltado["avl_nuevo"] = caso.hecho.id
                j.puntos += 4
                if j.logro("Investigador"):
                    self.log(f"Logro de {j.nombre}: Investigador", "logro")
            else:
                self.log(f"Verificación inconclusa: '{caso.hecho.titulo}' no está en el Archivo "
                         f"({comps} comparaciones). Ve a {nombre_zona(caso.hecho.lugar)} a comprobarlo "
                         "en persona o pide ayuda a un periodista.", "info")
                self.ultimo_resaltado["verificacion"] = dict(nodo=nodo.id, inconclusa=True,
                                                            zona=caso.hecho.lugar, comps=comps)
                return
        dif = nodo.afirmacion.comparar_con(hecho)
        ya = nodo.verificado
        nodo.verificado = True
        self._descubrir(caso, nodo)
        if not ya:
            j.puntos += 5
            j.reputacion += 2
            j.stats["verificados"] += 1
            self.ciudad.ajustar(confianza=1)
        self.ultimo_resaltado["verificacion"] = dict(nodo=nodo.id, diferencias=dif, comps=comps)
        if dif:
            self.log(f"Verificado ({comps} comparaciones en el Archivo): es FALSA. "
                     + ", ".join(DISTORSIONES[d] for d in dif) + ".", "bueno")
        else:
            self.log(f"Verificado ({comps} comparaciones en el Archivo): coincide con el hecho oficial.", "bueno")
        if j.logro("Primer chequeo"):
            self.log(f"Logro de {j.nombre}: Primer chequeo", "logro")

    def _a_reportar(self, j: Jugador, caso: Caso, nodo: NodoMutacion) -> None:
        if nodo.es_veraz:
            j.reputacion -= 8
            j.puntos -= 4
            self.ciudad.ajustar(confianza=-3, convivencia=-2)
            self._confianza_aristas(j.nombre, -0.03)
            nodo.verificado = True
            self.log("Civitas revisó el reporte: el contenido era VERDADERO. Reporte rechazado "
                     "(-4 pts). Reportar lo cierto también hace daño.", "malo")
            return
        self._descubrir(caso, nodo)
        eliminados = caso.arbol.podar(nodo.id)
        ids = {n.id for n in eliminados}
        avisados = 0
        for c, nid in caso.receptores.items():
            if nid in ids and caso.creencia.get(c) == "falso":
                caso.creencia[c] = "corregido"
                avisados += 1
        for n in eliminados:
            if caso.creencia.get(n.autor) == "falso":
                caso.creencia[n.autor] = "corregido"
                avisados += 1
        falsos = sum(1 for n in eliminados if not n.es_veraz)
        pts = 6 + 2 * falsos
        j.puntos += pts
        j.reputacion += 3
        j.stats["reportes"] += 1
        j.stats["corregidos"] += avisados
        self.ciudad.ajustar(convivencia=2, conflictos=-1)
        self._ajuste_desinfo -= avisados / 3
        self.ultimo_resaltado = {"podados": [n.id for n in eliminados]}
        self.log(f"Reporte aceptado: se retiraron {len(eliminados)} publicaciones y {avisados} "
                 f"personas recibieron el aviso de Civitas. +{pts} pts", "bueno")
        if len(eliminados) >= 5 and j.logro("Poda limpia"):
            self.log(f"Logro de {j.nombre}: Poda limpia", "logro")
        for bot in {n.autor for n in eliminados if self.ciudadano(n.autor) and self.ciudadano(n.autor).bot}:
            seguidores = self.red.grado_salida(bot)
            self.red.eliminar_vertice(bot)
            self.animar(t="vertice_fuera", v=bot)
            j.puntos += 8
            self.log(f"Civitas suspendió la cuenta bot {bot}: ya no le llega nada a sus "
                     f"{seguidores} seguidores. +8 pts", "bueno")
            if j.logro("Caza-bots"):
                self.log(f"Logro de {j.nombre}: Caza-bots", "logro")

    def _a_ignorar(self, j: Jugador, caso: Caso, nodo: NodoMutacion) -> None:
        if not nodo.es_veraz:
            j.puntos += 2
            self.ciudad.ajustar(bienestar=1)
            self.log(f"{j.nombre} no alimentó el rumor. +2 pts", "info")
        else:
            self.log(f"{j.nombre} dejó pasar la publicación.", "info")

    def _a_borrar(self, j: Jugador, caso: Caso, nodo: NodoMutacion) -> None:
        hijos = len(nodo.hijos)
        caso.arbol.eliminar_nodo(nodo.id)
        self.ultimo_resaltado = {"podados": [nodo.id]}
        if hijos:
            self.log(f"{j.nombre} borró su publicación, pero sus {hijos} reenvíos siguen circulando: "
                     "borrar no deshace lo compartido.", "malo" if not nodo.es_veraz else "info")
        else:
            self.log(f"{j.nombre} borró su publicación antes de que alguien la reenviara.", "bueno")
            if not nodo.es_veraz:
                j.puntos += 3
                j.reputacion += 2

    def _corregir(self, caso: Caso, gente, prevenir: bool = False) -> tuple[list[str], list[str]]:
        corregidos, prevenidos = [], []
        for c in gente:
            if not self.es_npc(c):
                continue
            if caso.creencia.get(c) == "falso":
                caso.creencia[c] = "corregido"
                corregidos.append(c)
            elif prevenir and c not in caso.receptores:
                caso.receptores[c] = -1
                caso.creencia[c] = "corregido"
                prevenidos.append(c)
        return corregidos, prevenidos

    def _a_alertar(self, j: Jugador, caso: Caso, nodo: NodoMutacion) -> None:
        contactos = sorted(self.red.contactos(j.nombre), key=str)
        corregidos, prevenidos = self._corregir(caso, contactos, prevenir=True)
        marcados = {nodo.id: nodo}
        for h in nodo.hijos:
            marcados[h.id] = h
        for n in caso.arbol.preorden():
            if n.autor in contactos:
                marcados[n.id] = n
        for n in marcados.values():
            n.inmune = True
        j.puntos += 3 + 2 * len(marcados) + len(corregidos)
        j.stats["corregidos"] += len(corregidos)
        self._confianza_aristas(j.nombre, 0.03)
        self.ciudad.ajustar(convivencia=2, bienestar=1)
        self._ajuste_desinfo -= len(corregidos) / 2
        self.ultimo_resaltado = {"inmunes": list(marcados), "contactos": contactos}
        self.animar(t="alerta", de=j.nombre, a=contactos, caso=caso.id)
        self.log(f"{j.nombre} alertó a sus {len(contactos)} contactos: {len(corregidos)} dejaron de "
                 f"creerlo, {len(prevenidos)} quedaron prevenidos y {len(marcados)} reenvíos dejan "
                 "de circular.", "bueno")
        if len(marcados) >= 5 and j.logro("Cortafuegos"):
            self.log(f"Logro de {j.nombre}: Cortafuegos", "logro")

    def _a_rastrear(self, j: Jugador, caso: Caso, nodo: NodoMutacion) -> None:
        camino = caso.arbol.camino_a_raiz(nodo.id)
        puntos = caso.arbol.punto_de_mutacion(nodo.id)
        for n in camino:
            n.verificado = True
        self._descubrir(caso, nodo)
        self.ultimo_resaltado = {"camino": [n.id for n in camino],
                                 "mutacion": [n.id for n in puntos.values()],
                                 "ruta_social": [n.autor for n in reversed(camino)]}
        j.puntos += 4 + 2 * len(camino)
        j.reputacion += 4
        j.stats["rastreos"] += 1
        self.ciudad.ajustar(confianza=3)
        self._ajuste_desinfo -= 2
        self.animar(t="rastreo", ruta=[n.autor for n in reversed(camino)], caso=caso.id)
        if not puntos:
            self.log(f"Rastreo: {len(camino)} saltos hasta el origen y ninguna distorsión. "
                     "Es fiel al hecho.", "bueno")
            return
        partes = []
        for d, n in puntos.items():
            nombre = " + ".join(DISTORSIONES.get(x, x) for x in d.split("+"))
            quien = "desde el ORIGEN" if n.es_raiz else f"en el reenvío de {n.autor} (ola {n.profundidad})"
            partes.append(f"{nombre} {quien}")
        self.log("Rastreo (" + str(len(camino)) + " saltos): " + "; ".join(partes), "bueno")
        origen = min(puntos.values(), key=lambda n: n.profundidad)
        if self.es_npc(origen.autor):
            k = self._confianza_aristas(origen.autor, -0.2)
            self.log(f"{origen.autor} quedó expuesto: sus {k} seguidores le creerán menos.", "evento")
        if j.logro("Paciente cero"):
            self.log(f"Logro de {j.nombre}: Paciente cero", "logro")

    def _insertar_correccion(self, caso: Caso, j: Jugador, destino: NodoMutacion) -> NodoMutacion:
        corr = NodoMutacion(caso.hecho.afirmacion_real(), j.nombre, self.ronda, alcance=0,
                            es_correccion=True)
        corr.verificado = True
        caso.arbol.insertar(destino.id, corr)
        return corr

    def _a_amplificar(self, j: Jugador, caso: Caso, nodo: NodoMutacion) -> None:
        puntos = caso.arbol.punto_de_mutacion(nodo.id)
        objetivo = min(puntos.values(), key=lambda n: n.profundidad) if puntos else nodo
        marcados = caso.arbol.inmunizar(objetivo.id)
        corr = self._insertar_correccion(caso, j, objetivo.padre or objetivo)
        niveles = self.red.bfs_niveles(j.nombre, max_nivel=2)
        alcanzados = [v for nivel in niveles[1:] for v in nivel]
        corregidos, _ = self._corregir(caso, alcanzados)
        pasos, _ = self._propagar_nodo(caso, corr)
        corr.inmune = True
        j.puntos += 6 + 2 * len(marcados) + len(corregidos)
        j.reputacion += 6
        j.stats["corregidos"] += len(corregidos)
        self.ciudad.ajustar(confianza=4, convivencia=2)
        self._ajuste_desinfo -= len(marcados) + len(corregidos) / 2
        self.ultimo_resaltado = {"inmunes": [n.id for n in marcados], "nuevos": [corr.id],
                                 "bfs": niveles}
        self.animar(t="bfs", origen=j.nombre, niveles=niveles, caso=caso.id)
        self.log(f"{j.nombre} amplificó un desmentido: {len(marcados)} reenvíos contenidos desde donde "
                 f"se torció la historia y {len(corregidos)} personas corregidas a 2 saltos.", "bueno")
        if len(marcados) >= 5 and j.logro("Cortafuegos"):
            self.log(f"Logro de {j.nombre}: Cortafuegos", "logro")

    def _a_desmentir(self, j: Jugador, caso: Caso, nodo: NodoMutacion) -> None:
        marcados = caso.arbol.inmunizar(nodo.id)
        corr = self._insertar_correccion(caso, j, nodo)
        corr.inmune = True
        confianza, prev = self.red.confianza_maxima(j.nombre)
        convencidos = [c for c in caso.creyentes_falso() if confianza.get(c, 0) >= UMBRAL_CONFIANZA]
        corregidos, _ = self._corregir(caso, convencidos)
        rutas = {c: Grafo.reconstruir(prev, c) for c in corregidos}
        sobre_mi = bool(j.candidato) and j.candidato in nodo.afirmacion.sujeto
        bonus = 2 if sobre_mi else 1
        j.puntos += (5 + len(marcados) + len(corregidos)) * bonus
        j.reputacion += 3 * bonus
        j.stats["corregidos"] += len(corregidos)
        if j.candidato:
            self.apoyo[j.candidato] += 1.5 * bonus
        self.ciudad.ajustar(confianza=2 * bonus)
        self._ajuste_desinfo -= len(marcados) + len(corregidos) / 2
        self.ultimo_resaltado = {"inmunes": [n.id for n in marcados], "nuevos": [corr.id],
                                 "rutas_confianza": rutas}
        self.animar(t="confianza", origen=j.nombre, rutas=rutas, caso=caso.id)
        extra = " Era un rumor sobre su campaña: apoyo x2." if sobre_mi else ""
        self.log(f"Desmentido oficial de {j.nombre}: {len(marcados)} reenvíos contenidos y "
                 f"{len(corregidos)} personas convencidas por caminos de confianza.{extra}", "bueno")

    # ------------------------------------------------------------------ acciones en el mapa
    def destinos(self) -> dict[str, float]:
        """Zonas a las que el jugador actual llega con los minutos que le quedan (Dijkstra acotado)."""
        j = self.jugador_actual
        return self.mapa.alcanzables(j.zona, j.minutos)

    def mover(self, zona: str) -> list[Mensaje]:
        j = self.jugador_actual
        if zona not in self.mapa or zona == j.zona or self.terminada:
            return []
        dist, prev = self.mapa.dijkstra(j.zona)
        if dist.get(zona, 1e9) > j.minutos:
            return [Mensaje(f"{nombre_zona(zona)} queda a {int(dist.get(zona, 0))} min y solo te quedan "
                            f"{j.minutos} min este turno.", "malo")]
        antes = len(self.mensajes)
        ruta = Grafo.reconstruir(prev, zona)
        j.minutos -= int(dist[zona])
        j.stats["km"] += int(dist[zona])
        j.zona = zona
        self.red.dato(j.nombre).zona = zona
        self.ultimo_resaltado = {"ruta": ruta}
        self.animar(t="mover", jugador=self.indice_de(j), ruta=ruta)
        self.log(f"{j.nombre} fue a {nombre_zona(zona)} ({int(dist[zona])} min).", "info")
        clave = (self.ronda, j.nombre, zona)
        if j.candidato and clave not in self._visitas:
            self._visitas.add(clave)
            self.apoyo_zona[zona][j.candidato] += 2
            self.log(f"{j.candidato} saludó a los vecinos de {nombre_zona(zona)}: más apoyo en la zona.", "bueno")
        return self.mensajes[antes:]

    def objetivo_charla(self, zona: Optional[str] = None) -> list[str]:
        """Vecinos de la zona que creen una historia que ya se descubrió falsa."""
        zona = zona or self.jugador_actual.zona
        descubiertos = [c for c in self.casos if c.descubierto]
        return [v for v in residentes(self.red, zona)
                if any(c.creencia.get(v) == "falso" for c in descubiertos)]

    def puede_conversar(self) -> tuple[bool, str]:
        j = self.jugador_actual
        if self.terminada:
            return False, "La campaña terminó"
        if j.atencion < 1:
            return False, "Te falta atención"
        if not self.objetivo_charla():
            return False, "Aquí nadie cree un rumor ya descubierto"
        return True, ""

    def conversar(self) -> list[Mensaje]:
        ok, motivo = self.puede_conversar()
        if not ok:
            return [Mensaje(motivo, "malo")]
        j = self.jugador_actual
        antes = len(self.mensajes)
        gente = self.objetivo_charla()
        for c in self.casos:
            if c.descubierto:
                self._corregir(c, gente)
        j.atencion -= 1
        pts = 2 + 3 * len(gente)
        j.puntos += pts
        j.reputacion += 2
        j.stats["corregidos"] += len(gente)
        self.ciudad.ajustar(convivencia=len(gente), bienestar=1)
        self.tension_extra[j.zona] = max(0, self.tension_extra[j.zona] - 10)
        self.ultimo_resaltado = {"charla": gente, "zona": j.zona}
        self.animar(t="charla", zona=j.zona, a=gente, jugador=self.indice_de(j))
        self.log(f"{j.nombre} conversó con los vecinos de {nombre_zona(j.zona)}: "
                 f"{len(gente)} dejaron de creer el rumor. +{pts} pts", "bueno")
        if len(gente) >= 3 and j.logro("Vecino ejemplar"):
            self.log(f"Logro de {j.nombre}: Vecino ejemplar", "logro")
        self._recalcular()
        return self.mensajes[antes:]

    # ------------------------------------------------------------------ turnos y rondas
    def terminar_turno(self) -> None:
        if self.terminada:
            return
        self.turno_idx += 1
        if self.turno_idx >= len(self.jugadores):
            self.turno_idx = 0
            self._fin_de_ronda()
        self.jugador_actual.atencion = ATENCION_POR_TURNO
        self.jugador_actual.minutos = MINUTOS_POR_TURNO
        if not self.terminada:
            self.log(f"Turno de {self.jugador_actual.nombre} "
                     f"({self.jugador_actual.info_rol['nombre']}).", "info")

    def _cerrar_casos(self) -> None:
        for c in self.casos_abiertos():
            if c.arbol.raiz is None:
                c.abierto, c.cierre = False, "retirado"
                self.log(f"La historia '{c.hecho.titulo}' fue retirada de Civitas.", "evento")
                continue
            contenido = all(n.inmune or n.es_correccion for n in c.arbol.preorden())
            vieja = self.ronda - c.ronda_inicio >= 2
            if not c.arbol.frontera() and (contenido or vieja):
                c.abierto, c.cierre = False, "contenido" if contenido else "agotado"
                quedan = len([v for v in c.creyentes_falso() if self.es_npc(v)])
                if contenido:
                    self.log(f"La historia '{c.hecho.titulo}' quedó contenida: ya no se propaga.", "evento")
                elif quedan:
                    self.log(f"La historia '{c.hecho.titulo}' dejó de circular, pero {quedan} personas "
                             "siguen creyendo la versión falsa. Puedes conversar con ellas en su barrio.", "evento")
                else:
                    self.log(f"La historia '{c.hecho.titulo}' dejó de circular.", "evento")
        abiertos = self.casos_abiertos()
        if len(abiertos) > MAX_CASOS:
            for c in sorted(abiertos, key=lambda c: c.ronda_inicio)[:len(abiertos) - MAX_CASOS]:
                if not c.arbol.frontera():
                    c.abierto, c.cierre = False, "agotado"

    def _fin_de_ronda(self) -> None:
        nuevos, alcanzados = self._ola_de_propagacion()
        self.log(f"Noche en Civitas: la ola de propagación le llegó a {alcanzados} personas y dejó "
                 f"{nuevos} reenvíos nuevos.", "evento")
        for nombre in self.apoyo:
            creen = sum(1 for c in self.casos for v in c.creyentes_falso()
                        if self.es_npc(v) and nombre in self._version_de(c, v))
            self.apoyo[nombre] = max(5.0, self.apoyo[nombre] - 0.25 * creen)
        d = self.ciudad.v["desinformacion"]
        tension_media = sum(self.tension(z) for z in ZONAS) / len(ZONAS)
        self.ciudad.ajustar(conflictos=(d - 30) / 12 + (tension_media - 25) / 25,
                            convivencia=-(d - 30) / 15, bienestar=-(d - 35) / 20)
        for z in self.tension_extra:
            self.tension_extra[z] *= 0.7
        for c in self.casos:
            if not c.abierto:
                for v in c.creyentes_falso():
                    if self.rng.random() < 0.1:
                        c.creencia[v] = "duda"
        self._ajuste_desinfo *= 0.85
        self._evento_aleatorio()
        self._cerrar_casos()
        intentos = 0
        while len(self.casos_abiertos()) < MIN_CASOS and intentos < 3:
            intentos += 1
            self._nuevo_caso(falso=self.rng.random() < 0.65)
        self._recalcular()
        self.ciudad.guardar()
        self.ronda += 1
        if self.ronda > self.rondas_totales:
            self._terminar()
        else:
            faltan = self.rondas_totales - self.ronda
            self.log(f"Día {self.ronda}: " + ("mañana es la elección." if faltan == 0 else
                                               "falta 1 día para la elección." if faltan == 1 else
                                               f"faltan {faltan} días para la elección."), "evento")

    def _version_de(self, caso: Caso, v: str) -> str:
        nid = caso.receptores.get(v)
        nodo = caso.arbol.buscar(nid) if isinstance(nid, int) and nid >= 0 else None
        return nodo.afirmacion.sujeto if nodo else ""

    def _terminar(self) -> None:
        from .eleccion import calcular_eleccion
        self.terminada = True
        self.evento_viral = None
        for j in self.jugadores:
            if j.stats["falsos_compartidos"] == 0 and j.logro("Mano limpia"):
                self.log(f"Logro de {j.nombre}: Mano limpia", "logro")
        self.eleccion = calcular_eleccion(self)
        for j in self.jugadores:
            if j.candidato and j.candidato == self.eleccion["ganador"]:
                j.puntos += 25
                j.logro("Alcaldía de Ciudad Nova")
        self.log("Fin de la campaña: Ciudad Nova va a las urnas.", "evento")

    def _evento_aleatorio(self) -> None:
        eventos = [("falsa", 3), ("rumor", 3), ("verdadera", 2), ("viral", 4), ("discusion", 2),
                   ("campana", 2), ("reporte_npc", 2), ("vence", 1), ("bot", 2), ("vecino", 1)]
        if len(self.casos_abiertos()) >= MAX_CASOS:
            eventos = [e for e in eventos if e[0] not in ("falsa", "rumor", "verdadera", "bot")]
        if len(self.red) >= MAX_CIUDADANOS + len(self.jugadores):
            eventos = [e for e in eventos if e[0] != "vecino"]
        tipo = self.rng.choices([e[0] for e in eventos], [e[1] for e in eventos])[0]
        getattr(self, "_ev_" + tipo)()

    def _ev_falsa(self) -> None:
        c = self._nuevo_caso(falso=True)
        if c:
            self.animar(t="evento", tipo="falsa", zona=c.hecho.lugar)
            self.log(f"Evento: aparece una noticia falsa sobre '{c.hecho.titulo}'.", "evento")

    def _ev_rumor(self) -> None:
        c = self._nuevo_caso(falso=True, sobre_candidato=True)
        if c:
            self.animar(t="evento", tipo="rumor", zona=c.hecho.lugar)
            self.log(f"Evento: rumor sobre un candidato ('{c.hecho.titulo}').", "evento")

    def _ev_verdadera(self) -> None:
        c = self._nuevo_caso(falso=False)
        if c:
            self.animar(t="evento", tipo="verdadera", zona=c.hecho.lugar)
            self.log(f"Evento: se publica una noticia verdadera ('{c.hecho.titulo}').", "evento")

    def _ev_viral(self) -> None:
        cands = [(c, n) for c in self.casos_abiertos() for n in c.arbol.frontera()
                 if n.autor in self.red]
        if not cands:
            return self._ev_discusion()
        # Superpropagador: el autor con más seguidores (centralidad de grado) tiene más opciones.
        pesos = [1 + self.red.grado_salida(n.autor) ** 2 for _, n in cands]
        c, n = self.rng.choices(cands, pesos)[0]
        n.viral = True
        j = self.jugadores[self.ronda % len(self.jugadores)]
        self.evento_viral = EventoViral(c, n, j, j.info_rol["tiempo_viral"])
        self.animar(t="evento", tipo="viral", zona=c.hecho.lugar, nodo=n.id)
        self.log(f"Evento: ¡una publicación de {n.autor} ({self.red.grado_salida(n.autor)} seguidores) "
                 "se está volviendo viral!", "evento")

    def _ev_discusion(self) -> None:
        zonas = list(ZONAS)
        zona = self.rng.choices(zonas, [1 + self.tension(z) for z in zonas])[0]
        gente = residentes(self.red, zona)
        pares = [(a, b) for a in gente for b in gente if a < b and self.red.tiene_arista(a, b)]
        if not pares:
            pares = [(a, b) for a in gente for b in self.red.vecinos(a) if self.es_npc(b) and a < b]
        texto = ""
        if pares:
            a, b = self.rng.choice(pares)
            comps_antes = len(self.red.componentes_conexas())
            for u, v in ((a, b), (b, a)):
                if self.red.tiene_arista(u, v):
                    self.aristas_rotas.append((u, v, self.red.peso(u, v)))
                    self.red.eliminar_arista(u, v)
            self.animar(t="arista_rota", u=a, v=b)
            texto = f" {a} y {b} dejaron de seguirse."
            if len(self.red.componentes_conexas()) > comps_antes:
                texto += " Se formó una burbuja: un grupo quedó aislado del resto de la red."
        _, nivel, _ = self.mapa.bfs(zona, max_nivel=2)
        for z, d in nivel.items():
            self.tension_extra[z] += (24, 12, 6)[d]
        self.ciudad.ajustar(conflictos=6, convivencia=-4)
        self.animar(t="evento", tipo="discusion", zona=zona)
        self.log(f"Evento: discusión en {nombre_zona(zona)}.{texto} La tensión se contagia "
                 "a las zonas vecinas. Conflictos +6", "evento")

    def _ev_campana(self) -> None:
        zona = self.rng.choice(list(ZONAS))
        _, nivel, _ = self.mapa.bfs(zona, max_nivel=2)
        for z, d in nivel.items():
            self.tension_extra[z] = max(0.0, self.tension_extra[z] - (20, 10, 5)[d])
        reparadas = 0
        for u, v, p in list(self.aristas_rotas):
            if u in self.red and v in self.red and (self.red.dato(u).zona in nivel or self.red.dato(v).zona in nivel):
                self.red.agregar_arista(u, v, p, tipo="amistad")
                self.aristas_rotas.remove((u, v, p))
                reparadas += 1
        gente = residentes(self.red, zona)
        for a in gente:
            for b in gente:
                if a != b and self.red.tiene_arista(a, b):
                    self.red.ajustar_peso(a, b, 0.05)
        self.ciudad.ajustar(convivencia=6, bienestar=4)
        self.animar(t="evento", tipo="campana", zona=zona)
        extra = f" Se reconciliaron {reparadas // 2 or reparadas} amistades." if reparadas else ""
        self.log(f"Evento: campaña de convivencia digital en {nombre_zona(zona)}. Convivencia +6.{extra}", "evento")

    def _ev_reporte_npc(self) -> None:
        falsos = [(c, n) for c in self.casos_abiertos() for n in c.arbol.hojas()
                  if not n.es_veraz and not n.es_raiz]
        if not falsos:
            return self._ev_campana()
        c, n = self.rng.choice(falsos)
        quien = self.rng.choice(self.npcs())
        c.arbol.podar(n.id)
        if c.creencia.get(n.autor) == "falso":
            c.creencia[n.autor] = "corregido"
        self.animar(t="evento", tipo="reporte", zona=self.red.dato(quien).zona)
        self.log(f"Evento: {quien} reportó un reenvío falso de {n.autor} y Civitas lo retiró.", "evento")

    def _ev_vence(self) -> None:
        en_uso = {c.hecho.id for c in self.casos_abiertos()}
        libres = [k for k, _ in self.archivo.inorden() if k not in en_uso]
        if libres:
            k = self.rng.choice(libres)
            self.archivo.eliminar(k)
            self.animar(t="evento", tipo="vence", zona=self.hechos[k].lugar)
            self.log(f"Evento: el hecho '{self.hechos[k].titulo}' venció y salió del Archivo.", "evento")

    def _ev_bot(self) -> None:
        libres = [b for b in BOTS if b not in self.red]
        if not libres:
            return self._ev_falsa()
        bot = self.rng.choice(libres)
        zona = self.rng.choice(list(ZONAS))
        self.red.agregar_vertice(bot, Ciudadano(bot, zona, credulidad=1.0, actividad=1.0,
                                                look=look_aleatorio(self.rng, False), bot=True))
        for v in self.rng.sample(self.npcs(), 8):
            self.red.agregar_arista(bot, v, round(self.rng.uniform(0.45, 0.7), 2), tipo="seguimiento")
        self.animar(t="vertice_nuevo", v=bot)
        c = self._nuevo_caso(falso=True, sobre_candidato=True, autor=bot)
        self.animar(t="evento", tipo="bot", zona=zona)
        if c:
            self.log(f"Evento: la cuenta {bot} apareció de la nada con 8 seguidores y publica un rumor "
                     f"sobre '{c.hecho.titulo}'. Si la reportas, Civitas puede suspenderla.", "evento")
        else:
            self.log(f"Evento: apareció la cuenta {bot} con 8 seguidores.", "evento")

    def _ev_vecino(self) -> None:
        libres = [r for r in RESERVA if r[0] not in self.red]
        if not libres:
            return self._ev_campana()
        nombre, fem = self.rng.choice(libres)
        zona = self.rng.choice(list(ZONAS))
        self.red.agregar_vertice(nombre, Ciudadano(
            nombre, zona, credulidad=round(self.rng.uniform(0.25, 0.8), 2),
            actividad=round(self.rng.uniform(0.35, 0.9), 2), look=look_aleatorio(self.rng, fem)))
        cerca = residentes(self.red, zona) or self.npcs()
        for v in self.rng.sample([c for c in cerca if c != nombre], min(3, len(cerca) - 1)):
            p = round(self.rng.uniform(0.5, 0.8), 2)
            self.red.agregar_arista(nombre, v, p, tipo="amistad")
            self.red.agregar_arista(v, nombre, p, tipo="amistad")
        self.animar(t="vertice_nuevo", v=nombre)
        self.animar(t="evento", tipo="vecino", zona=zona)
        self.log(f"Evento: {nombre} se mudó a {nombre_zona(zona)} y se unió a Civitas.", "evento")

    def resolver_viral(self, clave: Optional[str]) -> list[Mensaje]:
        ev, self.evento_viral = self.evento_viral, None
        if ev is None or not ev.caso.abierto or ev.nodo.id not in ev.caso.arbol:
            return []
        actual = self.turno_idx
        self.turno_idx = self.jugadores.index(ev.jugador)
        try:
            if clave is None:
                antes = len(self.mensajes)
                ev.nodo.entregado = False
                pasos, hijos = self._propagar_nodo(ev.caso, ev.nodo, factor=2.5)
                ev.nodo.viral = False
                self.animar(t="difusion", de=ev.nodo.autor, caso=ev.caso.id, pasos=pasos)
                if not ev.nodo.es_veraz:
                    self._ajuste_desinfo += 4
                self.log(f"Nadie reaccionó a tiempo: la publicación viral le llegó a {len(pasos)} "
                         f"personas y generó {len(hijos)} reenvíos.", "malo")
                self._recalcular()
                return self.mensajes[antes:]
            msgs = self.ejecutar(clave, ev.caso, ev.nodo, gratis=True)
            if clave in ("verificar", "reportar") and not ev.nodo.es_veraz and ev.jugador.logro("Sangre fría"):
                msgs.append(Mensaje(f"Logro de {ev.jugador.nombre}: Sangre fría", "logro"))
                self.log(msgs[-1].texto, "logro")
            return msgs
        finally:
            self.turno_idx = actual

    def resumen(self) -> dict:
        return dict(salud=self.ciudad.salud(), indicadores=dict(self.ciudad.v),
                    ranking=sorted(self.jugadores, key=lambda j: -j.puntos),
                    apoyo=dict(self.apoyo), eleccion=self.eleccion)

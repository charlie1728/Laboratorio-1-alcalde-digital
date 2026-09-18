"""Lógica de la partida (sin nada de interfaz: se puede probar sola).

Flujo: cada RONDA todos los jugadores juegan un turno (3 puntos de atención).
Al cerrar la ronda ocurre la OLA DE PROPAGACIÓN (los árboles crecen y mutan)
y un EVENTO ALEATORIO.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from ..estructuras.arbol_mutaciones import ArbolMutaciones, NodoMutacion
from ..estructuras.archivo_avl import ArchivoHechosAVL
from .afirmacion import DISTORSIONES
from .ciudad import Ciudad
from .hechos import CANDIDATOS, Hecho, catalogo
from .roles import ROLES

CIUDADANOS = ["Ana", "Luis", "Pedro", "María", "Carlos", "Sofía", "Andrés",
              "Camila", "Jorge", "Daniela", "Mateo", "Paula", "Iván", "Rosa",
              "Kevin", "Laura", "Nicolás", "Valeria", "Samuel", "Juliana"]

ATENCION_POR_TURNO = 3
MAX_NODOS_CASO = 30
MAX_CASOS = 3
PROF_MAX = 6


@dataclass
class Jugador:
    nombre: str
    rol: str
    color: tuple
    puntos: int = 0
    reputacion: int = 50
    atencion: int = ATENCION_POR_TURNO
    logros: list = field(default_factory=list)
    candidato: Optional[str] = None      # nombre si rol == candidato

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


@dataclass
class Mensaje:
    texto: str
    tipo: str = "info"          # info | bueno | malo | evento | logro


@dataclass
class EventoViral:
    caso: Caso
    nodo: NodoMutacion
    jugador: Jugador
    segundos: int


class Partida:
    def __init__(self, config_jugadores: list[tuple[str, str, tuple]],
                 rondas: int = 8, semilla: Optional[int] = None):
        if not 2 <= len(config_jugadores) <= 4:
            raise ValueError("El juego es de 2 a 4 jugadores")
        self.rng = random.Random(semilla)
        self.rondas_totales = rondas
        self.ronda = 1
        self.turno_idx = 0
        self.terminada = False
        self.ciudad = Ciudad()
        self.mensajes: list[Mensaje] = []
        self.evento_viral: Optional[EventoViral] = None
        self.ultimo_resaltado: dict = {}     # la UI lo usa para animar
        self.apoyo = {c[0]: 25.0 for c in CANDIDATOS}
        self._ajuste_desinfo = 0.0
        self._sig_caso = 1

        libres = [c[0] for c in CANDIDATOS]
        self.jugadores: list[Jugador] = []
        for nombre, rol, color in config_jugadores:
            j = Jugador(nombre, rol, color)
            if rol == "candidato":
                j.candidato = libres.pop(0)
            self.jugadores.append(j)

        # Archivo de hechos (AVL) con los hechos ya registrados
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
        self.log("Ronda 1: circulan las primeras publicaciones en Civitas.", "evento")

    # ------------------------------------------------------------ utilidades
    def log(self, texto: str, tipo: str = "info") -> None:
        self.mensajes.append(Mensaje(texto, tipo))

    @property
    def jugador_actual(self) -> Jugador:
        return self.jugadores[self.turno_idx]

    def casos_abiertos(self) -> list[Caso]:
        return [c for c in self.casos if c.abierto]

    def _caso_de(self, nodo: NodoMutacion) -> Optional[Caso]:
        for c in self.casos_abiertos():
            if nodo.id in c.arbol:
                return c
        return None

    def _ciudadano(self) -> str:
        return self.rng.choice(CIUDADANOS)

    def _nuevo_caso(self, falso: bool, sobre_candidato: bool = False) -> Optional[Caso]:
        usados = {c.hecho.id for c in self.casos_abiertos()}
        libres = [h for h in self.hechos.values() if h.id not in usados]
        if sobre_candidato:
            libres = [h for h in libres if h.sujetos_falsos] or libres
        if not libres:
            return None
        hecho = self.rng.choice(libres)
        af = hecho.afirmacion_real()
        dist = None
        if falso:
            # Fabricado desde el origen: dos distorsiones en la raíz
            ops = af.posibles_distorsiones(hecho)
            if sobre_candidato and "atribucion" in ops:
                elegidas = ["atribucion"] + self.rng.sample([o for o in ops if o != "atribucion"], 1)
            else:
                elegidas = self.rng.sample(ops, 2)
            for d in elegidas:
                af = af.mutar(d, hecho, self.rng)
            dist = elegidas[0]
        autor = hecho.fuente if not falso else self._ciudadano()
        raiz = NodoMutacion(af, autor, self.ronda, distorsion=dist,
                            alcance=self.rng.randint(20, 40))
        if falso and len(af.distorsiones) > 1:
            raiz.distorsion = "+".join(af.distorsiones)
        arbol = ArbolMutaciones(hecho.titulo, raiz)
        caso = Caso(self._sig_caso, hecho, arbol)
        self._sig_caso += 1
        self.casos.append(caso)
        # primeros reenvíos
        for _ in range(self.rng.randint(2, 3)):
            self._reenviar(caso, raiz, prob_mutar=0.4)
        return caso

    def _reenviar(self, caso: Caso, padre: NodoMutacion, prob_mutar: float = 0.3,
                  autor: Optional[str] = None, alcance: Optional[int] = None,
                  sin_mutar: bool = False) -> Optional[NodoMutacion]:
        """Crea un reenvío (hijo). Puede introducir UNA distorsión nueva."""
        if len(caso.arbol) >= MAX_NODOS_CASO:
            return None
        af, dist = padre.afirmacion, None
        if not sin_mutar and not padre.es_correccion and self.rng.random() < prob_mutar:
            ops = af.posibles_distorsiones(caso.hecho)
            if ops:
                dist = self.rng.choice(ops)
                af = af.mutar(dist, caso.hecho, self.rng)
        hijo = NodoMutacion(af, autor or self._ciudadano(), self.ronda, dist,
                            alcance if alcance is not None else self.rng.randint(5, 30),
                            es_correccion=padre.es_correccion)
        return caso.arbol.insertar(padre.id, hijo)

    # --------------------------------------------------- cálculo indicadores
    def _recalcular(self) -> None:
        total = falso = nodos = verif = 0
        for c in self.casos_abiertos():
            e = c.arbol.estadisticas()
            total += e["alcance"]
            falso += e["alcance_falso"]
            nodos += e["nodos"]
            verif += e["verificados"]
        ratio = falso / total if total else 0
        self.ciudad.fijar("desinformacion", ratio * 70 + self._ajuste_desinfo)
        base_info = (verif / nodos * 60) if nodos else 30
        self.ciudad.fijar("info_verificada", 20 + base_info + max(0, -self._ajuste_desinfo) / 2)

    # ================================================================ ACCIONES
    def acciones_para(self, nodo: Optional[NodoMutacion]) -> list[dict]:
        """Qué puede hacer el jugador actual con el nodo seleccionado."""
        j = self.jugador_actual
        esp_clave, esp_nombre, esp_costo = j.info_rol["especial"]
        acciones = [
            dict(clave="compartir", nombre="Compartir", costo=1),
            dict(clave="verificar", nombre="Verificar", costo=1),
            dict(clave="reportar", nombre="Reportar", costo=1),
            dict(clave="ignorar", nombre="Ignorar", costo=1),
            dict(clave=esp_clave, nombre=esp_nombre, costo=esp_costo, especial=True),
        ]
        if nodo is not None and nodo.autor == j.nombre and not nodo.es_correccion:
            acciones.append(dict(clave="borrar", nombre="Borrar mi publicación", costo=1))
        for a in acciones:
            a["ok"], a["motivo"] = True, ""
            if nodo is None:
                a["ok"], a["motivo"] = False, "Selecciona una publicación"
            elif j.atencion < a["costo"]:
                a["ok"], a["motivo"] = False, "Sin atención suficiente"
            elif nodo.es_correccion and a["clave"] not in ("compartir", "ignorar"):
                a["ok"], a["motivo"] = False, "Es un desmentido"
            elif a["clave"] in ("alertar", "amplificar", "desmentir"):
                if not nodo.verificado or nodo.es_veraz:
                    a["ok"], a["motivo"] = False, "Requiere una versión verificada como falsa"
                elif nodo.inmune:
                    a["ok"], a["motivo"] = False, "Esa rama ya está contenida"
            elif a["clave"] == "compartir" and nodo.inmune and not nodo.es_correccion:
                a["ok"], a["motivo"] = False, "Rama contenida"
            elif a["clave"] == "compartir" and self._caso_de(nodo) and \
                    len(self._caso_de(nodo).arbol) >= MAX_NODOS_CASO:
                a["ok"], a["motivo"] = False, "Hilo saturado"
        return acciones

    def ejecutar(self, clave: str, caso: Caso, nodo: NodoMutacion,
                 gratis: bool = False) -> list[Mensaje]:
        j = self.jugador_actual
        acc = next(a for a in self.acciones_para(nodo) if a["clave"] == clave)
        if not gratis and not acc["ok"]:
            return [Mensaje(acc["motivo"], "malo")]
        antes = len(self.mensajes)
        self.ultimo_resaltado = {}
        getattr(self, "_a_" + clave)(j, caso, nodo)
        if not gratis:
            j.atencion -= acc["costo"]
        j.reputacion = max(0, min(100, j.reputacion))
        self._cerrar_casos()
        self._recalcular()
        return self.mensajes[antes:]

    # --- básicas --------------------------------------------------------
    def _a_compartir(self, j: Jugador, caso: Caso, nodo: NodoMutacion) -> None:
        mult = j.info_rol["mult_alcance"]
        nuevo = self._reenviar(caso, nodo, autor=j.nombre, alcance=15 * mult, sin_mutar=True)
        if nuevo is None:
            self.log("Este hilo ya está saturado; nadie más lo ve.", "info")
            return
        nuevo.inmune = nodo.inmune
        self.ultimo_resaltado = {"nuevos": [nuevo.id]}
        if j.rol == "influencer" and not nodo.inmune:
            for _ in range(2):
                extra = self._reenviar(caso, nuevo, prob_mutar=0.35)
                if extra:
                    self.ultimo_resaltado["nuevos"].append(extra.id)
        if nodo.es_veraz:
            if nodo.verificado or nodo.es_correccion:
                j.puntos += 10 * mult
                j.reputacion += 4
                self.ciudad.ajustar(confianza=2 * mult, bienestar=1)
                self._ajuste_desinfo -= 1.5 * mult
                self.log(f"{j.nombre} difundió información verificada. +{10 * mult} pts", "bueno")
            else:
                j.puntos += 2
                self.log(f"{j.nombre} compartió sin verificar... por suerte era cierta. +2 pts", "info")
        else:
            nodo.verificado = True
            j.puntos -= 5 * mult
            j.reputacion -= 8 * mult // 2 + 4
            self.ciudad.ajustar(conflictos=2 * mult, confianza=-2 * mult)
            self._ajuste_desinfo += 3 * mult
            nombres = ", ".join(DISTORSIONES[d] for d in nodo.afirmacion.distorsiones)
            self.log(f"{j.nombre} amplificó una versión FALSA ({nombres}). "
                     f"-{5 * mult} pts, reputación baja.", "malo")

    def _a_verificar(self, j: Jugador, caso: Caso, nodo: NodoMutacion) -> None:
        hecho, comps, ruta = self.archivo.buscar(caso.hecho.id)
        self.ultimo_resaltado = {"avl_ruta": ruta, "verificado": [nodo.id]}
        if hecho is None:
            if j.rol == "periodista":
                n_rot = len(self.archivo.bitacora)
                self.archivo.insertar(caso.hecho.id, caso.hecho)
                nuevas = self.archivo.bitacora[n_rot:]
                rot = "; ".join(nuevas) if nuevas else "sin rotaciones"
                self.log(f"{j.nombre} investigó y registró '{caso.hecho.titulo}' "
                         f"en el Archivo ({rot}).", "evento")
                hecho, comps, ruta = self.archivo.buscar(caso.hecho.id)
                self.ultimo_resaltado["avl_ruta"] = ruta
                j.puntos += 4
            else:
                self.log(f"Verificación inconclusa: '{caso.hecho.titulo}' aún no está en el "
                         f"Archivo ({comps} comparaciones). Un periodista puede investigarlo.", "info")
                return
        dif = nodo.afirmacion.comparar_con(hecho)
        ya = nodo.verificado
        nodo.verificado = True
        if not ya:
            j.puntos += 5
            j.reputacion += 2
            self.ciudad.ajustar(confianza=1)
        if dif:
            self.log(f"Verificado ({comps} comp. en el Archivo): FALSO -> "
                     + ", ".join(DISTORSIONES[d] for d in dif), "bueno")
        else:
            self.log(f"Verificado ({comps} comp. en el Archivo): coincide con el hecho oficial.", "bueno")
        if len(j.logros) == 0 and j.logro("Primer chequeo"):
            self.log(f"Logro de {j.nombre}: Primer chequeo", "logro")

    def _a_reportar(self, j: Jugador, caso: Caso, nodo: NodoMutacion) -> None:
        if nodo.es_veraz:
            j.reputacion -= 8
            j.puntos -= 4
            self.ciudad.ajustar(confianza=-3, convivencia=-2)
            nodo.verificado = True
            self.log("Civitas revisó el reporte: el contenido era VERDADERO. "
                     "Reporte rechazado (-4 pts). Reportar lo cierto también hace daño.", "malo")
            return
        eliminados = caso.arbol.podar(nodo.id)
        falsos = sum(1 for n in eliminados if not n.es_veraz)
        alc = sum(n.alcance for n in eliminados if not n.es_veraz)
        pts = 6 + 2 * falsos
        j.puntos += pts
        j.reputacion += 3
        self.ciudad.ajustar(convivencia=2, conflictos=-1)
        self._ajuste_desinfo -= alc / 25
        self.ultimo_resaltado = {"podados": [n.id for n in eliminados]}
        self.log(f"Reporte aceptado: se retiraron {len(eliminados)} publicaciones "
                 f"({alc} personas dejaron de verlas). +{pts} pts", "bueno")
        if len(eliminados) >= 5 and j.logro("Poda limpia"):
            self.log(f"Logro de {j.nombre}: Poda limpia (5+ reenvíos de un tajo)", "logro")

    def _a_ignorar(self, j: Jugador, caso: Caso, nodo: NodoMutacion) -> None:
        if not nodo.es_veraz:
            j.puntos += 2
            self.ciudad.ajustar(bienestar=1)
            self.log(f"{j.nombre} no alimentó el rumor. +2 pts (bienestar +1)", "info")
        else:
            self.log(f"{j.nombre} dejó pasar la publicación.", "info")

    def _a_borrar(self, j: Jugador, caso: Caso, nodo: NodoMutacion) -> None:
        """eliminar_nodo: los reenvíos NO desaparecen, se re-enganchan al abuelo."""
        hijos = len(nodo.hijos)
        caso.arbol.eliminar_nodo(nodo.id)
        self.ultimo_resaltado = {"podados": [nodo.id]}
        if hijos:
            self.log(f"{j.nombre} borró su publicación, pero sus {hijos} reenvíos siguen "
                     "circulando: borrar no deshace lo compartido.", "malo" if not nodo.es_veraz else "info")
        else:
            self.log(f"{j.nombre} borró su publicación antes de que alguien la reenviara.", "bueno")
            if not nodo.es_veraz:
                j.puntos += 3
                j.reputacion += 2

    # --- especiales -----------------------------------------------------
    def _a_alertar(self, j: Jugador, caso: Caso, nodo: NodoMutacion) -> None:
        marcados = [nodo] + list(nodo.hijos)
        for n in marcados:
            n.inmune = True
        j.puntos += 3 + 2 * len(marcados)
        self.ciudad.ajustar(convivencia=2, bienestar=1)
        self._ajuste_desinfo -= len(marcados)
        self.ultimo_resaltado = {"inmunes": [n.id for n in marcados]}
        self.log(f"{j.nombre} alertó a sus contactos: {len(marcados)} reenvíos dejan de circular.", "bueno")

    def _a_rastrear(self, j: Jugador, caso: Caso, nodo: NodoMutacion) -> None:
        camino = caso.arbol.camino_a_raiz(nodo.id)
        puntos = caso.arbol.punto_de_mutacion(nodo.id)
        for n in camino:
            n.verificado = True
        self.ultimo_resaltado = {"camino": [n.id for n in camino],
                                 "mutacion": [n.id for n in puntos.values()]}
        j.puntos += 4 + 2 * len(camino)
        j.reputacion += 4
        self.ciudad.ajustar(confianza=3)
        self._ajuste_desinfo -= 2
        if not puntos:
            self.log(f"Rastreo: {len(camino)} saltos hasta el origen y ninguna distorsión. Es fiel al hecho.", "bueno")
            return
        partes = []
        for d, n in puntos.items():
            nombre = " + ".join(DISTORSIONES.get(x, x) for x in d.split("+"))
            quien = "desde el ORIGEN" if n.es_raiz else f"en el reenvío de {n.autor} (ola {n.profundidad})"
            partes.append(f"{nombre} {quien}")
        self.log("Rastreo (" + str(len(camino)) + " saltos): " + "; ".join(partes), "bueno")
        if j.logro("Paciente cero"):
            self.log(f"Logro de {j.nombre}: Paciente cero", "logro")

    def _a_amplificar(self, j: Jugador, caso: Caso, nodo: NodoMutacion) -> None:
        puntos = caso.arbol.punto_de_mutacion(nodo.id)
        # la distorsión más alta (más cerca de la raíz) es la que hay que cortar
        objetivo = min(puntos.values(), key=lambda n: n.profundidad) if puntos else nodo
        marcados = caso.arbol.inmunizar(objetivo.id)
        corr = NodoMutacion(caso.hecho.afirmacion_real(), j.nombre, self.ronda,
                            alcance=60, es_correccion=True)
        corr.inmune = True
        corr.verificado = True
        destino = objetivo.padre or objetivo
        caso.arbol.insertar(destino.id, corr)
        j.puntos += 6 + 2 * len(marcados)
        j.reputacion += 6
        self.ciudad.ajustar(confianza=4, convivencia=2)
        self._ajuste_desinfo -= len(marcados) * 1.5
        self.ultimo_resaltado = {"inmunes": [n.id for n in marcados], "nuevos": [corr.id]}
        self.log(f"{j.nombre} amplificó un desmentido: {len(marcados)} reenvíos contenidos "
                 f"desde el punto de mutación.", "bueno")

    def _a_desmentir(self, j: Jugador, caso: Caso, nodo: NodoMutacion) -> None:
        marcados = caso.arbol.inmunizar(nodo.id)
        corr = NodoMutacion(caso.hecho.afirmacion_real(), j.nombre, self.ronda,
                            alcance=40, es_correccion=True)
        corr.inmune = corr.verificado = True
        caso.arbol.insertar(nodo.id, corr)
        sobre_mi = j.candidato and j.candidato in nodo.afirmacion.sujeto
        bonus = 2 if sobre_mi else 1
        j.puntos += (5 + len(marcados)) * bonus
        j.reputacion += 3 * bonus
        if j.candidato:
            self.apoyo[j.candidato] += 3 * bonus
        self.ciudad.ajustar(confianza=2 * bonus)
        self._ajuste_desinfo -= len(marcados)
        self.ultimo_resaltado = {"inmunes": [n.id for n in marcados], "nuevos": [corr.id]}
        extra = " ¡Era un rumor sobre su campaña: apoyo x2!" if sobre_mi else ""
        self.log(f"Desmentido oficial de {j.nombre}: {len(marcados)} reenvíos contenidos.{extra}", "bueno")

    # ================================================================ TURNOS
    def terminar_turno(self) -> None:
        self.turno_idx += 1
        if self.turno_idx >= len(self.jugadores):
            self.turno_idx = 0
            self._fin_de_ronda()
        self.jugador_actual.atencion = ATENCION_POR_TURNO
        if not self.terminada:
            self.log(f"Turno de {self.jugador_actual.nombre} "
                     f"({self.jugador_actual.info_rol['nombre']}).", "info")

    def _cerrar_casos(self) -> None:
        for c in self.casos_abiertos():
            if c.arbol.raiz is None:
                c.abierto = False
                self.log(f"Caso '{c.hecho.titulo}' eliminado de Civitas.", "evento")
            elif not c.arbol.frontera() and not all(n.es_veraz for n in c.arbol.preorden()):
                c.abierto = False
                self.log(f"Caso '{c.hecho.titulo}' contenido: ya no se propaga.", "evento")

    def _ola_de_propagacion(self) -> int:
        """Recorre cada árbol POR NIVELES: los nodos de la última ola son los
        más activos (acaban de llegar a gente nueva)."""
        nuevos = 0
        for c in self.casos_abiertos():
            niveles = c.arbol.por_niveles()
            ultimo = len(niveles) - 1
            for d, nivel in enumerate(niveles):
                for n in list(nivel):
                    if n.inmune or n.es_correccion or d >= PROF_MAX:
                        continue
                    p = 0.40 if d >= ultimo - 1 else 0.08
                    veces = 2 if n.viral else 1
                    for _ in range(veces):
                        if self.rng.random() < p and self._reenviar(c, n):
                            nuevos += 1
                    n.viral = False
        return nuevos

    def _fin_de_ronda(self) -> None:
        nuevos = self._ola_de_propagacion()
        self.log(f"Ola de propagación: {nuevos} reenvíos nuevos en Civitas.", "evento")
        # los rumores vivos sobre candidatos les quitan apoyo
        for c in self.casos_abiertos():
            for n in c.arbol.frontera():
                if "atribucion" in n.afirmacion.distorsiones:
                    for nombre in self.apoyo:
                        if nombre in n.afirmacion.sujeto:
                            self.apoyo[nombre] = max(0, self.apoyo[nombre] - 0.5)
        # deriva natural de la ciudad
        d = self.ciudad.v["desinformacion"]
        self.ciudad.ajustar(conflictos=(d - 30) / 12, convivencia=-(d - 30) / 15,
                            bienestar=-(d - 35) / 20)
        self._ajuste_desinfo *= 0.85
        self._evento_aleatorio()
        self._cerrar_casos()
        if not self.casos_abiertos():
            self._nuevo_caso(falso=self.rng.random() < 0.6)
        self._recalcular()
        self.ciudad.guardar()
        self.ronda += 1
        if self.ronda > self.rondas_totales:
            self.terminada = True
            self.log("Fin de la campaña. (La elección del alcalde llega en la entrega final.)", "evento")
        else:
            self.log(f"Ronda {self.ronda}.", "evento")

    def _evento_aleatorio(self) -> None:
        eventos = [("falsa", 3), ("rumor", 3), ("verdadera", 2), ("viral", 4),
                   ("discusion", 2), ("campana", 2), ("reporte_npc", 2), ("vence", 1)]
        if len(self.casos_abiertos()) >= MAX_CASOS:
            eventos = [e for e in eventos if e[0] not in ("falsa", "rumor", "verdadera")]
        tipo = self.rng.choices([e[0] for e in eventos], [e[1] for e in eventos])[0]
        if tipo == "falsa":
            c = self._nuevo_caso(falso=True)
            if c:
                self.log(f"EVENTO: aparece una noticia falsa sobre '{c.hecho.titulo}'.", "evento")
        elif tipo == "rumor":
            c = self._nuevo_caso(falso=True, sobre_candidato=True)
            if c:
                self.log(f"EVENTO: rumor sobre un candidato ('{c.hecho.titulo}').", "evento")
        elif tipo == "verdadera":
            c = self._nuevo_caso(falso=False)
            if c:
                self.log(f"EVENTO: se publica una noticia verdadera ('{c.hecho.titulo}').", "evento")
        elif tipo == "viral":
            cands = [(c, n) for c in self.casos_abiertos() for n in c.arbol.frontera()]
            if cands:
                c, n = self.rng.choice(cands)
                n.viral = True
                j = self.jugadores[0]
                self.evento_viral = EventoViral(c, n, j, j.info_rol["tiempo_viral"])
                self.log("EVENTO: ¡una publicación se está volviendo VIRAL!", "evento")
        elif tipo == "discusion":
            self.ciudad.ajustar(conflictos=6, convivencia=-4)
            self.log(f"EVENTO: {self._ciudadano()} y {self._ciudadano()} discuten en los comentarios. "
                     "Conflictos +6", "evento")
        elif tipo == "campana":
            self.ciudad.ajustar(convivencia=6, bienestar=4)
            self.log("EVENTO: campaña de convivencia digital en el Colegio. Convivencia +6", "evento")
        elif tipo == "reporte_npc":
            falsos = [(c, n) for c in self.casos_abiertos() for n in c.arbol.hojas()
                      if not n.es_veraz and not n.es_raiz]
            if falsos:
                c, n = self.rng.choice(falsos)
                c.arbol.podar(n.id)
                self.log(f"EVENTO: {self._ciudadano()} reportó un reenvío falso y fue retirado.", "evento")
        elif tipo == "vence":
            en_uso = {c.hecho.id for c in self.casos_abiertos()}
            libres = [k for k, _ in self.archivo.inorden() if k not in en_uso]
            if libres:
                k = self.rng.choice(libres)
                self.archivo.eliminar(k)
                self.log(f"EVENTO: el hecho '{self.hechos[k].titulo}' venció y salió del Archivo.", "evento")

    def resolver_viral(self, clave: Optional[str]) -> list[Mensaje]:
        """Decisión bajo presión de tiempo. None = se acabó el tiempo."""
        ev, self.evento_viral = self.evento_viral, None
        if ev is None or ev.nodo.id not in ev.caso.arbol:
            return []
        actual = self.turno_idx
        self.turno_idx = self.jugadores.index(ev.jugador)
        try:
            if clave is None:
                antes = len(self.mensajes)
                for _ in range(3):
                    self._reenviar(ev.caso, ev.nodo, prob_mutar=0.5)
                if not ev.nodo.es_veraz:
                    self._ajuste_desinfo += 4
                self.log("Nadie reaccionó a tiempo: la publicación viral generó 3 reenvíos más.", "malo")
                self._recalcular()
                return self.mensajes[antes:]
            msgs = self.ejecutar(clave, ev.caso, ev.nodo, gratis=True)
            if clave in ("verificar", "reportar") and not ev.nodo.es_veraz and ev.jugador.logro("Sangre fría"):
                msgs.append(Mensaje(f"Logro de {ev.jugador.nombre}: Sangre fría", "logro"))
                self.log(msgs[-1].texto, "logro")
            return msgs
        finally:
            self.turno_idx = actual

    # ================================================================ RESUMEN
    def resumen(self) -> dict:
        return dict(salud=self.ciudad.salud(), indicadores=dict(self.ciudad.v),
                    ranking=sorted(self.jugadores, key=lambda j: -j.puntos),
                    apoyo=dict(self.apoyo))

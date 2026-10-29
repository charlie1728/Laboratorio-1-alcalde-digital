"""Convierte una Partida en un diccionario JSON y viceversa.

El servidor envía este diccionario a los clientes después de cada jugada; el cliente
reconstruye una Partida "espejo" con los mismos árboles y grafos para dibujarla.
  * Árbol de mutaciones: se envía en preorden (cada padre llega antes que sus hijos),
    así que se reconstruye insertando en ese mismo orden.
  * Archivo AVL: se envía su preorden y se reconstruye con la misma forma, sin rotar.
  * Grafos: lista de vértices y lista de aristas con sus pesos.
"""
from __future__ import annotations

import random
from dataclasses import asdict

from ..estructuras.arbol_mutaciones import ArbolMutaciones, NodoMutacion
from ..estructuras.archivo_avl import ArchivoHechosAVL
from ..estructuras.grafo import Grafo
from .afirmacion import Afirmacion
from .ciudad import Ciudad
from .hechos import catalogo
from .mapa import crear_mapa
from .partida import Caso, EventoViral, Jugador, Mensaje, Partida
from .red_social import Ciudadano

MENSAJES_ENVIADOS = 80


def _af(af: Afirmacion) -> dict:
    d = asdict(af)
    d["distorsiones"] = list(af.distorsiones)
    return d


def _af_desde(d: dict) -> Afirmacion:
    d = dict(d)
    d["distorsiones"] = tuple(d["distorsiones"])
    return Afirmacion(**d)


def arbol_a_lista(arbol: ArbolMutaciones) -> list[dict]:
    return [dict(id=n.id, padre=n.padre.id if n.padre else None, autor=n.autor, turno=n.turno,
                 distorsion=n.distorsion, alcance=n.alcance, correccion=n.es_correccion,
                 verificado=n.verificado, inmune=n.inmune, viral=n.viral, entregado=n.entregado,
                 af=_af(n.afirmacion)) for n in arbol.preorden()]


def arbol_desde_lista(titulo: str, lista: list[dict]) -> ArbolMutaciones:
    def nodo(d):
        n = NodoMutacion(_af_desde(d["af"]), d["autor"], d["turno"], d["distorsion"], d["alcance"],
                         es_correccion=d["correccion"], id=d["id"])
        n.verificado, n.inmune, n.viral, n.entregado = d["verificado"], d["inmune"], d["viral"], d["entregado"]
        return n
    if not lista:
        arbol = ArbolMutaciones(titulo, NodoMutacion(Afirmacion("", "", "", "", ""), "", id=-1))
        arbol.podar(-1)
        return arbol
    arbol = ArbolMutaciones(titulo, nodo(lista[0]))
    for d in lista[1:]:
        arbol.insertar(d["padre"], nodo(d))
    return arbol


def partida_a_dict(p: Partida) -> dict:
    datos_red = {v: asdict(p.red.dato(v)) for v in p.red.vertices()}
    viral = None
    if p.evento_viral:
        ev = p.evento_viral
        viral = dict(caso=ev.caso.id, nodo=ev.nodo.id, jugador=p.jugadores.index(ev.jugador),
                     segundos=ev.segundos)
    off = getattr(p, "_off_mensajes", 0)
    recientes = p.mensajes[-MENSAJES_ENVIADOS:]
    return dict(
        ronda=p.ronda, rondas_totales=p.rondas_totales, turno_idx=p.turno_idx, terminada=p.terminada,
        jugadores=[dict(asdict(j), color=list(j.color)) for j in p.jugadores],
        ciudad=dict(v=p.ciudad.v, historial=p.ciudad.historial),
        red=dict(grafo=p.red.a_dict(), datos=datos_red),
        archivo=dict(preorden=list(p.archivo.preorden()), bitacora=p.archivo.bitacora[-12:]),
        casos=[dict(id=c.id, hecho=c.hecho.id, abierto=c.abierto, ronda_inicio=c.ronda_inicio,
                    receptores=c.receptores, creencia=c.creencia, descubierto=c.descubierto,
                    cierre=c.cierre, arbol=arbol_a_lista(c.arbol)) for c in p.casos],
        viral=viral, apoyo=p.apoyo, apoyo_zona=p.apoyo_zona, tension_extra=p.tension_extra,
        ultimo_resaltado=p.ultimo_resaltado, eleccion=p.eleccion,
        mensajes=[[m.texto, m.tipo] for m in recientes],
        n_mensajes=off + len(p.mensajes), anim=p.anim[-40:], seq=p._seq,
        ajuste=p._ajuste_desinfo, sig_caso=p._sig_caso,
    )


def partida_desde_dict(d: dict) -> Partida:
    p = Partida.__new__(Partida)
    p.rng = random.Random(0)
    p.ronda, p.rondas_totales = d["ronda"], d["rondas_totales"]
    p.turno_idx, p.terminada = d["turno_idx"], d["terminada"]
    p.ciudad = Ciudad()
    p.ciudad.v = dict(d["ciudad"]["v"])
    p.ciudad.historial = [dict(h) for h in d["ciudad"]["historial"]]
    p.mensajes = [Mensaje(t, tipo) for t, tipo in d["mensajes"]]
    p._off_mensajes = d["n_mensajes"] - len(p.mensajes)
    p.anim, p._seq = list(d["anim"]), d["seq"]
    p.apoyo = dict(d["apoyo"])
    p.apoyo_zona = {z: dict(v) for z, v in d["apoyo_zona"].items()}
    p.tension_extra = dict(d["tension_extra"])
    p.aristas_rotas = []
    p.eleccion = d["eleccion"]
    p.ultimo_resaltado = d["ultimo_resaltado"] or {}
    p._ajuste_desinfo, p._sig_caso, p._visitas = d["ajuste"], d["sig_caso"], set()
    p.mapa = crear_mapa()
    datos = {v: Ciudadano(**c) for v, c in d["red"]["datos"].items()}
    p.red = Grafo.desde_dict(d["red"]["grafo"], datos)
    p.jugadores = [Jugador(**dict(j, color=tuple(j["color"]))) for j in d["jugadores"]]
    p.hechos = {h.id: h for h in catalogo()}
    p.archivo = ArchivoHechosAVL.desde_preorden(d["archivo"]["preorden"], lambda k: p.hechos[k])
    p.archivo.bitacora = list(d["archivo"]["bitacora"])
    p.casos = []
    for c in d["casos"]:
        hecho = p.hechos[c["hecho"]]
        p.casos.append(Caso(c["id"], hecho, arbol_desde_lista(hecho.titulo, c["arbol"]), c["abierto"],
                            c["ronda_inicio"], dict(c["receptores"]), dict(c["creencia"]),
                            c["descubierto"], c["cierre"]))
    p.evento_viral = None
    if d["viral"]:
        v = d["viral"]
        caso = p.caso_por_id(v["caso"])
        nodo = caso.arbol.buscar(v["nodo"]) if caso else None
        if nodo is not None:
            p.evento_viral = EventoViral(caso, nodo, p.jugadores[v["jugador"]], v["segundos"])
    return p

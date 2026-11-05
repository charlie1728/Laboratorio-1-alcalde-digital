"""Opciones, récords (en un AVL) y logros guardados en la carpeta datos/."""
import json
import time

from .config import DATOS
from .estructuras.avl import AVL

OPCIONES_BASE = {"musica": 0.45, "efectos": 0.8, "subtitulos": True, "contraste": False,
                 "tranquilo": False, "pantalla_completa": False, "pistas": True, "duracion": 90, "rondas": 2}


def _leer(nombre, defecto):
    try:
        return json.loads((DATOS / nombre).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defecto


def _escribir(nombre, datos):
    try:
        DATOS.mkdir(parents=True, exist_ok=True)
        (DATOS / nombre).write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass


def cargar_opciones():
    op = dict(OPCIONES_BASE)
    op.update(_leer("opciones.json", {}))
    return op


def guardar_opciones(op):
    _escribir("opciones.json", op)


class Records:
    """Tabla de récords: un AVL ordenado por (puntos, momento). Se guarda como lista."""
    MAXIMO = 200

    def __init__(self):
        self.arbol = AVL()
        for r in _leer("records.json", []):
            self.arbol.insertar((r["total"], r["t"]), r)

    def agregar(self, nombre, personaje, total, salvados):
        r = {"nombre": nombre, "personaje": personaje, "total": total, "salvados": salvados,
             "t": time.time(), "fecha": time.strftime("%d/%m %H:%M")}
        self.arbol.insertar((total, r["t"]), r)
        while len(self.arbol) > self.MAXIMO:
            self.arbol.eliminar(self.arbol.menor())
        _escribir("records.json", [v for _, v in self.arbol.en_orden()])
        puesto = [v for _, v in self.arbol.mejores(len(self.arbol))].index(r) + 1
        return puesto

    def mejores(self, k=10):
        return [v for _, v in self.arbol.mejores(k)]


LOGROS = [
    ("primer", "Primer Bulo", "Atrapa tu primer Bulo", lambda r: r["stats"]["bulos"] >= 1),
    ("cazador", "Cazabulos", "Atrapa 25 Bulos en un turno", lambda r: r["stats"]["bulos"] >= 25),
    ("raiz", "Cortaste la raíz", "Tumba una cadena de 3 o más Bulos de un golpe", lambda r: r["stats"]["cadena"] >= 3),
    ("antena", "Señal cortada", "Apaga una antena del Bot", lambda r: r["stats"]["antenas"] >= 1),
    ("dos_antenas", "Sin señal", "Apaga 2 antenas en un turno", lambda r: r["stats"]["antenas"] >= 2),
    ("ojo", "Ojo de periodista", "Revisa 4 noticias antes de compartirlas", lambda r: r["stats"]["verificadas"] >= 4),
    ("cartero", "Cartero de la verdad", "Entrega 4 noticias reales", lambda r: r["stats"]["entregadas"] >= 4),
    ("paz", "Paz en el barrio", "Calma 2 peleas", lambda r: r["stats"]["peleas"] >= 2),
    ("viral", "Freno al viral", "Detén el Bulo viral", lambda r: r["stats"]["viral"] >= 1),
    ("salvador", "Barrio a salvo", "Termina con 15 vecinos o más a salvo", lambda r: r["salvados"] >= 15),
    ("limpio", "Cero cadenas", "Termina sin compartir ningún Bulo y con más de 200 puntos",
     lambda r: r["stats"]["compartidas_falsas"] == 0 and r["total"] >= 200),
    ("combo", "Imparable", "Haz un combo de 10", lambda r: r["stats"]["combo_max"] >= 10),
    ("medico", "Doctor de rumores", "Cura a 10 vecinos", lambda r: r["stats"]["curados"] >= 10),
    ("tres", "Tres estrellas", "Gana 3 estrellas de reputación", lambda r: r["reputacion"] >= 3),
]


class Logros:
    def __init__(self):
        self.ganados = set(_leer("logros.json", []))

    def revisar(self, resumen):
        nuevos = []
        for clave, nombre, desc, prueba in LOGROS:
            try:
                ok = prueba(resumen)
            except (KeyError, TypeError):
                ok = False
            if ok:
                nuevos.append((clave, nombre, desc, clave not in self.ganados))
                self.ganados.add(clave)
        _escribir("logros.json", sorted(self.ganados))
        return nuevos

"""Opciones, récords (en un AVL) y logros guardados en la carpeta datos/."""
import json
import time

from .config import DATOS
from .estructuras.avl import AVL

VERSION_OPCIONES = 2
OPCIONES_BASE = {"musica": 0.45, "efectos": 0.8, "subtitulos": False, "contraste": False,
                 "tranquilo": False, "pantalla_completa": True, "pistas": True, "duracion": 120, "rondas": 2,
                 "historia_vista": False, "volver_inicio": True, "version": VERSION_OPCIONES}
# Lo que cambió de una versión a otra y debe aplicarse aunque ya hubiera opciones guardadas:
# en la versión 2 el juego abre en pantalla completa, sin subtítulos de sonidos y con turnos de 2 minutos.
NUEVOS_EN_V2 = {"pantalla_completa": True, "subtitulos": False, "duracion": 120}


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
    guardadas = _leer("opciones.json", {})
    op.update(guardadas)
    if guardadas and guardadas.get("version", 1) < 2:
        op.update(NUEVOS_EN_V2)
    op["version"] = VERSION_OPCIONES
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
    ("tijeras", "Tijeras", "Corta 3 Bulos que viajaban por los hilos", lambda r: r["stats"]["pulsos"] >= 3),
    ("cartero", "Cartero de la verdad", "Comparte 3 estrellas", lambda r: r["stats"]["compartidas"] >= 3),
    ("paz", "Paz en el barrio", "Calma 2 peleas", lambda r: r["stats"]["peleas"] >= 2),
    ("viral", "Freno al viral", "Detén el Bulo viral", lambda r: r["stats"]["viral"] >= 1),
    ("salvador", "Barrio a salvo", "Termina con todos los vecinos a salvo", lambda r: r["salvados"] >= r["vecinos"]),
    ("limpio", "Cero cadenas", "Que nadie le pase un Bulo a un amigo (y más de 200 puntos)",
     lambda r: r["stats"]["regados"] == 0 and r["total"] >= 200),
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

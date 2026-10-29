from __future__ import annotations

# Opciones de personalización de personajes. El modelo solo guarda índices y nombres;
# la interfaz (ui/personajes.py) decide cómo se dibuja cada opción.

TONOS_PIEL = 6
PEINADOS = ["corto", "rapado", "afro", "largo", "cola", "mono", "ondulado", "trenzas", "calvo"]
COLORES_PELO = 7
COLORES_ROPA = 8
EXTRAS = ["", "gafas", "barba", "bigote", "aretes", "gorra"]

_PEINADOS_F = ["largo", "cola", "mono", "ondulado", "trenzas", "afro", "corto"]
_PEINADOS_M = ["corto", "rapado", "afro", "ondulado", "calvo", "corto", "rapado"]
_EXTRAS_F = ["", "", "aretes", "gafas", "aretes"]
_EXTRAS_M = ["", "", "barba", "bigote", "gafas", "gorra"]


def look_por_defecto(i: int = 0) -> dict:
    return dict(piel=(i * 2 + 1) % TONOS_PIEL, pelo=PEINADOS[i % 6],
                color_pelo=i % COLORES_PELO, ropa=i % COLORES_ROPA, extra="")


def look_aleatorio(rng, femenino: bool) -> dict:
    return dict(
        piel=rng.randrange(TONOS_PIEL),
        pelo=rng.choice(_PEINADOS_F if femenino else _PEINADOS_M),
        color_pelo=rng.randrange(COLORES_PELO),
        ropa=rng.randrange(COLORES_ROPA),
        extra=rng.choice(_EXTRAS_F if femenino else _EXTRAS_M),
    )


def normalizar(look: dict) -> dict:
    base = look_por_defecto()
    if not isinstance(look, dict):
        return base
    out = dict(base)
    out["piel"] = int(look.get("piel", base["piel"])) % TONOS_PIEL
    out["pelo"] = look.get("pelo") if look.get("pelo") in PEINADOS else base["pelo"]
    out["color_pelo"] = int(look.get("color_pelo", base["color_pelo"])) % COLORES_PELO
    out["ropa"] = int(look.get("ropa", base["ropa"])) % COLORES_ROPA
    out["extra"] = look.get("extra") if look.get("extra") in EXTRAS else ""
    return out

# Color de cada puesto de jugador (anillo en la red, ficha en el mapa, tarjetas).
COLORES_JUGADOR = [(108, 77, 245), (255, 150, 30), (0, 158, 115), (230, 70, 140)]

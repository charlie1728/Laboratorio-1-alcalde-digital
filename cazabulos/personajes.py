"""Los cuatro protagonistas, dibujados pixel a pixel (16x24) para que se distingan de lejos.

Cada personaje tiene una silueta propia (boina, copete, gorra, peinado), un color de equipo
y un objeto que lo identifica (cámara, celular, morral, corbata). Los vecinos del barrio usan
los sprites de Kenney (16x16), así que los jugadores se ven más grandes y nunca se confunden.

Las plantillas son filas de 16 caracteres. Las vistas de frente y de espaldas se escriben por
mitades (8 caracteres) y se reflejan, así quedan simétricas. La vista de lado mira a la derecha;
la izquierda se obtiene volteando la imagen.
"""
import pygame

ANCHO, ALTO = 16, 24
CONTORNO = (40, 26, 38)

PIELES = [(255, 218, 185), (240, 190, 145), (205, 142, 96), (150, 94, 60), (98, 60, 40)]
PELOS = [(40, 36, 52), (110, 66, 38), (236, 128, 52), (250, 206, 96), (230, 72, 162), (90, 120, 230)]


def sim(mitad):
    """Fila simétrica a partir de su mitad izquierda (8 caracteres)."""
    assert len(mitad) == 8, mitad
    return mitad + mitad[::-1]


def fila(*partes):
    s = "".join(partes)
    assert len(s) == 16, (s, len(s))
    return s


# ----------------------------------------------------------------- cuerpo base
CABEZA_FRENTE = [sim(m) for m in [
    "........", "........",
    "....kkkk", "...kssss", "..ksssss", "..ksssss", "..ksssss",
    "..kssess", "..kssess", "..krssss", "..kssssm", "...kssss", "....kkkk"]]
CABEZA_ESPALDA = [sim(m) for m in [
    "........", "........",
    "....kkkk", "...kssss", "..ksssss", "..ksssss", "..ksssss",
    "..ksssss", "..ksssss", "..ksssss", "..ksssss", "...kssss", "....kkkk"]]
CUERPO_FRENTE = [
    sim("....kttt"), sim("...ktttt"), sim("..ktTttt"), sim("..ktTttt"),
    fila("..ksk", "tttttt", "ksk.."),
    sim("...kkppp"), sim("...kpppp"), sim("...kpppk"), sim("...kpppk"), sim("...koook"), sim("...kkkk."),
]
CABEZA_LADO = [
    "................", "................",
    fila("....", "kkkkkkkk", "...."),
    fila("...", "k", "ssssssss", "k", "..."),
    fila("..", "k", "ssssssssss", "k", ".."),
    fila("..", "k", "ssssssssss", "k", ".."),
    fila("..", "k", "ssssssssss", "k", ".."),
    fila("..", "k", "ssssssss", "e", "s", "k", ".."),
    fila("..", "k", "ssssssss", "e", "s", "s", "k", "."),
    fila("..", "k", "sssssss", "r", "s", "s", "k", ".."),
    fila("..", "k", "sssssssss", "m", "k", ".."),
    fila("...", "k", "ssssssss", "k", "..."),
    fila("....", "kkkkkkkk", "...."),
]
CUERPO_LADO = [
    fila(".....", "k", "tttt", "k", "....."),
    fila("....", "k", "tttttt", "k", "...."),
    fila("....", "k", "ttTTtt", "k", "...."),
    fila("....", "k", "ttTTtt", "k", "...."),
    fila("....", "k", "ttsstt", "k", "...."),
    fila("....", "k", "pppppp", "k", "...."),
    fila("....", "k", "pppppp", "k", "...."),
    fila("....", "k", "pp", "kk", "pp", "k", "...."),
    fila("....", "k", "pp", "kk", "pp", "k", "...."),
    fila("....", "k", "ooo", "k", "ooo", "k", "..."),
    fila("....", "kkkk", ".", "kkkk", "..."),
]

BASE = {
    "frente": CABEZA_FRENTE + CUERPO_FRENTE,
    "espalda": CABEZA_ESPALDA + CUERPO_FRENTE,
    "lado": CABEZA_LADO + CUERPO_LADO,
}


def _vacia():
    return ["." * 16 for _ in range(ALTO)]


def _poner(capa, y, texto):
    """Pone una fila en la capa (los '.' no cambian nada)."""
    capa[y] = texto


# ----------------------------------------------------------------- detalles por personaje
# Cada capa es un dict {fila: texto de 16}. '.' deja lo de abajo, '_' borra el pixel.

def _capas_ana():
    f, e, l = {}, {}, {}
    # boina roja ladeada + melena negra corta (bob) + flequillo
    f.update({0: fila(".......", "kkk", "......"), 1: fila(".....", "kkaaak", "....."),
              2: fila("...", "k", "aaaaaaaaa", "k", ".."), 3: sim("..kAAAAA"),
              4: sim("..khhhhh"), 5: fila("..k", "hjhhhhhhhh", "k.."), 6: sim("..khhshh"),
              7: sim("..kh...."), 8: sim("..kh...."), 9: sim("..kh...."), 10: sim("..kh...."),
              11: sim("..khh..."), 12: sim("..kkk...")})
    # cámara colgada al pecho
    f.update({13: sim("....kc.."), 14: sim("...k.ccc"), 15: sim("....ccll"), 16: sim("....kccc"),
              18: sim("...kkttt"), 19: sim("...ktttt")})
    e.update({0: fila(".......", "kkk", "......"), 1: fila(".....", "kkaaak", "....."),
              2: fila("...", "k", "aaaaaaaaa", "k", ".."), 3: sim("..kAAAAA"),
              4: sim("..khhhhh"), 5: sim("..khhhhh"), 6: sim("..khhhhh"), 7: sim("..khhhhh"),
              8: sim("..khhhhh"), 9: sim("..khhhhh"), 10: sim("..khhhhh"), 11: sim("..kHhhhh"),
              12: sim("..kkkkkk"), 13: sim("....kc.."), 18: sim("...kkttt"), 19: sim("...ktttt")})
    l.update({0: fila("......", "kkk", "......."), 1: fila("....", "kkaaak", "......"),
              2: fila("..", "k", "aaaaaaaa", "k", "...."), 3: fila(".", "k", "AAAAAAAAAA", "k", "..."),
              4: fila("..", "k", "hhhhhhhhhh", "k", ".."), 5: fila("..", "k", "hhhhhhhjhh", "k", ".."),
              6: fila("..", "k", "hhhhhhh", "ss", "h", "k", ".."), 7: fila("..", "k", "hhhhh", ".....", "k", ".."),
              8: fila("..", "k", "hhhhh", "........"), 9: fila("..", "k", "hhhhh", "........"),
              10: fila("..", "k", "hhhh", "........."), 11: fila("..", "k", "hhhh", "........."),
              12: fila("..", "kkk", "...........")})
    l.update({14: fila("..........", "cck", "..."), 15: fila("..........", "cll", "..."),
              16: fila("..........", "cck", "..."),
              18: fila("....", "k", "tttttt", "k", "...."), 19: fila("....", "k", "tttttt", "k", "....")})
    return f, e, l


def _capas_beto():
    f, e, l = {}, {}, {}
    # copete alto fucsia + gafas de sol + capucha + celular
    f.update({0: sim(".....kkk"), 1: sim("....khjj"), 2: sim("...khhjh"), 3: sim("..khhhhh"),
              4: sim("..khhhhh"), 5: sim("..kHhHhH"), 6: sim("..kh.sss"),
              7: fila("..ks", "qwqqqqqq", "sk.."),
              8: fila("..ks", "qqq", "ss", "qqq", "sk.."), 9: sim("..ksssss"),
              10: fila("..ksss", "mmmm", "sssk..")})
    f.update({14: sim("...ktwtt"), 15: fila("..ktTttttttT", "f", "Fk."), 16: fila("..ktTttttttT", "f", "Fk."),
              17: fila("..ksk", "tttttt", "k", "s", "fk.")})
    e.update({0: sim(".....kkk"), 1: sim("....khhh"), 2: sim("...khhhh"), 3: sim("..khhjhh"),
              4: sim("..khhhhh"), 5: sim("..khhhhh"), 6: sim("..khhhhh"), 7: sim("..kHhhhh"),
              8: sim("..kHHHHH"), 13: sim("...kTTTT"), 14: sim("..kTTTTT"), 15: sim("..ktTTTT")})
    l.update({0: fila(".....", "kkkk", "......."), 1: fila("....", "k", "hhhj", "kk", "....."),
              2: fila("...", "k", "hhhhjjj", "k", "...."), 3: fila("..", "k", "hhhhhhhhhh", "k", ".."),
              4: fila("..", "k", "hhhhhhhhhh", "k", ".."), 5: fila("..", "k", "hhhhhhHhHh", "k", ".."),
              6: fila("..", "k", "hhhh", "......", "k", ".."), 7: fila("..", "k", "hhh", "......", "qqq", "k"),
              8: fila("..", "k", "hh", "......", "qq", "..."),
              13: fila("....", "k", "TT", "...", "k", "....."), 14: fila("...", "k", "TT", ".........."),
              15: fila("....", "k", "...", "...", "f", "F", "k", ".."), 16: fila("....", "k", "...", "..", "s", "f", "F", "k", ".."),
              17: fila("....", "k", "......", "k", "....")})
    return f, e, l


def _capas_caro():
    f, e, l = {}, {}, {}
    # gorra verde al revés + pelo naranja con cola + pecas + overol + morral
    f.update({1: sim(".....kkk"), 2: sim("...kaaaa"), 3: sim("..kaaaaa"), 4: fila("..k", "aAaaaaaaAa", "k.."),
              5: sim("..kAAAAA"), 6: sim("..khhshh"), 7: sim("..kh...."), 8: sim("..kh...."),
              9: fila("..khf", "......", "fhk..")})
    f.update({13: sim("....kvtt"), 14: sim("...ktvtt"), 15: sim("..kTtvyv"), 16: sim("..kTtvvv"),
              17: fila("..ksk", "vvvvvv", "ksk..")})
    e.update({1: sim(".....kkk"), 2: sim("...kaaaa"), 3: sim("..kaaaaa"), 4: sim("..kaaAAA"),
              5: sim("..kAAAAA"), 6: fila("..khhh", "AAAA", "hhhk.."), 7: sim("..khhhhh"), 8: sim("..khhhhk"),
              9: sim("..khhhkh"),
              10: sim("..kHhhkh"), 11: sim("...khhkh"), 12: sim("....kkkk"),
              13: sim("....kyyy"), 14: sim("...kyyyy"), 15: sim("..ktyYYY"), 16: sim("..ktyyyy"),
              17: sim("..ksyyyy"), 18: sim("...kkkkk")})
    l.update({1: fila(".....", "kkkk", "......."), 2: fila("...", "k", "aaaaaa", "k", "....."),
              3: fila("..", "k", "aaaaaaaaa", "k", "..."), 4: fila("kk", "AAA", "aaaaaaa", "k", "..."),
              5: fila("kAAA", "AAAAAAAA", "k", "..."), 6: fila(".", "k", "khhhhhhh", "s", "h", "k", "..."),
              7: fila(".", "kh", "khhh", "......", "k", ".."), 8: fila(".", "kh", "khhh", "........."),
              9: fila("..", "kh", "hh", "....", "f", "...", ".."), 10: fila("..", "kk", "h", "..........."),
              })
    l.update({13: fila(".", "kkk", ".", "k", "vttv", "k", "....."), 14: fila(".", "kyyk", "vttttt", "k", "...."),
              15: fila(".", "kyYk", "vvTTvv", "k", "...."), 16: fila(".", "kyyk", "vvTTvv", "k", "...."),
              17: fila(".", "kyyk", "vvssvv", "k", "...."), 18: fila(".", "kkkk", "...........")})
    return f, e, l


def _capas_dani():
    f, e, l = {}, {}, {}
    # peinado con raya + traje azul + corbata roja + escarapela dorada
    f.update({2: sim("....kkkk"), 3: sim("...khhhh"), 4: fila("..k", "hhhjhhhhhh", "k.."),
              5: fila("..k", "hhhjhhhhhh", "k.."), 6: fila("..khh", "hh", "sssss", "hk.."),
              7: sim("..kh...."), 10: fila("..ksss", "mwwm", "sssk..")})
    f.update({13: sim("....ktww"), 14: sim("...kttwR"), 15: fila("..ktT", "t", "tRRt", "t", "Ttk.."),
              16: fila("..ktT", "t", "tRRt", "t", "Ttk.."), 17: fila("..ksk", "ttRRtt", "ksk..")})
    f[14] = fila("...k", "ottw", "wttt", "k...")
    e.update({2: sim("....kkkk"), 3: sim("...khhhh"), 4: sim("..khhhhh"), 5: fila("..khhhhj", "hhhhhk.."),
              6: sim("..khhhhh"), 7: sim("..khhhhh"), 8: sim("..kHhhhh"), 9: sim("..ksHHHH"),
              13: sim("....kttt"), 14: sim("...ktttt"), 15: sim("..ktTTtt")})
    l.update({2: fila("....", "kkkkkkkk", "...."), 3: fila("...", "k", "hhhhhhhh", "k", "..."),
              4: fila("..", "k", "hhhhhhhjhh", "k", ".."), 5: fila("..", "k", "hhhhhhjhhh", "k", ".."),
              6: fila("..", "k", "hhhhh", "sssss", "k", ".."), 7: fila("..", "k", "hhh", ".......", "k", ".."),
              8: fila("..", "k", "hh", "........", "..", "."), 10: fila("..", "k", "ssssssss", "w", "m", "k", ".."),
              13: fila(".....", "k", "ttw", "w", "k", "....."), 14: fila("....", "k", "ttt", "tRR", "k", "...."),
              15: fila("....", "k", "o", "tTTtt", "k", "....")})
    return f, e, l


# Cada personaje: colores base por letra y sus capas.
PERSONAJES = {
    "ana": {
        "nombre": "ANA", "rol": "Periodista", "color": (255, 190, 40),
        "piel": 2, "pelo": 0,
        "colores": {"t": (252, 196, 52), "T": (214, 148, 30), "p": (56, 62, 102), "o": (120, 70, 44),
                    "a": (226, 58, 64), "A": (150, 30, 44), "c": (40, 40, 52), "l": (150, 200, 230)},
        "capas": _capas_ana,
    },
    "beto": {
        "nombre": "BETO", "rol": "Influencer", "color": (255, 92, 176),
        "piel": 3, "pelo": 4,
        "colores": {"t": (255, 118, 186), "T": (214, 72, 150), "p": (226, 226, 240), "o": (250, 250, 255),
                    "q": (24, 22, 36), "w": (255, 255, 255), "f": (36, 36, 56), "F": (90, 230, 255)},
        "capas": _capas_beto,
    },
    "caro": {
        "nombre": "CARO", "rol": "Ciudadana", "color": (70, 205, 100),
        "piel": 0, "pelo": 2,
        "colores": {"t": (245, 245, 245), "T": (205, 205, 215), "p": (58, 168, 92), "o": (232, 62, 62),
                    "a": (64, 190, 96), "A": (36, 130, 66), "v": (58, 168, 92), "y": (232, 176, 70),
                    "Y": (186, 126, 40), "f": (196, 110, 70)},
        "capas": _capas_caro,
    },
    "dani": {
        "nombre": "DANI", "rol": "Candidato", "color": (70, 140, 255),
        "piel": 1, "pelo": 1,
        "colores": {"t": (56, 104, 224), "T": (36, 72, 170), "p": (36, 46, 90), "o": (30, 30, 40),
                    "w": (250, 250, 255), "R": (228, 52, 60), "o2": (255, 210, 60)},
        "capas": _capas_dani,
    },
}
ORDEN = ["ana", "beto", "caro", "dani"]


def _oscuro(c, f=0.78):
    return tuple(int(v * f) for v in c)


def _claro(c, f=0.35):
    return tuple(int(v + (255 - v) * f) for v in c)


def _paleta(clave, piel=None, pelo=None):
    p = PERSONAJES[clave]
    piel = PIELES[p["piel"] if piel is None else piel]
    pelo = PELOS[p["pelo"] if pelo is None else pelo]
    pal = {"k": CONTORNO, "s": piel, "z": _oscuro(piel), "e": (34, 26, 44), "r": (240, 120, 120),
           "m": (150, 60, 70), "h": pelo, "H": _oscuro(pelo, 0.7), "j": _claro(pelo, 0.4)}
    if piel in PIELES[3:]:
        pal["r"] = _oscuro(piel, 0.85)
        pal["m"] = (70, 30, 34)
    pal.update(p["colores"])
    if clave == "dani":
        pal["o"] = (255, 210, 60)  # escarapela dorada en la solapa
        pal["p"] = (36, 46, 90)
    return pal


def _combinar(base, capas):
    g = [list(r) for r in base]
    for y, texto in capas.items():
        for x, ch in enumerate(texto):
            if ch == ".":
                continue
            g[y][x] = "." if ch == "_" else ch
    return g


def _levantar_pierna(g, x0, x1):
    """La pierna entre las columnas x0..x1 sube un pixel (paso de caminar visto de frente)."""
    for x in range(x0, x1 + 1):
        for y in range(20, 23):
            g[y][x] = g[y + 1][x]
        g[23][x] = "."


def _abrir_piernas(g):
    """Vista de lado: la pierna de adelante va a la derecha y la de atrás a la izquierda."""
    for y in range(20, 24):
        filao = g[y][:]
        for x in range(16):
            g[y][x] = "."
        for x in range(16):
            ch = filao[x]
            if ch == ".":
                continue
            nx = x + 1 if x >= 8 else x - 1
            if 0 <= nx < 16 and g[y][nx] == ".":
                g[y][nx] = ch


def _a_superficie(g, pal):
    s = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    for y, f in enumerate(g):
        for x, ch in enumerate(f):
            if ch != "." and ch in pal:
                s.set_at((x, y), pal[ch])
    return s


_cache = {}


def cuadros(clave, piel=None, pelo=None):
    """Diccionario dir -> lista de 4 cuadros (quieto, paso A, quieto, paso B). dir: abajo, arriba, der, izq."""
    llave = (clave, piel, pelo)
    if llave in _cache:
        return _cache[llave]
    pal = _paleta(clave, piel, pelo)
    cf, ce, cl = PERSONAJES[clave]["capas"]()
    res = {}
    for nombre, base, capa in (("abajo", BASE["frente"], cf), ("arriba", BASE["espalda"], ce), ("der", BASE["lado"], cl)):
        g = _combinar(base, capa)
        quieto = _a_superficie(g, pal)
        if nombre == "der":
            a = [r[:] for r in g]
            _abrir_piernas(a)
            pa = _a_superficie(a, pal)
            pb = pa
        else:
            a = [r[:] for r in g]
            _levantar_pierna(a, 3, 7)
            b = [r[:] for r in g]
            _levantar_pierna(b, 8, 12)
            pa, pb = _a_superficie(a, pal), _a_superficie(b, pal)
        res[nombre] = [quieto, pa, quieto, pb]
    res["izq"] = [pygame.transform.flip(c, True, False) for c in res["der"]]
    _cache[llave] = res
    return res


def retrato(clave, piel=None, pelo=None):
    """La cabeza de frente (para el HUD y las tarjetas)."""
    img = cuadros(clave, piel, pelo)["abajo"][0]
    return img.subsurface((0, 0, 16, 14)).copy()

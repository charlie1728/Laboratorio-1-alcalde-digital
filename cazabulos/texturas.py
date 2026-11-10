"""Texturas del barrio hechas con numpy al cargar el mapa.

Se calculan una sola vez (menos de un segundo) y quedan pegadas en la imagen del suelo: mientras se
juega no cuestan nada. Todo va en pixeles nativos (16 por tile) y en estilo pixel art: colores de una
paleta corta con tramado (dithering) en vez de degradados suaves, para que combine con los tiles de
Kenney.

- Pasto con manchas de varios verdes, hojitas, tréboles y florecitas.
- Bordes orgánicos (redondeados e irregulares) donde el pasto toca los caminos y la arena, y un
  bordillo de piedra donde toca los andenes, la plaza y la terminal.
- Caminos, plaza, andenes, asfalto y arena con variaciones, grietas, piedritas y musgo en las juntas.
- Laguna con orillas redondeadas, borde de piedras, agua más honda en el centro y espuma en la orilla.
- Sombras suaves (proyectadas hacia abajo a la derecha) y oclusión ambiental debajo de todo.
- Edificios con relieve: techo con degradado y manchas, sombra del alero, grietas y canto con luz.
"""
import numpy as np
import pygame

from .config import TILE

CODIGOS = {"g": 0, "a": 1, "p": 2, "b": 3, "s": 4, "r": 5, "e": 6, "w": 7}
G, A, P, B, S, R, E, AGUA = range(8)
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) / 16 - 0.47

PASTO = np.array([(38, 114, 72), (50, 136, 86), (64, 156, 98), (82, 174, 106), (106, 194, 114)], np.float32)
FLORCITAS = np.array([(252, 252, 242), (255, 224, 88), (255, 168, 204), (198, 168, 255)], np.float32)
AGUA_COL = np.array([(136, 222, 232), (106, 204, 226), (84, 180, 216), (66, 156, 204)], np.float32)
PIEDRAS = np.array([(116, 114, 124), (148, 146, 156), (176, 174, 184), (204, 202, 210)], np.float32)


# ----------------------------------------------------------------- herramientas
def ruido(h, w, escala, rng):
    """Ruido suave (value noise) entre 0 y 1, con manchas de unos 'escala' pixeles."""
    gh, gw = h // escala + 2, w // escala + 2
    g = rng.random((gh, gw)).astype(np.float32)
    ys = np.arange(h, dtype=np.float32) / escala
    xs = np.arange(w, dtype=np.float32) / escala
    y0, x0 = ys.astype(np.int32), xs.astype(np.int32)
    fy, fx = ys - y0, xs - x0
    fy = (fy * fy * (3 - 2 * fy))[:, None]
    fx = (fx * fx * (3 - 2 * fx))[None, :]
    yy, xx = y0[:, None], x0[None, :]
    a, b = g[yy, xx], g[yy, xx + 1]
    c, d = g[yy + 1, xx], g[yy + 1, xx + 1]
    arriba = a + (b - a) * fx
    abajo = c + (d - c) * fx
    return arriba + (abajo - arriba) * fy


def _caja(a, r, eje):
    pad = [(0, 0)] * a.ndim
    pad[eje] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode="edge"), axis=eje, dtype=np.float32)
    n = a.shape[eje]
    alto = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=eje)
    bajo = np.take(c, np.arange(0, n), axis=eje)
    return (alto - bajo) / (2 * r + 1)


def difuminar(a, r, veces=2):
    """Desenfoque de caja (dos pasadas ya parecen un desenfoque gaussiano)."""
    a = a.astype(np.float32)
    for _ in range(veces):
        a = _caja(_caja(a, r, 0), r, 1)
    return a


def crecer(m, n=1):
    """Agranda una máscara n pixeles (vecinos en cruz)."""
    m = m.copy()
    for _ in range(n):
        g = m.copy()
        g[1:] |= m[:-1]
        g[:-1] |= m[1:]
        g[:, 1:] |= m[:, :-1]
        g[:, :-1] |= m[:, 1:]
        m = g
    return m


def encoger(m, n=1):
    return ~crecer(~m, n)


def correr(m, dx, dy):
    """La máscara corrida dx, dy pixeles (lo que sale por un lado no entra por el otro)."""
    out = np.zeros_like(m)
    h, w = m.shape
    out[max(0, dy):h + min(0, dy), max(0, dx):w + min(0, dx)] = m[max(0, -dy):h - max(0, dy), max(0, -dx):w - max(0, dx)]
    return out


def tramado(h, w):
    return np.tile(BAYER, (h // 4 + 1, w // 4 + 1))[:h, :w]


def por_pixel(tiles):
    return np.repeat(np.repeat(tiles, TILE, 0), TILE, 1)


def _vista(s):
    """Los pixeles de la superficie como arreglo (alto, ancho, 3) que escribe directo en ella."""
    return pygame.surfarray.pixels3d(s).swapaxes(0, 1)


def _alfa(s):
    return pygame.surfarray.array_alpha(s).swapaxes(0, 1)


def grietas(img, permitido, rng, n, largo=(4, 9)):
    """Grietas finas: una línea oscura que serpentea con un pixel claro debajo (parece hundida)."""
    ys, xs = np.nonzero(permitido)
    if not len(ys) or n <= 0:
        return
    h, w = permitido.shape
    direcciones = ((1, 0), (0, 1), (1, 1), (1, -1))
    for i in rng.integers(0, len(ys), n):
        y, x = int(ys[i]), int(xs[i])
        dx, dy = direcciones[int(rng.integers(4))]
        for _ in range(int(rng.integers(*largo))):
            if not (0 <= y < h - 1 and 0 <= x < w) or not permitido[y, x]:
                break
            img[y, x] *= 0.66
            if permitido[y + 1, x]:
                img[y + 1, x] = np.minimum(img[y + 1, x] * 1.12, 255)
            if rng.random() < 0.45:            # que no sea una raya recta
                if dx:
                    y += int(rng.integers(-1, 2))
                else:
                    x += int(rng.integers(-1, 2))
            x += dx
            y += dy


def piedritas(img, permitido, rng, densidad):
    ys, xs = np.nonzero(permitido[1:, 1:])
    if not len(ys):
        return
    elegidas = rng.random(len(ys)) < densidad
    ys, xs = ys[elegidas] + 1, xs[elegidas] + 1
    img[ys, xs] *= 0.72
    img[ys - 1, xs - 1] = np.minimum(img[ys - 1, xs - 1] * 1.18, 255)


# ----------------------------------------------------------------- pasto
def textura_pasto(h, w, rng):
    """Pasto pixel art: manchas grandes de varios verdes con tramado, matitas tipo Pokémon, tréboles y florecitas."""
    v = 0.5 * ruido(h, w, 20, rng) + 0.32 * ruido(h, w, 7, rng) + 0.18 * ruido(h, w, 3, rng)
    v = (v - v.min()) / (v.max() - v.min() + 1e-6)
    idx = np.digitize(v + tramado(h, w) * 0.17, [0.14, 0.36, 0.64, 0.85])
    img = PASTO[idx]
    # matitas en forma de "v" y "w": puntas claras y base con sombra para dar relieve 2D
    n = int(h * w * 0.011)
    ys, xs = rng.integers(1, h - 3, n), rng.integers(1, w - 3, n)
    claro = PASTO[np.minimum(idx[ys, xs] + 1, 4)]
    sombra = PASTO[np.maximum(idx[ys, xs] - 1, 0)]
    img[ys, xs] = claro
    img[ys, xs + 2] = claro
    img[ys + 1, xs + 1] = claro
    for dx in range(3):
        img[ys + 2, xs + dx] = sombra
    # hojitas dobles: rayita de 2 pixeles (punta clara, base oscura)
    n = int(h * w * 0.048)
    ys, xs = rng.integers(0, h - 1, n), rng.integers(0, w, n)
    img[ys, xs] = PASTO[np.minimum(idx[ys, xs] + 1, 4)]
    img[ys + 1, xs] = PASTO[np.maximum(idx[ys + 1, xs] - 1, 0)]
    # tréboles: grupitos de hojas redondeadas con centro luminoso
    n = int(h * w * 0.0045)
    ys, xs = rng.integers(1, h - 2, n), rng.integers(1, w - 2, n)
    for dy, dx in ((0, 0), (0, 1), (1, 0), (1, 1)):
        img[ys + dy, xs + dx] = PASTO[1]
    img[ys, xs] = PASTO[4]
    img[ys + 1, xs + 1] = PASTO[3]
    # florecitas silvestres (pétalos + centro + tallito)
    n = int(h * w * 0.0018)
    ys, xs = rng.integers(1, h - 2, n), rng.integers(1, w - 2, n)
    col_flor = FLORCITAS[rng.integers(0, len(FLORCITAS), n)]
    img[ys, xs] = col_flor
    img[ys, xs + 1] = col_flor
    img[ys + 1, xs] = PASTO[0]
    img[ys + 1, xs + 1] = PASTO[3]
    return img


# ----------------------------------------------------------------- el suelo completo
def suelo(mapa, s, debajo, debajo_cod, semilla=7):
    """Rehace el suelo de 's' (ya con los tiles de Kenney pegados). 'debajo' tiene, en los tiles de
    pasto que tocan un camino o la arena, el suelo de ese vecino (se ve donde el borde se redondea).
    Devuelve la información de la laguna para las animaciones."""
    rng = np.random.default_rng(semilla)
    vista = _vista(s)
    img = vista.astype(np.float32)
    h, w = img.shape[:2]
    cod = np.array([[CODIGOS[c] for c in fila] for fila in mapa.suelo], np.uint8)
    M = por_pixel(cod)
    pasto_t = np.isin(M, (G, AGUA))              # debajo de la laguna también hay pasto
    blando = np.isin(M, (B, S))
    # 1) pasto con bordes orgánicos: se redondea e irregulariza solo hacia los caminos y la arena
    n = (ruido(h, w, 4, rng) - 0.5) * 0.34 + (rng.random((h, w)).astype(np.float32) - 0.5) * 0.1
    hacia_blando = por_pixel(np.isin(cod, (G, A, P, E, R, AGUA)).astype(np.float32))
    m1 = difuminar(hacia_blando, 3) + n
    m2 = difuminar(pasto_t.astype(np.float32), 3) + n
    pasto = (pasto_t & (m1 > 0.5)) | (blando & (m2 > 0.5))
    # donde el pasto se retira se ve el suelo del vecino
    deb = pygame.surfarray.array3d(debajo).swapaxes(0, 1).astype(np.float32)
    deb_cod = por_pixel(np.array([[CODIGOS[c] for c in fila] for fila in debajo_cod], np.uint8))
    retiro = pasto_t & ~pasto
    img[retiro] = deb[retiro]
    Mef = M.copy()
    Mef[retiro] = deb_cod[retiro]
    Mef[pasto] = G
    # 2) cada material con su textura
    _materiales(img, Mef, pasto, rng)
    # 3) el pasto encima, con su orilla
    tex = textura_pasto(h, w, rng)
    img[pasto] = tex[pasto]
    orilla = pasto & ~encoger(pasto)
    img[orilla] *= 0.84
    fuera1 = crecer(pasto) & ~pasto
    fuera2 = crecer(pasto, 2) & ~pasto & ~fuera1
    blando_ef = np.isin(Mef, (B, S))
    img[fuera1 & blando_ef] *= 0.72                      # el pasto le hace sombrita al camino
    img[fuera2 & blando_ef] *= 0.88
    duro_ef = np.isin(Mef, (A, P, E))
    img[fuera1 & duro_ef] = (204, 206, 214)              # bordillo de piedra: arriba claro...
    img[fuera2 & duro_ef] = (124, 126, 138)              # ...y su costado oscuro
    img[crecer(fuera1 & duro_ef) & pasto] *= 0.8         # el pasto pegado al bordillo, a la sombra
    # 4) la laguna
    estanque = _laguna(img, M, rng)
    vista[:] = np.clip(img, 0, 255).astype(np.uint8)
    del vista
    return estanque


def _materiales(img, M, pasto, rng):
    h, w = M.shape
    yy, xx = np.mgrid[0:h, 0:w]
    # caminos del parque: cada piedrita con un tono distinto, grietas y piedras sueltas
    b = M == B
    if b.any():
        f = (0.9 + 0.17 * ruido(h, w, 5, rng))[b]
        img[b] *= f[:, None]
        grietas(img, b, rng, int(b.sum() // 3500), (3, 6))
        piedritas(img, b, rng, 0.0025)
    # arena: olitas que dejó el viento y piedritas
    s = M == S
    if s.any():
        ola = 1 + 0.04 * np.sin(xx * 0.45 + yy * 0.8 + ruido(h, w, 9, rng) * 7)
        img[s] *= ola[s][:, None]
        piedritas(img, s, rng, 0.004)
    # plaza, andenes y terminal: cada losa con su tono, grietas y musgo en las juntas
    pa = np.isin(M, (P, A))
    if pa.any():
        H, W = h // TILE, w // TILE
        losas = por_pixel(rng.uniform(0.93, 1.06, (H, W)).astype(np.float32))
        img[pa] *= losas[pa][:, None]
        lum = img.mean(axis=2)
        media = por_pixel(lum.reshape(H, TILE, W, TILE).mean(axis=(1, 3)))
        junta = pa & (lum < media * 0.86)
        cerca = crecer(pasto, 8)
        musgo = junta & (rng.random((h, w)) < np.where(cerca, 0.35, 0.03))
        img[musgo] = np.where(rng.random((int(musgo.sum()), 1)) < 0.5, (74, 128, 72), (92, 148, 80))
        grietas(img, pa, rng, int(pa.sum() // 7000), (3, 7))
    # asfalto: grano, parches más oscuros, manchas de aceite y grietas
    ra = np.isin(M, (R, E))
    if ra.any():
        grano = rng.normal(0, 4.5, (h, w)).astype(np.float32)
        img[ra] += grano[ra][:, None]
        parche = ra & (ruido(h, w, 14, rng) > 0.7)
        img[parche] *= 0.9
        aceite = ra & (ruido(h, w, 6, rng) > 0.8)
        img[aceite] *= 0.86
        grietas(img, ra, rng, int(ra.sum() // 2600), (5, 11))


def _laguna(img, M, rng):
    """Laguna de orillas redondeadas: piedras alrededor, agua más clara en la orilla y más honda en
    el centro, espuma en el borde y sombra de las piedras sobre el agua."""
    agua_t = M == AGUA
    ys, xs = np.nonzero(agua_t)
    if not len(ys):
        return None
    h, w = M.shape
    m = 14
    y0, y1 = max(0, ys.min() - m), min(h, ys.max() + 1 + m)
    x0, x1 = max(0, xs.min() - m), min(w, xs.max() + 1 + m)
    sub = agua_t[y0:y1, x0:x1].astype(np.float32)
    hh, ww = sub.shape
    forma = (difuminar(sub, 8) + (ruido(hh, ww, 14, rng) - 0.5) * 0.28 + (ruido(hh, ww, 5, rng) - 0.5) * 0.1
             + (ruido(hh, ww, 2, rng) - 0.5) * 0.04)
    agua = forma > 0.6
    piedra = (forma > 0.4) & ~agua
    reg = img[y0:y1, x0:x1]
    # piedras de la orilla: cuatro tonos, juntas oscuras, mojadas junto al agua
    t = ruido(hh, ww, 2, rng)
    col = PIEDRAS[np.digitize(t + tramado(hh, ww) * 0.12, [0.32, 0.5, 0.68])]
    col[np.abs(ruido(hh, ww, 3, rng) - 0.5) < 0.05] = (92, 90, 100)
    reg[piedra] = col[piedra]
    reg[piedra & crecer(agua)] *= 0.78
    reg[piedra & ~correr(piedra, 0, 1)] *= 1.12                           # luz arriba de cada piedra
    afuera = crecer(piedra | agua) & ~(piedra | agua)
    reg[afuera] *= 0.55                                                     # borde oscuro de la laguna
    reg[crecer(afuera, 2) & ~(piedra | agua) & ~afuera] *= 0.85
    # agua: más honda en el centro (cuatro azules con tramado)
    hondo = difuminar(agua.astype(np.float32), 7)
    d = np.clip((hondo - 0.5) / 0.5, 0, 1)
    nivel = np.digitize(d + tramado(hh, ww) * 0.12 + (ruido(hh, ww, 9, rng) - 0.5) * 0.12, [0.12, 0.4, 0.72])
    azul = AGUA_COL[nivel]
    # ondulaciones: rayitas un tono más claras
    n = int(hh * ww * 0.006)
    oy, ox = rng.integers(0, hh, n), rng.integers(0, ww - 4, n)
    for k in range(int(rng.integers(2, 5))):
        azul[oy, ox + k] = AGUA_COL[np.maximum(nivel[oy, ox + k] - 1, 0)]
    reg[agua] = azul[agua]
    sombra = agua & (correr(piedra, 0, 1) | correr(piedra, 0, 2) | correr(piedra, 0, 3))
    reg[sombra & ~piedra] *= 0.84                                           # las piedras de arriba dan sombra
    borde = agua & ~encoger(agua)
    reg[borde] = (200, 240, 246)                                            # espuma pegada a la orilla
    reg[agua & ~encoger(agua, 2) & ~borde] = (150, 226, 236)
    return {"x": int(x0), "y": int(y0), "agua": agua, "hondo": d, "piedra": piedra}


# ----------------------------------------------------------------- sombras
def sombras(s, capas, extra):
    """Oscurece el suelo con sombras suaves: cada capa (edificios, objetos) proyecta su silueta
    corrida hacia abajo a la derecha y además oscurece un poco alrededor de su base (oclusión
    ambiental). 'extra' es una superficie con manchas de sombra ya dibujadas (postes, buses...)."""
    vista = _vista(s)
    h, w = vista.shape[:2]
    oscuro = np.zeros((h, w), np.float32)
    for capa, corrida, fuerza, radio, fuerza_ao, radio_ao in capas:
        m = _alfa(capa) > 40
        dx, dy = corrida
        oscuro += fuerza * difuminar(correr(m, dx, dy).astype(np.float32), radio)
        oscuro += fuerza_ao * difuminar(m.astype(np.float32), radio_ao)
    oscuro += difuminar(_alfa(extra).astype(np.float32) / 255, 1)
    factor = 1 - np.clip(oscuro, 0, 0.62)
    vista[:] = (vista * factor[..., None]).astype(np.uint8)
    del vista


# ----------------------------------------------------------------- edificios
def relieve_edificios(capa, edificios, semilla=11):
    """Techos con degradado y manchas, la sombra del alero sobre la fachada, la base más oscura,
    grietas en las paredes y el canto izquierdo con luz."""
    rng = np.random.default_rng(semilla)
    vista = _vista(capa)
    img = vista.astype(np.float32)
    opaco = _alfa(capa) > 0
    for x, y, w, h, *_ in edificios:
        X0, Y0, X1, Y1 = x * TILE, y * TILE, (x + w) * TILE, (y + h) * TILE
        reg = img[Y0:Y1, X0:X1]
        op = opaco[Y0:Y1, X0:X1]
        alto_techo = (h - 3) * TILE
        ancho = X1 - X0
        if alto_techo > 0:
            techo = reg[:alto_techo]
            techo *= np.linspace(1.08, 0.9, alto_techo, dtype=np.float32)[:, None, None]
            manchas = ruido(alto_techo, ancho, 5, rng) > 0.7
            techo[manchas] *= 0.93
            techo *= (1 + (rng.random((alto_techo, ancho, 1)) - 0.5) * 0.05).astype(np.float32)
        for k, f in enumerate((0.64, 0.76, 0.88)):                     # alero
            if alto_techo + k < reg.shape[0]:
                reg[alto_techo + k] *= f
        for k, f in enumerate((0.92, 0.84, 0.76)):                     # base de la pared
            reg[-3 + k] *= f
        reg[:, :1] *= 1.12
        reg[:, -2:] *= 0.86
        pared = np.zeros_like(op)
        pared[alto_techo + 3:-4, 2:-2] = True
        grietas(reg, pared & op, rng, max(1, w // 3), (4, 8))
    vista[:] = np.clip(img, 0, 255).astype(np.uint8)
    del vista

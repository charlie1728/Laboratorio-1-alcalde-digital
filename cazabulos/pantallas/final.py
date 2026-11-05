"""Resultado de cada turno, tabla de la ronda, elección del alcalde y podio final."""
import math
import random

import pygame

from .. import personajes, sprites
from ..config import ALTO, ANCHO, TINTA
from ..hud import INDICADORES
from ..partida import CANDIDATOS, MOMENTOS, calcular_eleccion
from ..personajes import PERSONAJES
from ..recursos import escalar
from ..ui import barra, panel, parrafo, render, tecla, texto
from .base import Escena, FondoCiudad, es_aceptar, pie, titulo_pantalla


class Confeti:
    def __init__(self, n=140, colores=None):
        r = random.Random(5)
        colores = colores or [(255, 205, 50), (255, 96, 170), (70, 205, 100), (70, 140, 255), (255, 255, 255)]
        self.p = [[r.uniform(0, ANCHO), r.uniform(-ALTO, 0), r.uniform(-30, 30), r.uniform(80, 200),
                   r.choice(colores), r.uniform(0, 6)] for _ in range(n)]

    def dibujar(self, pant, dt):
        for c in self.p:
            c[0] += c[2] * dt
            c[1] += c[3] * dt
            c[5] += dt * 6
            if c[1] > ALTO + 10:
                c[1] = -10
            w = abs(math.sin(c[5])) * 10 + 2
            pygame.draw.rect(pant, c[4], (c[0], c[1], w, 8))


def dibujar_arbol(pant, filas, rect, t=0.0):
    """Dibuja el árbol de decisiones (lista en preorden) con las veces que pasó el jugador por cada nodo."""
    nodos = {c: {"texto": tx, "veces": v, "padre": p, "hoja": h, "hijos": []} for c, tx, v, p, h in filas}
    raiz = None
    for c, tx, v, p, h in filas:
        if p is None:
            raiz = c
        else:
            nodos[p]["hijos"].append(c)
    # posiciones: hojas repartidas a lo ancho, padres centrados sobre sus hijos
    hojas = [c for c, *_ in filas if nodos[c]["hoja"]]
    paso_x = rect.w / max(1, len(hojas))
    pos = {}

    def colocar(c, nivel):
        if nodos[c]["hoja"]:
            k = hojas.index(c)
            x = rect.x + paso_x * (k + 0.5)
        else:
            xs = [colocar(h, nivel + 1) for h in nodos[c]["hijos"]]
            x = sum(xs) / len(xs)
        pos[c] = (x, rect.y + 18 + nivel * (rect.h - 62) / 3)
        return x
    colocar(raiz, 0)
    for c, n in nodos.items():
        if n["padre"]:
            a, b = pos[n["padre"]], pos[c]
            usado = n["veces"] > 0
            pygame.draw.line(pant, (255, 205, 50) if usado else (80, 72, 120), a, b, 5 if usado else 2)
    for c, n in nodos.items():
        x, y = pos[c]
        usado = n["veces"] > 0
        bueno = c in ("verdad", "reporte", "suerte")
        malo = c in ("bulo", "perdida")
        color = (120, 220, 140) if (bueno and usado) else (255, 110, 110) if (malo and usado) else (255, 205, 50) if usado else (70, 62, 110)
        r = 15 if n["hoja"] else 12
        pygame.draw.circle(pant, TINTA, (int(x), int(y) + 2), r + 3)
        pygame.draw.circle(pant, color, (int(x), int(y)), r)
        if n["veces"]:
            texto(pant, str(n["veces"]), (x, y), 15, TINTA, "center", borde=None)
        etiqueta = CORTOS.get(c, n["texto"])
        lineas = [etiqueta] if len(etiqueta) < 11 else _partir(etiqueta)
        for k, ln in enumerate(lineas):
            texto(pant, ln, (x, y + r + 3 + k * 15), 13, (240, 240, 250) if usado else (150, 144, 180), "midtop", 600)


CORTOS = {"noticia": "Una noticia", "mirar": "La miras", "sin_mirar": "Sin mirar", "ignorar": "La dejas",
          "real": "Es real", "reporte": "Bulo descubierto", "verdad": "Compartes verdad", "perdida": "Se te pasó",
          "suerte": "Era real", "bulo": "Compartes Bulo"}


def _partir(s):
    palabras = s.split()
    mitad = len(palabras) // 2
    return [" ".join(palabras[:mitad]), " ".join(palabras[mitad:])]


def mensaje(res):
    s = res["salvados"] / max(1, res["vecinos"])
    if res["stats"]["compartidas_falsas"] >= 2:
        return "Ojo: compartiste Bulos sin mirarlos. ¡Detente un segundo antes de compartir!"
    if s >= 0.8:
        return "¡Increíble! El barrio confía en ti."
    if s >= 0.55:
        return "¡Muy bien! Salvaste a la mayoría de los vecinos."
    if s >= 0.3:
        return "¡Bien! Busca la raíz de las cadenas (el Bulo con corona) para tumbar muchos de una vez."
    return "Los Bulos ganaron esta vez. Apaga la antena pronto y lánzales a las cabezas de los vecinos."


class ResultadoTurno(Escena):
    def __init__(self, app, partida, indice, res, red=None):
        super().__init__(app)
        self.partida, self.indice, self.res, self.red = partida, indice, res, red
        self.fondo = FondoCiudad(app, 175)
        self.confeti = Confeti(90) if res["reputacion"] >= 2 else None
        self.sonado = 0
        app.son.tocar("victoria" if res["reputacion"] >= 2 else "fin")

    def evento(self, e):
        if (es_aceptar(e) or (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1)) and self.t > 0.8:
            self.app.son.tocar("click")
            self._seguir()

    def _seguir(self):
        if self.red:
            from .en_linea import EsperaRed
            self.app.cambiar(EsperaRed(self.app, self.partida, self.red))
            return
        pa = self.partida
        paso = pa.avanzar()
        if paso == "turno":
            from .seleccion import Relevo
            self.app.cambiar(Relevo(self.app, pa))
        else:
            self.app.cambiar(TablaRonda(self.app, pa, final=paso == "fin"))

    def dibujar(self, pant):
        self.fondo.dibujar(pant, 1 / 60)
        if self.confeti:
            self.confeti.dibujar(pant, 1 / 60)
        res = self.res
        j = self.partida.jugadores[self.indice]
        p = PERSONAJES[j["clave"]]
        titulo_pantalla(pant, f"¡Bien jugado, {j['nombre']}!" if res["reputacion"] >= 2 else f"Turno de {j['nombre']}", 18, p["color"], 46)
        # personaje y estrellas de reputación
        cs = personajes.cuadros(j["clave"], j["piel"], j["pelo"])
        salta = res["reputacion"] >= 2
        cuadro = int(self.t * 6) % 4 if salta else 0
        img = pygame.transform.scale(cs["abajo"][cuadro], (16 * 9, 24 * 9))
        dy = -abs(math.sin(self.t * 5)) * 18 if salta else 0
        pygame.draw.ellipse(pant, (0, 0, 0), (140, 470, 150, 26))
        pant.blit(img, img.get_rect(midbottom=(215, 486 + dy)))
        for k in range(3):
            aparece = self.t > 0.4 + k * 0.35
            if aparece and k < res["reputacion"] and self.sonado <= k:
                self.sonado = k + 1
                self.app.son.tocar("recoger")
            on = aparece and k < res["reputacion"]
            esc = 6 if on else 5
            img_s = escalar(sprites.estrella(revelada_falsa=False) if on else sprites.desaturar(sprites.estrella()), esc)
            pant.blit(img_s, img_s.get_rect(center=(140 + k * 75, 150 + (0 if k == 1 else 16))))
        parrafo(pant, mensaje(res), (215, 520), 19, 360, (255, 255, 255), ancla="midtop")
        # números
        r = panel(pant, (420, 96, 400, 420), borde=p["color"])
        s = res["stats"]
        filas = [("Bulos atrapados", s["bulos"]), ("Vecinos curados", s["curados"]), ("Antenas apagadas", s["antenas"]),
                 ("Noticias reales entregadas", s["entregadas"]), ("Bulos disfrazados descubiertos", s["reportadas"]),
                 ("Bulos compartidos sin mirar", s["compartidas_falsas"]), ("Peleas calmadas", s["peleas"]),
                 ("Viral detenido", "sí" if s["viral"] else "no"), ("Cadena más larga", s["cadena"])]
        for k, (nombre, v) in enumerate(filas):
            y = r.y + 18 + k * 30
            texto(pant, nombre, (r.x + 20, y), 18, (230, 226, 245), peso=600)
            mala = nombre.startswith("Bulos compartidos") and v
            texto(pant, str(v), (r.right - 20, y), 20, (255, 120, 120) if mala else (255, 255, 255), "topright")
        y = r.y + 300
        pygame.draw.line(pant, (90, 80, 140), (r.x + 16, y), (r.right - 16, y), 2)
        cuenta = min(1.0, self.t / 1.5)
        texto(pant, "Puntos", (r.x + 20, y + 10), 20, (230, 226, 245), peso=600)
        texto(pant, str(int(res["puntos"] * cuenta)), (r.right - 20, y + 10), 22, (255, 255, 255), "topright")
        texto(pant, f"{res['salvados']} vecinos a salvo x 10", (r.x + 20, y + 40), 20, (140, 240, 160), peso=600)
        texto(pant, f"+{int(res['bono'] * cuenta)}", (r.right - 20, y + 40), 22, (140, 240, 160), "topright")
        texto(pant, "TOTAL", (r.x + 20, y + 74), 28, p["color"])
        texto(pant, str(int(res["total"] * cuenta)), (r.right - 20, y + 70), 34, (255, 230, 120), "topright")
        # árbol de decisiones
        ra = panel(pant, (840, 96, 420, 300), borde=(255, 205, 50, 120))
        texto(pant, "Tu árbol de decisiones con las noticias", (ra.centerx, ra.y + 10), 17, (255, 230, 150), "midtop")
        dibujar_arbol(pant, res["arbol"], pygame.Rect(ra.x + 10, ra.y + 38, ra.w - 20, ra.h - 50), self.t)
        # logros
        rl = panel(pant, (840, 410, 420, 106))
        nuevos = [l for l in res.get("logros", []) if l[3]]
        texto(pant, "Logros nuevos" if nuevos else "Logros de este turno", (rl.x + 16, rl.y + 8), 17, (255, 230, 150))
        lista = nuevos or res.get("logros", [])
        if not lista:
            texto(pant, "Ninguno esta vez. ¡Mira la Ayuda para ver cómo ganarlos!", (rl.x + 16, rl.y + 40), 16, (220, 214, 240), peso=600)
        for k, (clave, nombre, desc, nuevo) in enumerate(lista[:4]):
            x = rl.x + 16 + (k % 2) * 200
            y = rl.y + 36 + (k // 2) * 32
            pygame.draw.circle(pant, (255, 205, 50) if nuevo else (140, 130, 190), (x + 10, y + 10), 10)
            texto(pant, nombre, (x + 26, y), 17, (255, 255, 255), peso=600)
        if res.get("puesto") and res["puesto"] <= 10:
            texto(pant, f"¡Entraste al puesto {res['puesto']} de los récords!", (ANCHO // 2 + 200, 540), 22, (255, 230, 120), "midtop")
        sube = math.sin(self.t * 4) * 3
        texto(pant, "Pulsa ESPACIO para seguir", (ANCHO // 2, ALTO - 40 + sube), 26, (255, 255, 255), "center")


class TablaRonda(Escena):
    def __init__(self, app, partida, final=False):
        super().__init__(app)
        self.partida, self.final = partida, final
        self.fondo = FondoCiudad(app, 175)
        app.son.tocar("fanfarria")

    def evento(self, e):
        if (es_aceptar(e) or (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1)) and self.t > 0.8:
            self.app.son.tocar("click")
            if self.final:
                self.app.cambiar(Eleccion(self.app, self.partida))
            else:
                from .seleccion import Relevo
                self.partida.siguiente_ronda()
                self.app.cambiar(Relevo(self.app, self.partida))

    def dibujar(self, pant):
        self.fondo.dibujar(pant, 1 / 60)
        pa = self.partida
        titulo_pantalla(pant, f"Así va la partida · Ronda {pa.ronda} de {pa.rondas}", 30, tam=44)
        orden = pa.ranking()
        maximo = max(1, max(pa.total(i) for i in orden))
        crece = min(1.0, self.t / 1.2)
        for k, i in enumerate(orden):
            j = pa.jugadores[i]
            p = PERSONAJES[j["clave"]]
            y = 150 + k * 120
            r = panel(pant, (120, y, ANCHO - 240, 100), borde=p["color"] if k == 0 else None)
            texto(pant, f"{k + 1}°", (r.x + 24, r.centery), 40, (255, 205, 50) if k == 0 else (255, 255, 255), "midleft")
            img = escalar(personajes.retrato(j["clave"], j["piel"], j["pelo"]), 5)
            pant.blit(img, img.get_rect(midleft=(r.x + 90, r.centery)))
            texto(pant, j["nombre"], (r.x + 190, r.y + 16), 30, p["color"])
            texto(pant, f"{pa.salvados(i)} vecinos salvados en total", (r.x + 190, r.y + 56), 18, (220, 214, 240), peso=600)
            barra(pant, (r.x + 520, r.y + 34, 400 * crece * pa.total(i) / maximo + 1, 30), 1, p["color"])
            texto(pant, str(int(pa.total(i) * crece)), (r.right - 24, r.centery), 34, (255, 255, 255), "midright")
        siguiente = "¡Ahora, la elección del alcalde!" if self.final else f"Siguiente ronda: {MOMENTOS.get(pa.ronda + 1, '')}"
        sube = math.sin(self.t * 4) * 3
        texto(pant, f"{siguiente}  ·  ESPACIO para seguir", (ANCHO // 2, ALTO - 44 + sube), 26, (255, 255, 255), "center")


def _figura_candidato(c):
    if c == "Emilio":
        return escalar(sprites.bulo(0, True, False, (0, 1)), 6)
    if c == "Dani":
        return escalar(personajes.cuadros("dani")["abajo"][0], 4)
    tipo = {"Lucia": 1, "Marcos": 3, "Elena": 0}[c]
    return escalar(sprites.vecino(tipo, {"Lucia": 1, "Marcos": 2, "Elena": 2}[c], "abajo", 0), 6)


class Eleccion(Escena):
    """Ciudad Nova vota. El resultado sale de cómo quedó el barrio en todos los turnos."""

    def __init__(self, app, partida):
        super().__init__(app)
        self.partida = partida
        self.fondo = FondoCiudad(app, 180)
        self.orden, self.datos = calcular_eleccion(partida.resultados, partida.jugadores)
        self.ganador = self.orden[0] if self.orden else "Lucia"
        self.anunciado = False
        self.confeti = None
        app.son.tocar("cuenta")

    def evento(self, e):
        if (es_aceptar(e) or (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1)) and self.t > 1.0:
            if not self.anunciado:
                self.t = max(self.t, 4.6)
                return
            self.app.son.tocar("click")
            self.app.cambiar(Podio(self.app, self.partida, self.ganador))

    def actualizar(self, dt):
        super().actualizar(dt)
        if self.t > 4.6 and not self.anunciado:
            self.anunciado = True
            if self.ganador == "Emilio":
                self.app.son.tocar("viral_mal")
            else:
                self.app.son.tocar("fanfarria")
                self.confeti = Confeti(160)

    def dibujar(self, pant):
        self.fondo.dibujar(pant, 1 / 60)
        if self.confeti:
            self.confeti.dibujar(pant, 1 / 60)
        titulo_pantalla(pant, "Ciudad Nova elige alcalde", 20, tam=48)
        votos = self.datos.get("votos", {})
        cands = [c for c in ("Lucia", "Marcos", "Elena", "Dani", "Emilio") if c in votos]
        total = max(1, sum(votos.values()))
        cuenta = min(1.0, self.t / 4.0)
        ancho = (ANCHO - 160) // len(cands)
        for k, c in enumerate(cands):
            nombre, lema, color = CANDIDATOS[c]
            x = 80 + k * ancho + ancho // 2
            v = int(votos[c] * cuenta)
            alto = int(min(230, 230 * v / max(votos.values()))) if max(votos.values()) else 0
            alto = int(alto * cuenta) if cuenta < 1 else alto
            base_y = 450
            gana = self.anunciado and c == self.ganador
            col = pygame.Rect(x - 50, base_y - alto, 100, alto)
            pygame.draw.rect(pant, tuple(int(cc * 0.6) for cc in color), col.move(0, 6), border_radius=10)
            pygame.draw.rect(pant, color, col, border_radius=10)
            fig = _figura_candidato(c)
            fr = fig.get_rect(midbottom=(x, base_y - alto - 6 - (abs(math.sin(self.t * 6)) * 14 if gana else 0)))
            pant.blit(fig, fr)
            texto(pant, nombre, (x, base_y + 14), 22, color, "midtop")
            parrafo(pant, lema, (x, base_y + 44), 14, ancho - 20, (220, 214, 240), ancla="midtop")
            texto(pant, f"{v} votos", (x, base_y + 88), 20, (255, 255, 255), "midtop")
            if gana:
                texto(pant, "¡GANÓ!", (x, fr.top - 4), 30, (255, 230, 120), "midbottom")
        if self.anunciado:
            prom = self.datos["promedio"]
            r = panel(pant, (ANCHO // 2 - 470, 584, 940, 92), borde=(255, 205, 50))
            if self.ganador == "Emilio":
                s = (f"Ganaron los Bulos: el barrio terminó con {int(prom['desinformacion'])} de desinformación. "
                     "Cuando la gente comparte sin mirar, gana quien más mentiras riega.")
            else:
                s = (f"Ciudad Nova votó informada: {int(prom['informacion'])} de información verificada y "
                     f"{int(prom['confianza'])} de confianza. Lo que hicieron en el barrio decidió la elección.")
            parrafo(pant, s, (r.centerx, r.y + 10), 19, r.w - 40, (255, 255, 255), ancla="midtop")
        else:
            texto(pant, "Contando votos...", (ANCHO // 2, 640), 26, (255, 255, 255), "center")


class Podio(Escena):
    def __init__(self, app, partida, ganador):
        super().__init__(app)
        self.partida = partida
        self.ganador = ganador
        self.fondo = FondoCiudad(app, 170)
        self.confeti = Confeti(180)
        app.son.tocar("victoria")

    def evento(self, e):
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_r,):
            from .seleccion import Preparar
            self.app.cambiar(Preparar(self.app))
        elif (es_aceptar(e) or (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1)) and self.t > 1.0:
            from .menu import Titulo
            if self.app.red:
                self.app.red.cerrar()
                self.app.red = None
            self.app.cambiar(Titulo(self.app))

    def dibujar(self, pant):
        self.fondo.dibujar(pant, 1 / 60)
        self.confeti.dibujar(pant, 1 / 60)
        pa = self.partida
        orden = pa.ranking()
        ganador = pa.jugadores[orden[0]]
        if len(orden) > 1:
            titulo_pantalla(pant, f"¡{ganador['nombre']} gana la partida!", 24, PERSONAJES[ganador["clave"]]["color"], 56)
        else:
            titulo_pantalla(pant, f"¡Partida terminada, {ganador['nombre']}!", 24, PERSONAJES[ganador["clave"]]["color"], 52)
        alturas = [170, 120, 84, 60]
        lugares = [1, 0, 2, 3]
        xs = {0: ANCHO // 2, 1: ANCHO // 2 - 260, 2: ANCHO // 2 + 260, 3: ANCHO // 2 + 470}
        for puesto in lugares:
            if puesto >= len(orden):
                continue
            i = orden[puesto]
            j = pa.jugadores[i]
            p = PERSONAJES[j["clave"]]
            x = xs[puesto]
            h = alturas[puesto]
            base = pygame.Rect(x - 100, 676 - h, 200, h)
            pygame.draw.rect(pant, tuple(int(c * 0.6) for c in p["color"]), base.move(0, 8), border_radius=12)
            pygame.draw.rect(pant, p["color"], base, border_radius=12)
            texto(pant, f"{puesto + 1}°", (x, base.y + 14), 48, (255, 255, 255), "midtop", grosor=3)
            texto(pant, str(pa.total(i)), (x, base.y + 70), 26, TINTA, "midtop", borde=None)
            cs = personajes.cuadros(j["clave"], j["piel"], j["pelo"])
            cuadro = int(self.t * 6 + puesto) % 4
            esc = 8 if puesto == 0 else 6
            img = pygame.transform.scale(cs["abajo"][cuadro], (16 * esc, 24 * esc))
            salto = abs(math.sin(self.t * 5 + puesto)) * (24 if puesto == 0 else 8)
            pant.blit(img, img.get_rect(midbottom=(x, base.y + 4 - salto)))
            texto(pant, j["nombre"], (x, base.y - 24 * esc - 14 - salto), 26, p["color"], "midbottom")
            if puesto == 0:
                corona = escalar(sprites.estrella(brillo=1), 4)
                pant.blit(corona, corona.get_rect(midbottom=(x, base.y - 24 * esc - 44 - salto)))
        nombre, lema, color = CANDIDATOS[self.ganador]
        texto(pant, f"Alcalde de Ciudad Nova: {nombre}", (ANCHO // 2, 100), 26, color, "midtop")
        texto(pant, "ENTER: volver al menú  ·  R: jugar otra partida", (ANCHO - 20, ALTO - 16), 16, (220, 214, 240), "bottomright", 600)

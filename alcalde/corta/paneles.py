"""Paneles que se abren encima de cualquier pantalla: tienda, álbum, ayuda y opciones.

Cada panel tiene evento(e) -> "cerrar" o None, actualizar(dt) y dibujar(sup).
"""
from __future__ import annotations

import math

import pygame

from ..modelo.mapa import ZONAS, nombre_zona
from ..ui.dibujo import (AZUL, BLANCO, LILA, MANGO, ROJO, TINTA, TINTA2, VERDE, ancho_texto, circulo, icono, mezclar,
                         pildora, rebote, texto)
from ..ui.tema import TEMA
from .comunes import Boton, Escala, estrellas, panel, parrafo, velo
from .contenido import BARRIOS_JUEGO, MEJORAS, PODERES, SENALES

AZUL_OK = (29, 155, 240)


class Panel:
    titulo = ""
    icono = "info"

    def __init__(self, app):
        self.app = app
        self.t = 0.0
        self.btn_cerrar = Boton("Cerrar", "cerrar", (236, 238, 248), "circle-x", tecla=pygame.K_ESCAPE)

    def actualizar(self, dt):
        self.t += dt

    def evento(self, e):
        if self.btn_cerrar.toca(e):
            self.app.sonar("click")
            return "cerrar"
        return self.evento_panel(e)

    def evento_panel(self, e):
        return None

    def marco(self, sup):
        E = Escala(sup)
        velo(sup, 170)
        k = rebote(min(1, self.t / 0.3))
        r = E.r(70, 50 + (1 - k) * 30, 1140, 620)
        panel(sup, r, BLANCO, round(34 * E.U))
        icono(sup, self.icono, (r.x + 52 * E.U, r.y + 50 * E.U), 38 * E.U, LILA, 2.6)
        texto(sup, self.titulo, (r.x + 84 * E.U, r.y + 50 * E.U), 34 * E.U, TINTA, 700, "titulo", "midleft")
        self.btn_cerrar.dibujar(sup, pygame.Rect(r.right - 200 * E.U, r.y + 20 * E.U, 176 * E.U, 58 * E.U), self.t)
        return E, r


class Pestanas(Panel):
    """Panel con pestañas a la izquierda."""
    paginas = []

    def __init__(self, app):
        super().__init__(app)
        self.pagina = 0
        self._rects = []

    def evento_panel(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in enumerate(self._rects):
                if r.collidepoint(e.pos):
                    self.pagina = i
                    self.app.sonar("click")
        elif e.type == pygame.KEYDOWN and e.key in (pygame.K_DOWN, pygame.K_RIGHT, pygame.K_TAB):
            self.pagina = (self.pagina + 1) % len(self.paginas)
        elif e.type == pygame.KEYDOWN and e.key in (pygame.K_UP, pygame.K_LEFT):
            self.pagina = (self.pagina - 1) % len(self.paginas)
        return None

    def dibujar(self, sup):
        E, r = self.marco(sup)
        U = E.U
        self._rects = []
        y = r.y + 110 * U
        for i, (nombre, ic) in enumerate(self.paginas):
            rr = pygame.Rect(r.x + 26 * U, y, 250 * U, 54 * U)
            sel = i == self.pagina
            pygame.draw.rect(sup, LILA if sel else (241, 244, 255), rr, border_radius=round(18 * U))
            icono(sup, ic, (rr.x + 28 * U, rr.centery), 22 * U, BLANCO if sel else LILA, 2.6)
            texto(sup, nombre, (rr.x + 50 * U, rr.centery), 15 * U, BLANCO if sel else TINTA, 900, ancla="midleft")
            self._rects.append(rr)
            y += 62 * U
        area = pygame.Rect(r.x + 310 * U, r.y + 110 * U, r.w - 340 * U, r.h - 136 * U)
        getattr(self, "pagina_" + str(self.pagina))(sup, area, U)


# ------------------------------------------------------------------ tienda
class Tienda(Panel):
    titulo = "Tienda de mejoras"
    icono = "store"

    def __init__(self, app, campana):
        super().__init__(app)
        self.c = campana
        self.botones = {k: Boton("", k, MANGO, "coins") for k in MEJORAS}

    def evento_panel(self, e):
        for k, b in self.botones.items():
            if b.toca(e):
                if self.c.comprar(k):
                    self.app.sonar("logro")
                    self.c.guardar()
                else:
                    self.app.sonar("malo")
        return None

    def dibujar(self, sup):
        E, r = self.marco(sup)
        U = E.U
        icono(sup, "coins", (r.x + 480 * U, r.y + 50 * U), 30 * U, (230, 159, 0), 2.6)
        texto(sup, f"{self.c.monedas} monedas", (r.x + 504 * U, r.y + 50 * U), 24 * U, TINTA, 700, "titulo", "midleft")
        cw, ch = 340 * U, 230 * U
        for i, (k, (nombre, ic, desc, precios)) in enumerate(MEJORAS.items()):
            fila, col = divmod(i, 3)
            x = r.x + 30 * U + col * (cw + 20 * U) + (fila * (cw + 20 * U) / 2 if fila else 0)
            y = r.y + 110 * U + fila * (ch + 20 * U)
            c = pygame.Rect(x, y, cw, ch)
            pygame.draw.rect(sup, (246, 247, 255), c, border_radius=round(22 * U))
            circulo(sup, (c.x + 50 * U, c.y + 52 * U), 32 * U, mezclar(MANGO, BLANCO, 0.55))
            icono(sup, ic, (c.x + 50 * U, c.y + 52 * U), 34 * U, TINTA, 2.6)
            texto(sup, nombre, (c.x + 96 * U, c.y + 38 * U), 21 * U, TINTA, 700, "titulo", "midleft")
            nivel = self.c.mejoras.get(k, 0)
            for p in range(len(precios)):
                circulo(sup, (c.x + 104 * U + p * 26 * U, c.y + 70 * U), 9 * U, VERDE if p < nivel else (220, 222, 236))
            parrafo(sup, desc, c.x + 24 * U, c.y + 100 * U, cw - 48 * U, 15 * U, TINTA2, max_lineas=2)
            precio = self.c.precio(k)
            b = self.botones[k]
            if precio is None:
                b.etiqueta, b.activo = "¡Al máximo!", False
            else:
                b.etiqueta, b.activo = f"Comprar · {precio}", self.c.monedas >= precio
            b.dibujar(sup, pygame.Rect(c.x + 24 * U, c.bottom - 70 * U, cw - 48 * U, 52 * U), self.t)


# ------------------------------------------------------------------ álbum
class Album(Pestanas):
    titulo = "Álbum del detective"
    icono = "book-open"
    paginas = [("Pistas de mentira", "search"), ("Archivo de hechos", "archive"), ("Barrios", "map")]

    def __init__(self, app, campana):
        super().__init__(app)
        self.c = campana

    def pagina_0(self, sup, area, U):
        vistas = set(self.c.senales) if self.c else set()
        texto(sup, f"Encontraste {len(vistas)} de {len(SENALES)} pistas. Cada vez que cortas una mentira, aprendes su truco.",
              (area.x, area.y + 10 * U), 15 * U, TINTA2, 800, ancla="midleft")
        cw, ch = (area.w - 30 * U) / 3, 150 * U
        for i, (sid, (nombre, ic, desc)) in enumerate(SENALES.items()):
            fila, col = divmod(i, 3)
            c = pygame.Rect(area.x + col * (cw + 15 * U), area.y + 34 * U + fila * (ch - 30 * U), cw, ch - 40 * U)
            tiene = sid in vistas
            pygame.draw.rect(sup, (255, 240, 238) if tiene else (238, 240, 248), c, border_radius=round(16 * U))
            circulo(sup, (c.x + 30 * U, c.y + 30 * U), 20 * U, BLANCO)
            icono(sup, ic if tiene else "lock", (c.x + 30 * U, c.y + 30 * U), 22 * U, ROJO if tiene else TINTA2, 2.6)
            texto(sup, nombre if tiene else "???", (c.x + 58 * U, c.y + 30 * U), 17 * U, TINTA, 700, "titulo", "midleft")
            if tiene:
                parrafo(sup, desc, c.x + 14 * U, c.y + 52 * U, c.w - 28 * U, 12.5 * U, TINTA2, max_lineas=3, interlineado=1.2)
            else:
                texto(sup, "Córtala para descubrirla", (c.x + 14 * U, c.y + 66 * U), 13 * U, TINTA2, 800, ancla="midleft")

    def pagina_1(self, sup, area, U):
        arch = self.c.archivo if self.c else None
        n = len(arch) if arch else 0
        alto = arch.altura if arch else 0
        parrafo(sup, f"Las noticias verdaderas que dejaste llegar a la gente quedan guardadas aquí. Se ordenan solas "
                     f"con un árbol AVL: {n} hechos, altura {alto}. Se leen en orden alfabético (recorrido en inorden).",
                area.x, area.y, area.w, 15 * U, TINTA2)
        if not n:
            texto(sup, "Todavía no hay hechos. ¡Deja pasar las noticias con chulito azul!", (area.centerx, area.centery),
                  18 * U, LILA, 900)
            return
        claves = [k for k, _ in arch.inorden()]
        por_col = 12
        for i, k in enumerate(claves[:36]):
            col, fila = divmod(i, por_col)
            x = area.x + col * (area.w / 3)
            y = area.y + 70 * U + fila * 34 * U
            circulo(sup, (x + 10 * U, y), 9 * U, AZUL_OK)
            icono(sup, "check", (x + 10 * U, y), 12 * U, BLANCO, 3)
            texto(sup, k, (x + 26 * U, y), 14 * U, TINTA, 800, ancla="midleft")

    def pagina_2(self, sup, area, U):
        y = area.y + 14 * U
        for z in sorted(ZONAS, key=nombre_zona):
            info = BARRIOS_JUEGO[z]
            icono(sup, info["icono"], (area.x + 18 * U, y), 22 * U, LILA, 2.6)
            texto(sup, nombre_zona(z), (area.x + 44 * U, y), 17 * U, TINTA, 700, "titulo", "midleft")
            texto(sup, info["titulo"], (area.x + 300 * U, y), 15 * U, TINTA2, 900, ancla="midleft")
            if self.c and z in self.c.liberadas:
                estrellas(sup, (area.right - 80 * U, y), 16 * U, self.c.estrellas.get(z, 1))
            else:
                texto(sup, "sin liberar", (area.right - 80 * U, y), 14 * U, TINTA2, 800)
            y += 50 * U


# ------------------------------------------------------------------ ayuda
class Ayuda(Pestanas):
    titulo = "Ayuda"
    icono = "circle-help"
    paginas = [("Cómo se juega", "gamepad-2"), ("Atajos: ¿es mentira?", "search"), ("Barrios", "map"),
               ("Personajes y poderes", "sparkles"), ("Mapa y elección", "flag"), ("Controles", "mouse-pointer-click"),
               ("Cómo funciona por dentro", "git-branch")]

    def _items(self, sup, area, U, items, tam=16):
        y = area.y + 6 * U
        for ic, titulo, desc in items:
            circulo(sup, (area.x + 22 * U, y + 18 * U), 20 * U, mezclar(LILA, BLANCO, 0.82))
            icono(sup, ic, (area.x + 22 * U, y + 18 * U), 22 * U, LILA, 2.6)
            texto(sup, titulo, (area.x + 56 * U, y + 12 * U), 19 * U, TINTA, 700, "titulo", "midleft")
            fin = parrafo(sup, desc, area.x + 56 * U, y + 26 * U, area.w - 70 * U, tam * U, TINTA2)
            y = fin + 14 * U

    def pagina_0(self, sup, area, U):
        self._items(sup, area, U, [
            ("scissors", "Corta lo falso", "Arrastra el mouse con el botón izquierdo sobre las publicaciones falsas."),
            ("badge-check", "Deja pasar lo verdadero", "Las noticias con chulito azul vienen de una fuente oficial. Si "
                                                       "llegan abajo, la gente se informa y el barrio gana confianza."),
            ("heart-handshake", "Cuida la confianza del barrio", "Cada mentira que cae o cada verdad que cortas le "
                                                                 "quita confianza. Si llega a cero, pierdes el nivel."),
            ("flame", "Combos y fiebre", "Corta varias mentiras seguidas para hacer combo. Con 8 seguidas entras en "
                                         "FIEBRE: puntos dobles."),
            ("star", "Estrellas", "1 estrella si salvas el barrio, 2 si queda con buena confianza y 3 si además no "
                                  "cortaste ninguna verdad."),
        ])

    def pagina_1(self, sup, area, U):
        texto(sup, "El atajo más importante:", (area.x, area.y + 10 * U), 18 * U, TINTA, 700, "titulo", "midleft")
        circulo(sup, (area.x + 250 * U, area.y + 10 * U), 12 * U, AZUL_OK)
        icono(sup, "check", (area.x + 250 * U, area.y + 10 * U), 16 * U, BLANCO, 3)
        texto(sup, "chulito azul = fuente oficial = verdad", (area.x + 270 * U, area.y + 10 * U), 18 * U, AZUL, 900,
              ancla="midleft")
        parrafo(sup, "Las mentiras traen señales. Al principio salen como íconos rojos en la esquina de la tarjeta; "
                     "en los barrios difíciles tendrás que reconocerlas solo leyendo:", area.x, area.y + 34 * U, area.w,
                15 * U, TINTA2)
        cw = (area.w - 20 * U) / 2
        for i, (sid, (nombre, ic, desc)) in enumerate(SENALES.items()):
            col, fila = divmod(i, 6)
            x = area.x + col * (cw + 20 * U)
            y = area.y + 100 * U + fila * 62 * U
            circulo(sup, (x + 16 * U, y + 14 * U), 15 * U, (255, 230, 226))
            icono(sup, ic, (x + 16 * U, y + 14 * U), 18 * U, ROJO, 2.6)
            texto(sup, nombre, (x + 40 * U, y + 6 * U), 15 * U, TINTA, 900, ancla="midleft")
            parrafo(sup, desc, x + 40 * U, y + 14 * U, cw - 50 * U, 12 * U, TINTA2, max_lineas=2, interlineado=1.15)

    def pagina_2(self, sup, area, U):
        items = [(BARRIOS_JUEGO[z]["icono"], f"{nombre_zona(z)}: {BARRIOS_JUEGO[z]['titulo']}", BARRIOS_JUEGO[z]["texto"])
                 for z in ("PLAZA", "NORTE", "PRADO", "COLEGIO", "PARQUE", "TERMINAL", "ESTADIO", "HOSPITAL", "ALCALDIA")]
        y = area.y
        for ic, t, d in items:
            icono(sup, ic, (area.x + 16 * U, y + 14 * U), 20 * U, LILA, 2.6)
            texto(sup, t, (area.x + 40 * U, y + 8 * U), 15 * U, TINTA, 900, ancla="midleft")
            parrafo(sup, d, area.x + 40 * U, y + 18 * U, area.w - 50 * U, 13 * U, TINTA2, max_lineas=1)
            y += 52 * U

    def pagina_3(self, sup, area, U):
        nombres = {"periodista": "Ana, la Periodista", "influencer": "Beto, el Influencer",
                   "ciudadano": "Caro, la Ciudadana", "candidato": "Dani, el Candidato"}
        items = [(PODERES[r]["icono"], f"{nombres[r]}: {PODERES[r]['nombre']}", PODERES[r]["texto"]) for r in PODERES]
        items.append(("zap", "¿Cómo se carga el poder?", "Cada mentira que cortas llena el círculo de abajo a la "
                                                        "derecha. Cuando brilla, pulsa Espacio o el clic derecho."))
        self._items(sup, area, U, items)

    def pagina_4(self, sup, area, U):
        self._items(sup, area, U, [
            ("map", "Libera Ciudad Nova", "Empiezas en la Plaza. Cada barrio que salvas abre el camino a sus vecinos "
                                          "(las calles del mapa)."),
            ("cloud-lightning", "El rumor se mueve de noche", "Después de cada nivel pasa una noche y los barrios "
                                                             "enfermos contagian a un vecino. Los liberados frenan el "
                                                             "contagio: escoge bien a dónde ir."),
            ("store", "Monedas y tienda", "Ganas monedas por estrellas y puntos. Cómpralas en mejoras: filo largo, "
                                          "calma, recarga rápida y más."),
            ("bot", "El jefe final", "En la Alcaldía espera el Bot Supremo. Al derrotarlo llega la elección."),
            ("medal", "La elección", "Cada barrio vota. Los liberados votan informados: entre más barrios salves "
                                     "antes del jefe, mejor termina la ciudad."),
        ])

    def pagina_5(self, sup, area, U):
        self._items(sup, area, U, [
            ("mouse-pointer-click", "Clic izquierdo y arrastrar", "Cortar."),
            ("zap", "Espacio o clic derecho", "Usar el poder de tu personaje cuando esté cargado."),
            ("pause", "Esc", "Pausar el nivel o cerrar un panel."),
            ("volume-2", "M", "Silenciar o activar el sonido."),
            ("monitor", "F11", "Pantalla completa."),
        ])

    def pagina_6(self, sup, area, U):
        self._items(sup, area, U, [
            ("network", "Grafo de la ciudad", "Los barrios son vértices y las calles son aristas con minutos. Solo "
                                              "puedes jugar en vecinos de un barrio liberado y el rumor se contagia "
                                              "por las calles (BFS). El mapa marca la ruta más corta (Dijkstra)."),
            ("users", "Grafo social", "Cada vecino sigue a otros. Cuando un ORIGEN llega arriba, se lo reenvían sus "
                                      "seguidores: las copias muestran quién la reenvió."),
            ("git-branch", "Árbol del rumor", "El ORIGEN es la raíz y cada reenvío es un hijo. Cortar el origen poda "
                                              "todo su subárbol: por eso caen todas las copias."),
            ("archive", "Árbol AVL de hechos", "Las noticias verdaderas que llegan a la gente se guardan en un AVL "
                                               "que se mantiene balanceado y se lee en orden en el álbum."),
            ("server", "Cliente-servidor", "En el duelo, un computador hace de servidor: reparte la misma partida, "
                                           "lleva los puntajes y pasa los ataques de un jugador a otro."),
        ], tam=14)


# ------------------------------------------------------------------ opciones
class Opciones(Panel):
    titulo = "Opciones"
    icono = "settings"
    LISTA = [("sonido", "volume-2", "Sonido", "Efectos de sonido del juego."),
             ("musica", "music", "Música", "Música de fondo."),
             ("tranquilo", "hourglass", "Modo tranquilo", "Todo va más despacio: ideal para niños pequeños o para leer con calma."),
             ("menos_movimiento", "eye", "Menos movimiento", "Sin temblores de pantalla ni destellos fuertes."),
             ("subtitulos", "captions", "Subtítulos de sonido", "Muestra en texto los sonidos importantes (para quien no oye bien).")]

    def __init__(self, app):
        super().__init__(app)
        self._rects = {}

    def evento_panel(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for k, r in self._rects.items():
                if r.collidepoint(e.pos):
                    TEMA.cambiar(k, not TEMA.op[k])
                    if k in ("sonido", "musica"):
                        self.app.aplicar_sonido()
                    self.app.sonar("click")
        return None

    def dibujar(self, sup):
        E, r = self.marco(sup)
        U = E.U
        y = r.y + 120 * U
        self._rects = {}
        for k, ic, nombre, desc in self.LISTA:
            fila = pygame.Rect(r.x + 60 * U, y, r.w - 120 * U, 80 * U)
            pygame.draw.rect(sup, (246, 247, 255), fila, border_radius=round(20 * U))
            icono(sup, ic, (fila.x + 40 * U, fila.centery), 30 * U, LILA, 2.6)
            texto(sup, nombre, (fila.x + 80 * U, fila.y + 28 * U), 21 * U, TINTA, 700, "titulo", "midleft")
            texto(sup, desc, (fila.x + 80 * U, fila.y + 56 * U), 14 * U, TINTA2, 800, ancla="midleft")
            on = TEMA.op.get(k, False)
            sw = pygame.Rect(fila.right - 110 * U, fila.centery - 20 * U, 80 * U, 40 * U)
            pygame.draw.rect(sup, VERDE if on else (210, 212, 228), sw, border_radius=round(20 * U))
            circulo(sup, (sw.right - 20 * U if on else sw.x + 20 * U, sw.centery), 16 * U, BLANCO)
            self._rects[k] = fila
            y += 92 * U

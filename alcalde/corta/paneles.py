"""Paneles que se abren encima de cualquier pantalla: tienda, álbum, ayuda, opciones, récords y confirmación.

Cada panel tiene evento(e) -> "cerrar", "si" (solo Confirmar) o None, actualizar(dt) y dibujar(sup).
"""
from __future__ import annotations

import pygame

from ..estructuras.arbol_decision import HOJA, PREGUNTA, arbol_viral
from ..modelo.mapa import ZONAS, nombre_zona
from ..ui.dibujo import AZUL, BLANCO, LILA, MANGO, ROJO, TINTA, TINTA2, VERDE, ancho_texto, circulo, icono, mezclar, \
    rebote, texto
from ..ui.tema import TEMA
from . import records
from .comunes import Boton, Escala, estrellas, panel, parrafo, velo
from . import vista_red
from .contenido import BARRIOS_JUEGO, INDICADORES, MEJORAS, PODERES, SENALES
from .logros import LOGROS, REGISTRO

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
        y = r.y + 104 * U
        paso = 62 if len(self.paginas) <= 7 else 52
        for i, (nombre, ic) in enumerate(self.paginas):
            rr = pygame.Rect(r.x + 26 * U, y, 250 * U, (paso - 8) * U)
            sel = i == self.pagina
            pygame.draw.rect(sup, LILA if sel else (241, 244, 255), rr, border_radius=round(18 * U))
            icono(sup, ic, (rr.x + 28 * U, rr.centery), 22 * U, BLANCO if sel else LILA, 2.6)
            texto(sup, nombre, (rr.x + 50 * U, rr.centery), 15 * U, BLANCO if sel else TINTA, 900, ancla="midleft")
            self._rects.append(rr)
            y += paso * U
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
    paginas = [("Pistas de mentira", "search"), ("Archivo de hechos", "archive"), ("Barrios", "map"),
               ("Logros", "trophy"), ("Mi red", "users"), ("Diario Nova", "newspaper")]

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


    def pagina_3(self, sup, area, U):
        texto(sup, f"Tienes {len(REGISTRO.tiene)} de {len(LOGROS)} logros. Se ganan jugando en cualquier modo.",
              (area.x, area.y + 10 * U), 15 * U, TINTA2, 800, ancla="midleft")
        cw, ch = (area.w - 20 * U) / 3, 74 * U
        for i, (k, (nombre, ic, desc, _)) in enumerate(LOGROS.items()):
            fila, col = divmod(i, 3)
            c = pygame.Rect(area.x + col * (cw + 10 * U), area.y + 34 * U + fila * (ch + 4 * U), cw, ch)
            tiene = k in REGISTRO
            pygame.draw.rect(sup, (255, 246, 214) if tiene else (238, 240, 248), c, border_radius=round(16 * U))
            circulo(sup, (c.x + 32 * U, c.centery), 22 * U, (255, 200, 40) if tiene else BLANCO)
            icono(sup, ic if tiene else "lock", (c.x + 32 * U, c.centery), 22 * U, TINTA if tiene else TINTA2, 2.6)
            texto(sup, nombre, (c.x + 64 * U, c.y + 22 * U), 16 * U, TINTA if tiene else TINTA2, 700, "titulo", "midleft")
            parrafo(sup, desc, c.x + 64 * U, c.y + 32 * U, c.w - 76 * U, 12 * U, TINTA2, max_lineas=2, interlineado=1.15)
            hecho, meta = REGISTRO.progreso(k)
            if meta > 1 and not tiene:
                barra = pygame.Rect(c.x + 64 * U, c.bottom - 12 * U, c.w - 120 * U, 6 * U)
                pygame.draw.rect(sup, BLANCO, barra, border_radius=round(3 * U))
                relleno = barra.copy()
                relleno.w = round(barra.w * hecho / meta)
                pygame.draw.rect(sup, LILA, relleno, border_radius=round(3 * U))
                texto(sup, f"{hecho}/{meta}", (c.right - 14 * U, c.bottom - 10 * U), 12 * U, LILA, 900, ancla="midright")

    def pagina_4(self, sup, area, U):
        if not self.c:
            texto(sup, "Empieza una campaña para ver tu red social.", area.center, 20 * U, LILA, 900)
            return
        red = self.c.red
        yo = self.c.personaje.get("nombre")
        mapa = pygame.Rect(area.x, area.y, area.w - 250 * U, area.h)
        pygame.draw.rect(sup, (244, 245, 255), mapa, border_radius=round(20 * U))
        nivel, superp = vista_red.mi_red(sup, red, mapa, U, yo, self.c.personaje.get("rol", "npc"))
        x0, y = mapa.right + 20 * U, area.y + 6 * U
        texto(sup, "Tu red en Civitas", (x0, y + 10 * U), 20 * U, TINTA, 700, "titulo", "midleft")
        y += 40 * U
        saltos = [sum(1 for n in nivel.values() if n == k) for k in (1, 2, 3)]
        filas = [(vista_red.COLOR_SALTO[1], f"{saltos[0]} te siguen", "a un salto de ti: les llega primero"),
                 (vista_red.COLOR_SALTO[2], f"{saltos[1]} más a 2 saltos", "los seguidores de tus seguidores"),
                 (vista_red.COLOR_SALTO[3], f"{saltos[2]} más a 3 saltos", "tres pasos de persona a persona"),
                 (LILA, f"Tú sigues a {red.grado_entrada(yo) if yo in red else 0}", "de ellos te llegan las noticias")]
        for col, grande, chico in filas:
            circulo(sup, (x0 + 8 * U, y + 10 * U), 7 * U, col)
            texto(sup, grande, (x0 + 24 * U, y + 4 * U), 17 * U, TINTA, 900, ancla="midleft")
            texto(sup, chico, (x0 + 24 * U, y + 24 * U), 12 * U, TINTA2, 800, ancla="midleft")
            y += 50 * U
        y = parrafo(sup, f"Superpropagadores (los que más gente los sigue): {', '.join(superp)}.", x0, y + 6 * U,
                    area.right - x0, 13 * U, TINTA2)
        parrafo(sup, "Es un BFS desde ti: cada color es un salto de persona a persona. El influencer tiene más "
                     "seguidores, por eso llega más lejos.", x0, y + 8 * U, area.right - x0, 12 * U, LILA)


    def pagina_5(self, sup, area, U):
        diario = list(self.c.diario) if self.c else []
        if not diario:
            texto(sup, "Cada mañana el Diario Nova cuenta lo que pasó. ¡Juega un barrio para ver el primero!",
                  area.center, 18 * U, LILA, 900)
            return
        texto(sup, "DIARIO NOVA", (area.x, area.y + 14 * U), 26 * U, TINTA, 700, "titulo", "midleft")
        texto(sup, "Los titulares de tu campaña, del más nuevo al más viejo", (area.right, area.y + 16 * U), 13 * U,
              TINTA2, 900, ancla="midright")
        pygame.draw.line(sup, TINTA, (area.x, area.y + 36 * U), (area.right, area.y + 36 * U), max(2, round(3 * U)))
        y = area.y + 52 * U
        for d in reversed(diario[-8:]):
            pygame.draw.rect(sup, (250, 246, 236), (area.x, y, area.w, 50 * U), border_radius=round(12 * U))
            texto(sup, f"Día {d['dia']}", (area.x + 16 * U, y + 25 * U), 14 * U, LILA, 900, ancla="midleft")
            texto(sup, d["titulo"], (area.x + 90 * U, y + 16 * U), 17 * U, TINTA, 700, "titulo", "midleft")
            bajada = d.get("bajada", "")
            while ancho_texto(bajada, 12 * U, 800) > area.w - 110 * U and len(bajada) > 8:
                bajada = bajada[:-2]
            if bajada != d.get("bajada", ""):
                bajada = bajada[:-1] + "…"
            texto(sup, bajada, (area.x + 90 * U, y + 36 * U), 12 * U, TINTA2, 800, ancla="midleft")
            y += 56 * U


# ------------------------------------------------------------------ ayuda
class Ayuda(Pestanas):
    titulo = "Ayuda"
    icono = "circle-help"
    paginas = [("Cómo se juega", "gamepad-2"), ("Atajos: ¿es mentira?", "search"), ("La alerta viral", "siren"),
               ("Indicadores de la ciudad", "landmark"), ("Barrios", "map"), ("Personajes y poderes", "sparkles"),
               ("Mapa y elección", "flag"), ("Controles", "mouse-pointer-click"),
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
            ("siren", "La alerta viral", "Una vez por nivel todo se congela: tienes 10 segundos para verificar, "
                                         "compartir, reportar o ignorar una publicación que se está regando."),
            ("angry", "Vecinos peleando", "Si aparece una burbuja roja en la calle, córtala para que hagan las paces."),
            ("flame", "Combos, fiebre y estrellas", "Corta mentiras seguidas para hacer combo; con 8 seguidas hay "
                                                    "FIEBRE (puntos x2). Hasta 3 estrellas si salvas el barrio sin "
                                                    "cortar verdades."),
        ], tam=15)

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
        parrafo(sup, "Todo se congela y tienes 10 segundos. Cada botón es una rama de este árbol; las hojas de "
                     "colores son las consecuencias (verde: bien, rojo: mal). Lo mejor siempre empieza por VERIFICAR.",
                area.x, area.y, area.w, 15 * U, TINTA2)
        dibujar_arbol(sup, arbol_viral(), pygame.Rect(area.x, area.y + 60 * U, area.w, area.h - 60 * U), U)

    def pagina_3(self, sup, area, U):
        como = {
            "verificada": "Sube si dejas llegar noticias reales o verificas. Baja si cortas una verdad.",
            "confianza": "Sube si salvas barrios con buena confianza. Baja si un barrio se pierde.",
            "convivencia": "Sube si calmas peleas entre vecinos o atrapas una campaña de convivencia.",
            "bienestar": "Sube con estrellas y campañas. Baja cuando caen publicaciones virales.",
            "desinformacion": "Mejor si baja. Sube con mentiras que caen, que compartes o que saltan de noche.",
            "conflictos": "Mejor si baja. Sube con peleas sin calmar y ataques sin pruebas que caen.",
        }
        self._items(sup, area, U, [(INDICADORES[k][2], INDICADORES[k][0], como[k]) for k in INDICADORES] +
                    [("vote", "¿Y para qué sirven?", "En la elección, la ciudad vota informada si estos indicadores "
                                                     "están bien: así gana un candidato con propuestas y no el de "
                                                     "los bots.")], tam=14)

    def pagina_4(self, sup, area, U):
        items = [(BARRIOS_JUEGO[z]["icono"], f"{nombre_zona(z)}: {BARRIOS_JUEGO[z]['titulo']}", BARRIOS_JUEGO[z]["texto"])
                 for z in ("PLAZA", "NORTE", "PRADO", "COLEGIO", "PARQUE", "TERMINAL", "ESTADIO", "HOSPITAL", "ALCALDIA")]
        y = area.y
        for ic, t, d in items:
            icono(sup, ic, (area.x + 16 * U, y + 14 * U), 20 * U, LILA, 2.6)
            texto(sup, t, (area.x + 40 * U, y + 8 * U), 15 * U, TINTA, 900, ancla="midleft")
            parrafo(sup, d, area.x + 40 * U, y + 18 * U, area.w - 50 * U, 13 * U, TINTA2, max_lineas=1)
            y += 52 * U

    def pagina_5(self, sup, area, U):
        nombres = {"periodista": "Ana, la Periodista", "influencer": "Beto, el Influencer",
                   "ciudadano": "Caro, la Ciudadana", "candidato": "Dani, el Candidato"}
        items = [(PODERES[r]["icono"], f"{nombres[r]}: {PODERES[r]['nombre']}", PODERES[r]["texto"]) for r in PODERES]
        items.append(("zap", "¿Cómo se carga el poder?", "Cada mentira que cortas llena el círculo de abajo a la "
                                                        "derecha. Cuando brilla, pulsa Espacio o el clic derecho."))
        self._items(sup, area, U, items)

    def pagina_6(self, sup, area, U):
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
            ("flag", "Misión del día", "Cada barrio trae un objetivo extra. Si lo cumples ganas +50 puntos y "
                                       "+20 monedas."),
            ("newspaper", "Diario Nova y logros", "Cada mañana el periódico cuenta lo que pasó. Los 18 logros se "
                                                  "ganan en cualquier modo y se ven en el álbum."),
        ], tam=14)

    def pagina_7(self, sup, area, U):
        self._items(sup, area, U, [
            ("mouse-pointer-click", "Clic izquierdo y arrastrar", "Cortar."),
            ("zap", "Espacio o clic derecho", "Usar el poder de tu personaje cuando esté cargado."),
            ("pause", "Esc", "Pausar el nivel o cerrar un panel."),
            ("siren", "1, 2, 3, 4", "Escoger un botón en la alerta viral (también con clic)."),
            ("volume-2", "M", "Silenciar o activar el sonido."),
            ("monitor", "F11", "Pantalla completa."),
        ])

    def pagina_8(self, sup, area, U):
        self._items(sup, area, U, [
            ("network", "Grafo de la ciudad", "Los barrios son vértices y las calles son aristas con minutos. Solo "
                                              "puedes jugar en vecinos de un barrio liberado y el rumor se contagia "
                                              "por las calles (BFS). El mapa marca la ruta más corta (Dijkstra)."),
            ("users", "Grafo social", "Cada vecino sigue a otros. Lo que alguien comparte les llega a sus seguidores "
                                      "salto por salto (BFS): así se ve quién lo recibe, cuántos y qué tan rápido."),
            ("git-branch", "Árbol del rumor", "El ORIGEN es la raíz y cada reenvío es un hijo. Cortar el origen poda "
                                              "todo su subárbol: por eso caen todas las copias."),
            ("waypoints", "Árbol de decisiones", "La alerta viral recorre un árbol: cada botón es un hijo, el juego "
                                                 "responde «¿es verdadera?» y cada hoja guarda una consecuencia."),
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
             ("subtitulos", "captions", "Subtítulos de sonido", "Muestra en texto los sonidos importantes (para quien no oye bien)."),
             ("contraste", "contrast", "Alto contraste", "Oscurece el fondo y marca más las tarjetas (para quien ve poco)."),
             ("simbolos", "accessibility", "Símbolos grandes",
              "Tijeras rojas en lo falso y chulito azul en lo verdadero: para quien todavía no lee.")]

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
        y = r.y + 104 * U
        self._rects = {}
        for k, ic, nombre, desc in self.LISTA:
            fila = pygame.Rect(r.x + 60 * U, y, r.w - 120 * U, 64 * U)
            pygame.draw.rect(sup, (246, 247, 255), fila, border_radius=round(18 * U))
            icono(sup, ic, (fila.x + 40 * U, fila.centery), 28 * U, LILA, 2.6)
            texto(sup, nombre, (fila.x + 80 * U, fila.y + 22 * U), 19 * U, TINTA, 700, "titulo", "midleft")
            texto(sup, desc, (fila.x + 80 * U, fila.y + 45 * U), 13 * U, TINTA2, 800, ancla="midleft")
            on = TEMA.op.get(k, False)
            sw = pygame.Rect(fila.right - 110 * U, fila.centery - 20 * U, 80 * U, 40 * U)
            pygame.draw.rect(sup, VERDE if on else (210, 212, 228), sw, border_radius=round(20 * U))
            circulo(sup, (sw.right - 20 * U if on else sw.x + 20 * U, sw.centery), 16 * U, BLANCO)
            self._rects[k] = fila
            y += 72 * U


# ------------------------------------------------------------------ récords de la feria
class Records(Panel):
    titulo = "Récords de la feria"
    icono = "trophy"

    def dibujar(self, sup):
        E, r = self.marco(sup)
        U = E.U
        lista = records.mejores(10)
        if not lista:
            texto(sup, "Todavía no hay récords. ¡Sé el primero con «¡Jugar ya!»!", (r.centerx, r.centery), 22 * U, LILA,
                  900)
            return
        colores = [(255, 200, 40), (160, 166, 196), (205, 127, 50)]
        for i, d in enumerate(lista):
            y = r.y + 124 * U + i * 46 * U
            pygame.draw.rect(sup, (255, 246, 214) if i < 3 else (246, 247, 255),
                             (r.x + 120 * U, y - 20 * U, r.w - 240 * U, 40 * U), border_radius=round(14 * U))
            if i < 3:
                icono(sup, "medal", (r.x + 156 * U, y), 26 * U, colores[i], 2.8)
            else:
                texto(sup, str(i + 1), (r.x + 156 * U, y), 20 * U, TINTA2, 700, "titulo")
            texto(sup, d["nombre"], (r.x + 196 * U, y), 20 * U, TINTA, 900, ancla="midleft")
            rol = PODERES.get(d.get("rol"), {}).get("nombre", "")
            barrio = nombre_zona(d["zona"]) if d.get("zona") else ""
            texto(sup, " · ".join(x for x in (barrio, rol) if x), (r.x + 470 * U, y), 15 * U, TINTA2, 800, ancla="midleft")
            estrellas(sup, (r.right - 300 * U, y), 16 * U, d.get("estrellas", 0))
            texto(sup, f"{d['puntos']:,}".replace(",", "."), (r.right - 150 * U, y), 22 * U, TINTA, 700, "titulo",
                  "midright")


# ------------------------------------------------------------------ ¿seguro?
class Confirmar:
    """Pregunta antes de algo que no se puede deshacer. Enter o Esc dicen que no (lo seguro); el sí es con clic."""

    def __init__(self, app, pregunta, detalle, texto_si, al_aceptar):
        self.app = app
        self.t = 0.0
        self.pregunta, self.detalle = pregunta, detalle
        self.al_aceptar = al_aceptar
        self.btn_no = Boton("No, volver", "no", MANGO, "chevron-left", tecla=[pygame.K_ESCAPE, pygame.K_RETURN])
        self.btn_si = Boton(texto_si, "si", (255, 226, 226), "check", color_texto=ROJO)

    def actualizar(self, dt):
        self.t += dt

    def evento(self, e):
        if self.btn_no.toca(e):
            self.app.sonar("click")
            return "cerrar"
        if self.btn_si.toca(e):
            self.app.sonar("click")
            return "si"
        return None

    def dibujar(self, sup):
        E = Escala(sup)
        U = E.U
        velo(sup, 170)
        k = rebote(min(1, self.t / 0.3))
        r = panel(sup, E.r(340, 200 + (1 - k) * 30, 600, 300), BLANCO, round(32 * U))
        icono(sup, "circle-help", (r.centerx, r.y + 56 * U), 48 * U, LILA, 2.6)
        texto(sup, self.pregunta, (r.centerx, r.y + 114 * U), 30 * U, TINTA, 700, "titulo")
        texto(sup, self.detalle, (r.centerx, r.y + 152 * U), 17 * U, TINTA2, 900)
        self.btn_no.dibujar(sup, pygame.Rect(r.x + 40 * U, r.bottom - 96 * U, 250 * U, 64 * U), self.t)
        self.btn_si.dibujar(sup, pygame.Rect(r.right - 290 * U, r.bottom - 96 * U, 250 * U, 64 * U), self.t)


# ------------------------------------------------------------------ dibujo del árbol de decisiones
def dibujar_arbol(sup, arbol, area, U, camino=()):
    """Dibuja el árbol por niveles: las hojas se reparten a lo ancho y cada padre queda sobre sus hijos."""
    hojas = arbol.hojas()
    ancho = area.w / max(1, len(hojas))
    alto_nivel = (area.h - 60 * U) / max(1, arbol.altura())
    pos = {}

    def ubicar(n):
        if n.es_hoja:
            x = area.x + ancho * (hojas.index(n) + 0.5)
        else:
            xs = [ubicar(h) for h in n.hijos]
            x = sum(xs) / len(xs)
        pos[n.clave] = (x, area.y + 20 * U + n.profundidad * alto_nivel)
        return x

    ubicar(arbol.raiz)
    for n in arbol.preorden():
        for h in n.hijos:
            a, b = pos[n.clave], pos[h.clave]
            pygame.draw.line(sup, (200, 194, 236), a, b, max(2, round(3 * U)))
            if h.respuesta is not None:
                texto(sup, "Sí" if h.respuesta else "No", ((a[0] + b[0]) / 2 + 14 * U, (a[1] + b[1]) / 2), 12 * U,
                      VERDE if h.respuesta else ROJO, 900)
    for n in arbol.preorden():
        x, y = pos[n.clave]
        borde = None
        if n.tipo == HOJA:
            col = VERDE if n.bien else ROJO if n.bien is False else (150, 156, 186)
            fondo, color_texto = col, BLANCO
        elif n.tipo == PREGUNTA:
            fondo, color_texto = (236, 231, 255), LILA
        elif n.clave == "raiz":
            fondo, color_texto = LILA, BLANCO
        else:
            fondo, color_texto, borde = BLANCO, TINTA, LILA
        etiqueta = "¿Verdad?" if n.tipo == PREGUNTA else n.texto
        w = ancho_texto(etiqueta, 12 * U, 900) + 18 * U
        rr = pygame.Rect(0, 0, w, 26 * U)
        rr.center = (x, y)
        pygame.draw.rect(sup, fondo, rr, border_radius=round(13 * U))
        if borde:
            pygame.draw.rect(sup, borde, rr, max(1, round(2 * U)), border_radius=round(13 * U))
        if n.clave in camino:
            pygame.draw.rect(sup, MANGO, rr.inflate(6 * U, 6 * U), max(2, round(3 * U)), border_radius=round(16 * U))
        texto(sup, etiqueta, rr.center, 12 * U, color_texto, 900)
        if n.tipo == HOJA and n.puntos:
            texto(sup, f"{'+' if n.puntos > 0 else ''}{n.puntos}", (x, y + 24 * U), 12 * U, col, 900)

"""Menú principal, preparar partida, opciones y récords."""
import math
import random

import pygame

from .. import personajes, sprites
from ..config import ALTO, ANCHO, TINTA
from ..personajes import ORDEN, PERSONAJES
from ..recursos import escalar
from ..ui import panel, parrafo, render, texto
from .base import Botonera, Escena, FondoCiudad, es_aceptar, es_volver, pie, titulo_pantalla


def piloto(m, rng):
    """Un jugador automático para el fondo del menú."""
    j = m.jugador
    objetivos = m._blancos() + [(s.x, s.y) for s in m.estrellas]
    e = {}
    if objetivos:
        t = min(objetivos, key=lambda p: math.dist(p, j.pos))
        dx, dy = t[0] - j.x, t[1] - j.y
        e["der"], e["izq"] = dx > 40, dx < -40
        e["abajo"], e["arriba"] = dy > 40, dy < -40
        e["accion"] = math.dist(t, j.pos) < 100 and rng.random() < 0.08
    return e


class Titulo(Escena):
    inactividad = None

    def __init__(self, app):
        super().__init__(app)
        from ..mundo import Mundo
        from ..render import Render
        self.demo = Mundo(semilla=2026, personaje="caro", duracion=100000, pistas=False)
        self.vista = Render(self.demo, None, {"demo": True})
        self.rng = random.Random(4)
        self.velo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        for y in range(0, ALTO, 4):
            self.velo.fill((18, 12, 44, int(90 + 110 * abs(y - 330) / 400)), (0, y, ANCHO, 4))
        from .seleccion import Preparar, Seleccion
        from .ayuda import Ayuda
        from .en_linea import EnLinea
        self.botones = Botonera([
            ("¡Jugar ya!", lambda: self._con_historia(Seleccion(app, 1, 1, 90, True))),
            ("Con amigos (mismo PC)", lambda: self._con_historia(Preparar(app))),
            ("En línea", lambda: app.cambiar(EnLinea(app))),
            ("Ayuda", lambda: app.cambiar(Ayuda(app))),
            ("Opciones", lambda: app.cambiar(Opciones(app))),
            ("Récords y logros", lambda: app.cambiar(RecordsPantalla(app))),
            ("Salir", self._salir),
        ], centro=(ANCHO // 2, 474), ancho=360, alto=44, sep=8, tam=24)
        self.confirmar = None

    def _salir(self):
        """En la feria un niño puede tocar "Salir" sin querer: se pregunta antes (por defecto, no)."""
        self.confirmar = Botonera([("No, seguir aquí", self._no_salir), ("Sí, salir del juego", self._si_salir)],
                                  centro=(ANCHO // 2, 448), ancho=420, alto=60, sep=14, tam=26)

    def _no_salir(self):
        self.confirmar = None

    def _si_salir(self):
        self.app.corriendo = False

    def _con_historia(self, siguiente):
        """La primera vez se cuenta la historia de Ciudad Nova (3 escenas cortas)."""
        if self.app.op.get("historia_vista"):
            self.app.cambiar(siguiente)
        else:
            from .historia import Historia
            self.app.cambiar(Historia(self.app, siguiente))

    def evento(self, e):
        if self.confirmar:
            if es_volver(e):
                self.confirmar = None
            else:
                self.confirmar.evento(e, self.app)
            return
        if es_volver(e) and e.key == pygame.K_ESCAPE:
            return
        self.botones.evento(e, self.app)

    def actualizar(self, dt):
        super().actualizar(dt)
        m = self.demo
        m.actualizar(dt, piloto(m, self.rng))
        m.fx.clear()
        self.vista.actualizar(dt)
        if m.t > 240:
            from ..mundo import Mundo
            from ..render import Render
            self.demo = Mundo(semilla=self.rng.randrange(9999), personaje=self.rng.choice(ORDEN), duracion=100000, pistas=False)
            self.vista = Render(self.demo, None, {"demo": True})

    def dibujar(self, pant):
        self.vista.dibujar(pant)
        pant.blit(self.velo, (0, 0))
        # logo con letras que saltan
        letras = "CAZABULOS"
        colores = [(255, 205, 50), (255, 96, 170), (70, 205, 100), (70, 140, 255)]
        x = ANCHO // 2 - 290
        for i, ch in enumerate(letras):
            dy = math.sin(self.t * 3 + i * 0.6) * 8
            img = render(ch, 96, colores[i % 4], 700, TINTA, 5)
            pant.blit(img, (x, 40 + dy))
            x += img.get_width() - 6
        texto(pant, "Alcalde Digital · Ciudad Nova", (ANCHO // 2, 168), 26, (255, 255, 255), "midtop")
        # Bulos que flotan junto al logo
        for k, (bx, by) in enumerate(((ANCHO // 2 - 360, 90), (ANCHO // 2 + 330, 70))):
            img = escalar(sprites.bulo(int(self.t * 4 + k) % 2, k == 1, False, (1 if k == 0 else -1, 0)), 5)
            pant.blit(img, (bx - 40, by + math.sin(self.t * 2 + k) * 10))
        img = escalar(sprites.estrella(brillo=int(self.t * 2) % 2), 4)
        pant.blit(img, (ANCHO // 2 + 250, 150 + math.sin(self.t * 2.5) * 6))
        # los cuatro protagonistas
        for k, clave in enumerate(ORDEN):
            cs = personajes.cuadros(clave)
            cuadro = int(self.t * 6 + k) % 4
            img = escalar(cs["abajo"][cuadro], 6)
            x = 120 + k * 75 if k < 2 else ANCHO - 120 - (3 - k) * 75 - 96
            y = ALTO - 230 + (math.sin(self.t * 3 + k) * 4 if cuadro in (1, 3) else 0)
            pygame.draw.ellipse(pant, (0, 0, 0, 120), (x + 10, y + 136, 76, 16))
            pant.blit(img, (x, y))
            p = PERSONAJES[clave]
            texto(pant, p["nombre"], (x + 48, y + 150), 22, p["color"], "midtop")
            texto(pant, p["rol"], (x + 48, y + 176), 15, (230, 226, 245), "midtop", 600)
        self.botones.dibujar(pant, self.t)
        pie(pant, "Flechas y ENTER para elegir  ·  M silencia la música  ·  F11 pantalla completa", self.app)
        if self.confirmar:
            velo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
            velo.fill((16, 10, 36, 200))
            pant.blit(velo, (0, 0))
            panel(pant, (ANCHO // 2 - 290, 276, 580, 262), borde=(255, 205, 50))
            texto(pant, "¿Salir del juego?", (ANCHO // 2, 304), 40, (255, 205, 50), "midtop", grosor=3)
            self.confirmar.dibujar(pant, self.t)


class Selector:
    """Fila de opciones que se cambia con izquierda/derecha."""

    def __init__(self, nombre, valores, indice=0, ayuda=""):
        self.nombre = nombre
        self.valores = valores      # [(texto, valor)]
        self.i = indice
        self.ayuda = ayuda

    @property
    def valor(self):
        return self.valores[self.i][1]

    def mover(self, d):
        self.i = (self.i + d) % len(self.valores)


class Formulario(Escena):
    """Pantalla con filas de selectores y botones al final."""
    titulo = ""

    def __init__(self, app, filas, botones):
        super().__init__(app)
        self.fondo = FondoCiudad(app)
        self.filas = filas
        self.botones = botones      # [(texto, función)]
        self.sel = 0

    def _total(self):
        return len(self.filas) + len(self.botones)

    def cambio(self):
        pass

    def evento(self, e):
        if es_volver(e):
            self.volver()
            return
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % self._total()
                self.app.son.tocar("mover")
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % self._total()
                self.app.son.tocar("mover")
            elif e.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d) and self.sel < len(self.filas):
                self.filas[self.sel].mover(1 if e.key in (pygame.K_RIGHT, pygame.K_d) else -1)
                self.app.son.tocar("mover")
                self.cambio()
            elif es_aceptar(e):
                if self.sel < len(self.filas):
                    self.filas[self.sel].mover(1)
                    self.cambio()
                else:
                    self.app.son.tocar("click")
                    self.botones[self.sel - len(self.filas)][1]()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in enumerate(getattr(self, "_rects", [])):
                if r.collidepoint(e.pos):
                    self.sel = i
                    if i < len(self.filas):
                        self.filas[i].mover(1 if e.pos[0] > r.centerx else -1)
                        self.cambio()
                    else:
                        self.botones[i - len(self.filas)][1]()
                    self.app.son.tocar("click")

    def volver(self):
        self.app.cambiar(Titulo(self.app))

    def dibujar(self, pant):
        self.fondo.dibujar(pant, 1 / 60)
        titulo_pantalla(pant, self.titulo)
        self._rects = []
        y = 140
        alto_fila = 62 if len(self.filas) <= 5 else (54 if len(self.filas) <= 7 else 50)
        for i, f in enumerate(self.filas):
            activo = i == self.sel
            r = pygame.Rect(ANCHO // 2 - 420, y, 840, alto_fila - 8)
            panel(pant, r, (40, 30, 84) if activo else (26, 20, 52), 235, 14, (255, 205, 50) if activo else None)
            texto(pant, f.nombre, (r.x + 24, r.centery), 24, (255, 255, 255), "midleft")
            vt = f.valores[f.i][0]
            texto(pant, f"<  {vt}  >" if activo else vt, (r.right - 30, r.centery), 24,
                  (255, 205, 50) if activo else (220, 214, 240), "midright")
            self._rects.append(r)
            y += alto_fila
        if self.sel < len(self.filas) and self.filas[self.sel].ayuda:
            parrafo(pant, self.filas[self.sel].ayuda, (ANCHO // 2, y + 4), 18, 780, (230, 226, 245), ancla="midtop")
        y += 60
        xs = ANCHO // 2 - (len(self.botones) * 300 - 20) // 2
        from ..ui import boton
        for k, (txt, _) in enumerate(self.botones):
            r = pygame.Rect(xs + k * 300, max(y, ALTO - 120), 280, 60)
            boton(pant, r, txt, self.sel == len(self.filas) + k, tam=26, t=self.t)
            self._rects.append(r)
        pie(pant, "Arriba/abajo para elegir  ·  izquierda/derecha para cambiar  ·  ESC para volver", self.app)


SI_NO = [("Sí", True), ("No", False)]


class Opciones(Formulario):
    titulo = "Opciones"

    def __init__(self, app):
        op = app.op
        vol = [(f"{k * 10}%", k / 10) for k in range(11)]
        filas = [
            Selector("Música", vol, int(round(op["musica"] * 10)), "La música se puede apagar en cualquier momento con la tecla M."),
            Selector("Efectos de sonido", vol, int(round(op["efectos"] * 10))),
            Selector("Subtítulos de sonidos", SI_NO, 0 if op["subtitulos"] else 1,
                     "Escribe en pantalla los sonidos importantes (pitos, alarmas, golpes). Ayuda a quien no oye bien o juega sin volumen en la feria."),
            Selector("Alto contraste", SI_NO, 0 if op["contraste"] else 1,
                     "Deja siempre visibles los controles y marca al jugador con 'TÚ'. Ayuda a quien ve poco o se distrae con facilidad."),
            Selector("Modo tranquilo (para peques)", SI_NO, 0 if op["tranquilo"] else 1,
                     "Los Bulos van más despacio y las peleas duran más. Para niños pequeños o para aprender a jugar."),
            Selector("Pistas en pantalla", SI_NO, 0 if op["pistas"] else 1, "Muestra mensajes que explican qué hacer la primera vez."),
            Selector("Pantalla completa", SI_NO, 0 if op["pantalla_completa"] else 1,
                     "No: una ventana grande que llena la pantalla (se ven la barra de título y la de tareas). "
                     "Sí: todo el monitor. También se cambia con F11."),
            Selector("Volver solo al inicio (feria)", SI_NO, 0 if op.get("volver_inicio", True) else 1,
                     "Si nadie toca nada en 90 segundos, el juego vuelve a la pantalla de inicio para el siguiente niño."),
        ]
        super().__init__(app, filas, [("Listo", self.volver)])

    def cambio(self):
        op = self.app.op
        f = self.filas
        op["musica"], op["efectos"] = f[0].valor, f[1].valor
        op["subtitulos"], op["contraste"], op["tranquilo"] = f[2].valor, f[3].valor, f[4].valor
        op["pistas"] = f[5].valor
        if op["pantalla_completa"] != f[6].valor:
            self.app.poner_pantalla(f[6].valor)
        op["volver_inicio"] = f[7].valor
        self.app.aplicar_volumen()
        self.app.guardar_opciones()


class RecordsPantalla(Escena):
    def __init__(self, app):
        super().__init__(app)
        self.fondo = FondoCiudad(app)
        self.lista = app.records.mejores(10)

    def evento(self, e):
        if es_volver(e) or es_aceptar(e) or (e.type == pygame.MOUSEBUTTONDOWN):
            self.app.son.tocar("click")
            self.app.cambiar(Titulo(self.app))

    def dibujar(self, pant):
        from ..guardado import LOGROS
        self.fondo.dibujar(pant, 1 / 60)
        titulo_pantalla(pant, "Récords y logros", 24)
        r = panel(pant, (40, 100, 640, 540), borde=(255, 205, 50))
        texto(pant, "Mejores turnos", (r.x + 24, r.y + 14), 24, (255, 230, 150))
        if not self.lista:
            texto(pant, "Todavía no hay récords. ¡Juega una partida!", r.center, 22, (255, 255, 255), "center")
        for k, rec in enumerate(self.lista):
            y = r.y + 56 + k * 47
            color = [(255, 205, 50), (220, 220, 235), (230, 160, 100)][k] if k < 3 else (255, 255, 255)
            texto(pant, f"{k + 1}.", (r.x + 24, y), 24, color)
            clave = rec.get("personaje", "caro")
            img = escalar(personajes.retrato(clave), 2)
            pant.blit(img, (r.x + 70, y - 2))
            texto(pant, rec["nombre"], (r.x + 116, y), 24, PERSONAJES.get(clave, PERSONAJES["caro"])["color"])
            texto(pant, f"{rec['salvados']} a salvo", (r.x + 300, y + 4), 18, (200, 230, 210), peso=600)
            texto(pant, rec.get("fecha", ""), (r.x + 430, y + 4), 16, (190, 186, 220), peso=600)
            texto(pant, str(rec["total"]), (r.right - 24, y), 26, color, "topright")
        rl = panel(pant, (700, 100, 540, 540), borde=(255, 205, 50))
        ganados = self.app.logros.ganados
        texto(pant, f"Logros  {len(ganados & {c for c, *_ in LOGROS})}/{len(LOGROS)}", (rl.x + 24, rl.y + 14), 24, (255, 230, 150))
        for k, (clave, nombre, desc, _) in enumerate(LOGROS):
            col, fila = k % 2, k // 2
            x, y = rl.x + 20 + col * 262, rl.y + 56 + fila * 68
            ok = clave in ganados
            pygame.draw.circle(pant, (90, 60, 150) if ok else (70, 62, 110), (x + 18, y + 22), 17)
            if ok:
                pygame.draw.circle(pant, (255, 205, 50), (x + 18, y + 22), 17, 3)
            if ok:
                img = escalar(sprites.estrella(), 2)
                pant.blit(img, img.get_rect(center=(x + 18, y + 22)))
            texto(pant, nombre, (x + 44, y + 2), 18, (255, 255, 255) if ok else (170, 164, 200))
            parrafo(pant, desc, (x + 44, y + 26), 13, 200, (220, 214, 240) if ok else (140, 134, 170))
        pie(pant, "Los récords se ordenan con un árbol AVL y se guardan en la carpeta datos  ·  ENTER para volver", self.app)

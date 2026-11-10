"""AYUDA: objetivo, controles, personajes, cómo ganar, indicadores y las estructuras de datos."""
import pygame

from .. import personajes, sprites
from ..ciudad import VECINOS, grafo_social
from ..config import ALTO, ANCHO, TINTA
from ..estructuras.arbol_decision import arbol_publicacion
from ..hud import INDICADORES
from ..mapa import NODOS
from ..personajes import ORDEN, PERSONAJES
from ..recursos import borde, escalar
from ..ui import panel, parrafo, tecla, texto
from .base import Escena, FondoCiudad, es_volver, instrucciones, pie
from .final import anillos_bfs, dibujar_arbol
from .seleccion import tarjeta_personaje

PAGINAS = ["Objetivo", "Cómo se juega", "Personajes", "Cómo ganar", "Indicadores", "Grafos", "Árboles", "Multijugador"]


class Ayuda(Escena):
    def __init__(self, app, volver=None):
        super().__init__(app)
        self.fondo = FondoCiudad(app, 190)
        self.pag = 0
        self.volver = volver
        self.social = grafo_social()
        from ..mundo import mapa_compartido
        _, self.ciudad = mapa_compartido()
        self.arbol = arbol_publicacion()
        for camino in (["falsa", "atrapar"], ["falsa", "atrapar"], ["falsa", "llega", "curar"], ["falsa", "llega", "pasar"],
                       ["verdadera", "compartir"]):
            self.arbol.recorrer(camino)
        self._tabs = []

    def evento(self, e):
        if es_volver(e):
            self.app.son.tocar("click")
            if self.volver:
                self.app.cambiar(self.volver)
            else:
                from .menu import Titulo
                self.app.cambiar(Titulo(self.app))
        elif e.type == pygame.KEYDOWN and e.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_SPACE, pygame.K_RETURN):
            self.pag = (self.pag + 1) % len(PAGINAS)
            self.app.son.tocar("mover")
        elif e.type == pygame.KEYDOWN and e.key in (pygame.K_LEFT, pygame.K_a):
            self.pag = (self.pag - 1) % len(PAGINAS)
            self.app.son.tocar("mover")
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in enumerate(self._tabs):
                if r.collidepoint(e.pos):
                    self.pag = i
                    self.app.son.tocar("click")

    def dibujar(self, pant):
        self.fondo.dibujar(pant, 1 / 60)
        texto(pant, "AYUDA", (40, 18), 40, (255, 205, 50), grosor=3)
        self._tabs = []
        x = 200
        for i, nombre in enumerate(PAGINAS):
            img_w = len(nombre) * 10 + 34
            r = pygame.Rect(x, 22, img_w, 40)
            activo = i == self.pag
            pygame.draw.rect(pant, (255, 205, 50) if activo else (46, 38, 90), r, border_radius=12)
            texto(pant, nombre, r.center, 17, TINTA if activo else (240, 240, 250), "center", borde=None if activo else TINTA)
            self._tabs.append(r)
            x += img_w + 8
        caja = panel(pant, (30, 80, ANCHO - 60, ALTO - 140), borde=(255, 205, 50, 90))
        getattr(self, f"_p{self.pag}")(pant, caja)
        pie(pant, "Izquierda/derecha para cambiar de página  ·  ESC para volver", self.app)

    # ------------------------------------------------------------- páginas
    def _p0(self, pant, c):
        texto(pant, "Salva a Ciudad Nova de los Bulos", (c.x + 40, c.y + 30), 34, (255, 205, 50))
        parrafo(pant, "Ciudad Nova va a elegir alcalde y por la red social Civitas corren los BULOS: rumores falsos que se "
                      "suben a la cabeza de los vecinos y los vuelven morados. Atrápalos y cura a los morados antes de que se "
                      "los pasen a sus amigos.", (c.x + 40, c.y + 84), 22, 700, (240, 240, 250))
        items = [(escalar(borde(sprites.bulo(0, False, False, (1, 0))), 3), "Bulo", "Una publicación falsa. Atrápala antes de que llegue a un vecino."),
                 (escalar(borde(sprites.morado(sprites.vecino(1, 0, "abajo", 0))), 3), "Vecino morado", "Se creyó un Bulo. Lánzale tu herramienta para curarlo."),
                 (escalar(borde(sprites.bulo(0, True, False, (1, 0))), 3), "Bulo con corona", "Es la raíz de una cadena: si lo atrapas caen todas sus copias."),
                 (escalar(borde(sprites.estrella()), 3), "Estrella", "Una noticia verdadera. Tócala: protege y cura al vecino y a sus amigos."),
                 (pygame.transform.scale(sprites.antena(), (24, 60)), "Antena del Bot", "Suelta Bulos sin parar. Golpéala varias veces para apagarla.")]
        for k, (img, nombre, desc) in enumerate(items):
            y = c.y + 210 + k * 70
            pant.blit(img, img.get_rect(center=(c.x + 80, y + 20)))
            texto(pant, nombre, (c.x + 130, y), 22, (255, 230, 150))
            texto(pant, desc, (c.x + 130, y + 28), 18, (230, 226, 245), peso=600)
        cs = personajes.cuadros("caro")
        img = pygame.transform.scale(cs["abajo"][int(self.t * 6) % 4], (16 * 10, 24 * 10))
        pant.blit(img, (c.right - 300, c.y + 150))
        texto(pant, "¡Gana quien salve a más vecinos!", (c.right - 220, c.y + 420), 22, (140, 240, 160), "midtop")

    def _p1(self, pant, c):
        # lo mismo que se ve en la cuenta regresiva: el juego en tres dibujos
        instrucciones(pant, (c.centerx, c.y + 118), self.t, teclas=False)
        filas = [("FLECHAS", "Caminar por el barrio (también W A S D)."),
                 ("ESPACIO", "Lanzar tu herramienta (puedes dejarla presionada). Todo se arregla lanzándole: Bulos, morados, la antena y las peleas."),
                 ("X", "Usar el poder de tu personaje cuando el círculo se llena."),
                 ("ESC", "Pausa.  ·  M: silenciar la música.  ·  F11: pantalla completa.")]
        y = c.y + 232
        for t_, d in filas:
            tecla(pant, t_, (c.x + 40, y), 18)
            y = max(y + 44, parrafo(pant, d, (c.x + 200, y + 2), 20, c.w - 260, (240, 240, 250)) + 14)
        r = panel(pant, (c.x + 40, c.y + 424, c.w - 80, 104), (60, 40, 110), 230, borde=(255, 205, 50))
        texto(pant, "Las estrellas", (r.x + 20, r.y + 12), 22, (255, 230, 150))
        parrafo(pant, "Una estrella es una noticia VERDADERA. Con solo tocarla la compartes: la verdad le llega al vecino más "
                      "cercano y a sus amigos por la red social, los cura y los protege un rato (brillan dorado).",
                (r.x + 20, r.y + 44), 19, r.w - 40, (240, 240, 250))
        texto(pant, "¿Con control USB?  Cruceta: caminar  ·  A: lanzar  ·  B o X: poder  ·  Start: pausa",
              (c.centerx, r.bottom + 16), 19, (200, 230, 255), "midtop", 600)

    def _p2(self, pant, c):
        w, sep = 276, 16
        x0 = c.centerx - (4 * w + 3 * sep) // 2
        for k, clave in enumerate(ORDEN):
            r = pygame.Rect(x0 + k * (w + sep), c.y + 20, w, c.h - 40)
            tarjeta_personaje(pant, clave, r, self.t, True, escala=6)

    def _p3(self, pant, c):
        texto(pant, "Cómo se gana", (c.x + 40, c.y + 26), 32, (255, 205, 50))
        filas = [("Atrapar un Bulo", "+10 (más en combo y en cadena)"), ("Curar a un vecino morado", "+15"),
                 ("Cortar un Bulo que viaja por un hilo", "+8"), ("Compartir una estrella", "+20"),
                 ("Calmar una pelea", "+20"), ("Apagar una antena", "+50"), ("Detener el viral", "+60"),
                 ("Cada vecino a salvo al final", "+10")]
        for k, (a, b) in enumerate(filas):
            y = c.y + 80 + k * 36
            texto(pant, a, (c.x + 40, y), 20, (240, 240, 250), peso=600)
            texto(pant, b, (c.x + 560, y), 20, (255, 120, 120) if b.startswith("-") else (140, 240, 160), "topright")
        parrafo(pant, "Cada jugador juega su turno en el MISMO barrio, con los mismos eventos. Al final de todas las rondas gana "
                      "quien sume más puntos.", (c.x + 620, c.y + 80), 20, c.w - 660, (240, 240, 250))
        # estrellas de reputación: cuántos vecinos a salvo hacen falta
        from ..mundo import umbrales_reputacion
        tres, dos = umbrales_reputacion(len(VECINOS))
        r = panel(pant, (c.x + 620, c.y + 170, c.w - 660, 190), (40, 30, 84), 235, borde=(255, 205, 50))
        texto(pant, "Estrellas de reputación", (r.x + 20, r.y + 12), 22, (255, 230, 150))
        filas = [(3, f"{tres} o más vecinos a salvo"), (2, f"{dos} o más vecinos a salvo"), (1, f"menos de {dos}")]
        llena, vacia = escalar(borde(sprites.estrella()), 2), escalar(borde(sprites.desaturar(sprites.estrella())), 2)
        for k, (n, txt) in enumerate(filas):
            y = r.y + 54 + k * 42
            for e in range(3):
                pant.blit(llena if e < n else vacia, (r.x + 20 + e * 36, y))
            texto(pant, txt, (r.x + 140, y + 6), 20, (240, 240, 250), peso=600)
        parrafo(pant, "Después viene la ELECCIÓN: si el barrio terminó informado, gana un candidato con propuestas. Si quedó lleno "
                      "de Bulos, gana Emilio Bot, el de las cadenas.", (c.x + 620, c.y + 384), 20, c.w - 660, (255, 230, 150))

    def _p4(self, pant, c):
        texto(pant, "Los indicadores del barrio", (c.x + 40, c.y + 26), 32, (255, 205, 50))
        desc = {"informacion": "Cuánta gente tiene noticias verificadas. Sube al compartir estrellas.",
                "confianza": "Qué tanto confían los vecinos entre sí. Baja con cada contagio.",
                "convivencia": "Qué tan bien se llevan. Baja si dejas que una pelea rompa una amistad.",
                "bienestar": "Cómo se sienten. Los vecinos con Bulo están tristes y morados.",
                "desinformacion": "Cuántos Bulos hay sueltos y en cabezas. ¡Mejor bajo!",
                "conflictos": "Peleas y amistades rotas. ¡Mejor bajo!"}
        for k, (clave, nombre, color, bueno) in enumerate(INDICADORES):
            y = c.y + 90 + k * 66
            pygame.draw.circle(pant, color, (c.x + 60, y + 18), 16)
            texto(pant, nombre, (c.x + 92, y), 24, color)
            texto(pant, ("Mejor alto. " if bueno else "") + desc[clave], (c.x + 92, y + 32), 18, (230, 226, 245), peso=600)
        parrafo(pant, "Se ven arriba a la derecha mientras juegas. Al final, el promedio de todos los turnos decide la elección.",
                (c.x + 40, c.bottom - 60), 19, c.w - 80, (255, 230, 150))

    def _p5(self, pant, c):
        texto(pant, "Grafo social: quién le pasa el Bulo a quién", (c.x + 30, c.y + 16), 22, (255, 205, 50))
        area = pygame.Rect(c.x + 30, c.y + 50, 560, 400)
        pygame.draw.rect(pant, (20, 16, 44), area, border_radius=12)
        pos, nivel, radios = anillos_bfs(self.social, "Rosa", area)
        paso = int(self.t * 1.2) % 5
        colores = [(255, 90, 150), (255, 160, 70), (255, 220, 80), (140, 220, 140), (120, 180, 255)]
        for n, (rx, ry) in enumerate(radios[1:], start=1):
            caja = pygame.Rect(0, 0, int(rx * 2), int(ry * 2))
            caja.center = area.center
            pygame.draw.ellipse(pant, colores[n] if n <= paso else (50, 44, 84), caja, 1)
        for a, b, p in self.social.aristas():
            pygame.draw.line(pant, (110, 100, 160), pos[a], pos[b], p)
        for v, (x, y) in pos.items():
            n = nivel[v]
            col = colores[min(n, 4)] if n <= paso else (90, 84, 130)
            pygame.draw.circle(pant, TINTA, (int(x), int(y) + 1), 11)
            pygame.draw.circle(pant, col, (int(x), int(y)), 9)
            texto(pant, v, (x, y + 10), 12, (230, 226, 245), "midtop", 600)
        parrafo(pant, f"Recorrido BFS desde Rosa (la más conectada, {self.social.grado('Rosa')} amigos): cada anillo es un nivel. "
                      "Así viaja un Bulo viral: primero a los amigos, luego a los amigos de los amigos.",
                (area.x, area.bottom + 8), 16, area.w, (230, 226, 245))
        texto(pant, "Grafo de la ciudad: la ruta más corta", (c.x + 630, c.y + 16), 22, (255, 205, 50))
        area2 = pygame.Rect(c.x + 630, c.y + 50, 560, 400)
        pygame.draw.rect(pant, (20, 16, 44), area2, border_radius=12)
        pc = {n: (area2.x + 16 + x / 64 * (area2.w - 32), area2.y + 16 + y / 46 * (area2.h - 32)) for n, (x, y) in NODOS.items()}
        for a, b, p in self.ciudad.aristas():
            pygame.draw.line(pant, (110, 100, 160), pc[a], pc[b], 2)
        camino = self.ciudad.camino("Colegio", "Terminal")
        k = int(self.t * 3) % (len(camino) + 3)
        for a, b in zip(camino[:k], camino[1:k]):
            pygame.draw.line(pant, (255, 205, 50), pc[a], pc[b], 5)
        for n, (x, y) in pc.items():
            pygame.draw.circle(pant, (255, 205, 50) if n in camino[:k] else (200, 196, 230), (int(x), int(y)), 5)
        for n in ("Colegio", "Terminal", "Plaza", "Mercado", "Kiosco", "Laguna"):
            x, y = pc[n]
            texto(pant, n, (x, y - 8), 13, (255, 255, 255), "midbottom", 600)
        parrafo(pant, "Dijkstra encuentra el camino más corto por las calles. Lo usa la línea que te guía hacia el viral, una "
                      "pelea o el vecino morado más cercano, y lo usan los vecinos para ir de una zona a otra sin atravesar edificios.",
                (area2.x, area2.bottom + 8), 16, area2.w, (230, 226, 245))

    def _p6(self, pant, c):
        texto(pant, "Árbol de mutaciones de los Bulos", (c.x + 30, c.y + 16), 22, (255, 205, 50))
        area = pygame.Rect(c.x + 30, c.y + 50, 540, 330)
        pygame.draw.rect(pant, (20, 16, 44), area, border_radius=12)
        arbol = [("A", None, 0, 2), ("B", "A", 1, 1), ("C", "A", 1, 3), ("D", "B", 2, 0.5), ("E", "B", 2, 1.5), ("F", "C", 2, 3)]
        pos = {n: (area.x + 60 + x * 130, area.y + 60 + nv * 110) for n, p, nv, x in arbol}
        cae = int(self.t * 2) % 6 >= 3
        for n, p, nv, x in arbol:
            if p:
                pygame.draw.line(pant, (176, 110, 255), pos[p], pos[n], 4)
        for n, p, nv, x in arbol:
            img = escalar(borde(sprites.bulo(int(self.t * 3) % 2, n == "A", False, (0, 1))), 4)
            if not (cae and n in ("B", "D", "E")):
                pant.blit(img, img.get_rect(center=pos[n]))
            else:
                texto(pant, "¡pop!", pos[n], 18, (255, 230, 120), "center")
        parrafo(pant, "Cada vez que un Bulo salta a otro vecino nace un HIJO. Si atrapas un Bulo, caen también todos sus "
                      "descendientes (se elimina el subárbol). La raíz lleva corona: ¡es la que tumba toda la cadena!",
                (area.x, area.bottom + 10), 17, area.w, (230, 226, 245))
        texto(pant, "Árbol de decisiones de cada publicación", (c.x + 620, c.y + 16), 22, (255, 205, 50))
        area2 = pygame.Rect(c.x + 610, c.y + 50, 590, 330)
        pygame.draw.rect(pant, (20, 16, 44), area2, border_radius=12)
        filas = [(n.clave, n.texto, n.veces, n.padre.clave if n.padre else None, n.es_hoja) for n in self.arbol.preorden()]
        dibujar_arbol(pant, filas, area2.inflate(-20, -20), self.t)
        parrafo(pant, "Cada publicación baja por este árbol: si es falsa la REPORTAS atrapándola o la VERIFICAS curando a quien "
                      "se la creyó; si es verdadera la COMPARTES o la IGNORAS. Las hojas cambian los indicadores. Al final del "
                      "turno ves tu propio árbol con los números.",
                (area2.x, area2.bottom + 10), 17, area2.w, (230, 226, 245))

    def _p7(self, pant, c):
        texto(pant, "Jugar con amigos", (c.x + 40, c.y + 26), 32, (255, 205, 50))
        mitad = c.w // 2
        # mismo computador: los turnos pasan de uno a otro
        texto(pant, "Mismo computador (2 a 4)", (c.x + mitad // 2, c.y + 90), 24, (255, 230, 150), "midtop")
        caras = [escalar(borde(personajes.retrato(k)), 4) for k in ORDEN]
        x0 = c.x + mitad // 2 - (4 * 70 + 3 * 34) // 2
        activo = int(self.t * 1.2) % 4
        for k, img in enumerate(caras):
            x = x0 + k * 104
            caja = pygame.Rect(x - 6, c.y + 150, 82, 74)
            pygame.draw.rect(pant, PERSONAJES[ORDEN[k]]["color"] if k == activo else (46, 38, 90), caja, border_radius=12)
            pant.blit(img, img.get_rect(center=caja.center))
            if k < 3:
                texto(pant, "›", (caja.right + 16, caja.centery), 34, (220, 214, 240), "center")
        parrafo(pant, "Cada uno juega su turno y le pasa el teclado al siguiente. En cada ronda todos juegan el MISMO barrio "
                      "con los mismos eventos: así es justo.", (c.x + mitad // 2, c.y + 250), 19, mitad - 80,
                (240, 240, 250), ancla="midtop")
        # en línea: un servidor y varios computadores
        sx = c.x + mitad + mitad // 2
        texto(pant, "En línea (2 a 4 computadores)", (sx, c.y + 90), 24, (255, 230, 150), "midtop")
        srv = pygame.Rect(0, 0, 150, 52)
        srv.center = (sx, c.y + 170)
        clientes = []
        for k in range(3):
            r = pygame.Rect(0, 0, 96, 70)
            r.center = (sx - 170 + k * 170, c.y + 300)
            clientes.append(r)
            fase = (self.t * 0.8 + k * 0.33) % 1.0
            pygame.draw.line(pant, (110, 100, 160), srv.center, r.center, 3)
            px = srv.centerx + (r.centerx - srv.centerx) * fase
            py = srv.centery + (r.centery - srv.centery) * fase
            pygame.draw.circle(pant, (255, 205, 50), (int(px), int(py)), 6)
        pygame.draw.rect(pant, (255, 205, 50), srv, border_radius=12)
        texto(pant, "Servidor", srv.center, 20, TINTA, "center", borde=None)
        for k, r in enumerate(clientes):
            pygame.draw.rect(pant, (46, 38, 90), r, border_radius=12)
            pygame.draw.rect(pant, (200, 196, 230), r, 2, border_radius=12)
            img = escalar(borde(personajes.retrato(ORDEN[k])), 3)
            pant.blit(img, img.get_rect(center=r.center))
        parrafo(pant, "Uno crea la sala y los demás escriben la dirección que aparece. Todos juegan a la vez, ven a los rivales "
                      "como fantasmas y el marcador en vivo.", (sx, c.y + 360), 19, mitad - 80, (240, 240, 250),
                ancla="midtop")
        parrafo(pant, "Nadie depende de otro: cada uno gana por su cuenta salvando a más vecinos.", (c.centerx, c.y + 480), 22,
                c.w - 80, (140, 240, 160), ancla="midtop")

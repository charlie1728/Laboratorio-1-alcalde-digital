"""La simulación de un turno de Cazabulos (sin dibujar nada).

La idea cabe en una frase: los Bulos se suben a la cabeza de los vecinos y los vuelven morados;
tú los atrapas y curas a los morados lanzándoles tu herramienta. Las estrellas son noticias
verdaderas: al recogerlas la verdad les llega al vecino más cercano y a sus amigos.

Un turno = un jugador, un barrio, 2 minutos. Todos los jugadores de una ronda reciben la misma
semilla: los eventos, las estrellas y las antenas salen igual para todos, así la competencia es
justa y nadie depende de lo que haga el otro.
"""
import math
import random

import pygame

from .ciudad import VECINOS, ZONAS_VECINO, grafo_ciudad, grafo_social, ruta
from .config import DURACION_RONDA, TILE, VELOCIDAD_BULO, VELOCIDAD_JUGADOR
from .estructuras.arbol_decision import arbol_publicacion
from .estructuras.arbol_mutaciones import ArbolMutaciones
from .mapa import ANTENAS, NODOS, Mapa
from .trafico import Trafico

CANDIDATOS = ["Lucia", "Marcos", "Elena", "Emilio"]
# Ejemplos de lo que dicen los Bulos (se ven en la ayuda y en la historia, no encima del juego).
RUMORES = ["¡Van a cerrar el colegio!", "Dicen que el alcalde roba", "¡Mañana cierran los parques!",
           "El agua tiene un virus", "Regalan celulares en la plaza", "¡Se cae el puente!"]
ESCUDO = 15.0           # segundos que protege una noticia verdadera
INMUNE = 3.0            # al curarse, un ratito sin que le entren Bulos (con Dani dura mucho más)
MAX_BULOS_LIBRES = 8
MAX_VIRAL = 5           # a cuántos vecinos les llega el viral si no lo detienes
GOLPES_PELEA = 2        # golpes para calmar una pelea (Caro la calma de uno)

ROLES = {
    "ana": {"poder": "Flash", "pasivo": "Ve todos los Bulos en el mapa y su periódico atraviesa varios",
            "poder_txt": "Congela a todos los Bulos de la pantalla"},
    "beto": {"poder": "En vivo", "pasivo": "Cuando cura a alguien, la cura les llega también a sus amigos",
             "poder_txt": "Protege a todos los vecinos de la pantalla"},
    "caro": {"poder": "Red gigante", "pasivo": "Corre más rápido, su red es más ancha y calma peleas de un golpe",
             "poder_txt": "Atrapa de un golpe todos los Bulos cercanos"},
    "dani": {"poder": "Discurso", "pasivo": "A quien cura no le vuelven a entrar Bulos por un buen rato",
             "poder_txt": "Cura a los vecinos cercanos y empuja a los Bulos"},
}

_mapa_cache = None


def mapa_compartido():
    """El mapa y su grafo de calles se construyen una sola vez."""
    global _mapa_cache
    if _mapa_cache is None:
        m = Mapa()
        _mapa_cache = (m, grafo_ciudad(m))
    return _mapa_cache


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


# ----------------------------------------------------------------- entidades
class Vecino:
    def __init__(self, nombre, tipo, variante, zona, pos):
        self.nombre = nombre
        self.tipo = tipo
        self.variante = variante
        self.zona = zona
        self.x, self.y = pos[0] * TILE + 8, pos[1] * TILE + 14
        self.dir = "abajo"
        self.mov = False
        self.paso = 0.0
        self.escudo = 0.0          # segundos protegido por la verdad (no le entran Bulos)
        self.bulo = None           # id del Bulo que tiene en la cabeza (está "morado")
        self.t_prop = 0.0          # tiempo para pasarle el Bulo a un amigo
        self.ruta = []
        self.espera = 0.0
        self.pelea = None
        self.triste = 0.0
        self.salto = 0.0           # animación al recibir algo

    @property
    def pos(self):
        return (self.x, self.y)

    @property
    def cabeza(self):
        return (self.x, self.y - 19)

    @property
    def cuerpo(self):
        return (self.x, self.y - 10)

    def rect(self):
        return pygame.Rect(int(self.x) - 4, int(self.y) - 3, 8, 4)


class Bulo:
    def __init__(self, ident, x, y, estado="libre", candidato=None):
        self.id = ident
        self.x, self.y = x, y
        self.estado = estado       # libre, cabeza
        self.vecino = None
        self.objetivo = None
        self.t = (ident * 0.37) % 6       # fase del bamboleo: fija, para que la misma semilla dé lo mismo
        self.congelado = 0.0
        self.aturdido = 0.0
        self.candidato = candidato
        self.vx = self.vy = 0.0
        self.reenvios = 0

    @property
    def pos(self):
        return (self.x, self.y)


class Pulso:
    """Un Bulo que viaja por un hilo del grafo social de un vecino a otro."""

    def __init__(self, padre, desde, hasta, dur):
        self.padre = padre
        self.desde = desde
        self.hasta = hasta
        self.f = 0.0
        self.dur = dur
        self.congelado = 0.0


class Estrella:
    """Una noticia verdadera. Al tocarla se comparte sola."""

    def __init__(self, ident, x, y):
        self.id = ident
        self.x, self.y = x, y
        self.vida = 22.0
        self.t = 0.0


class Antena:
    def __init__(self, x, y, vida):
        self.x, self.y = x, y
        self.vida = vida
        self.vida_max = vida
        self.t = 2.5
        self.golpe = 0.0

    def rect(self):
        return pygame.Rect(int(self.x) - 7, int(self.y) - 30, 14, 30)


class Viral:
    def __init__(self, x, y, objetivo):
        self.x, self.y = x, y
        self.objetivo = objetivo
        self.vida = 3
        self.t = 10.0
        self.golpe = 0.0
        self.congelado = 0.0


class Proyectil:
    def __init__(self, x, y, vx, vy, color, clave="caro", vida=0.5, radio=10, perfora=1):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.vida = vida
        self.vida0 = vida
        self.color = color
        self.clave = clave
        self.radio = radio
        self.perfora = perfora     # a cuántas cosas puede darle antes de desaparecer (Ana: varias)
        self.golpeados = set()
        self.rastro = []


class Jugador:
    def __init__(self, clave, x, y, piel=None, pelo=None):
        self.clave = clave
        self.piel, self.pelo = piel, pelo
        self.x, self.y = x, y
        self.dir = "abajo"
        self.vec = (0.0, 1.0)
        self.mov = False
        self.paso = 0.0
        self.puntos = 0
        self.combo = 0
        self.t_combo = 0.0
        self.carga = 0.0
        self.enfriar = 0.0
        self.lanzo = 0.0
        self.poder_t = 0.0
        self.stats = {"bulos": 0, "cadena": 0, "antenas": 0, "compartidas": 0, "peleas": 0, "viral": 0,
                      "curados": 0, "pulsos": 0, "regados": 0, "combo_max": 0, "poderes": 0}

    @property
    def pos(self):
        return (self.x, self.y)

    def rect(self, x=None, y=None):
        x = self.x if x is None else x
        y = self.y if y is None else y
        return pygame.Rect(int(x) - 5, int(y) - 4, 10, 5)


# ----------------------------------------------------------------- el mundo
class Mundo:
    def __init__(self, semilla, personaje="caro", duracion=DURACION_RONDA, tranquilo=False, ronda=1,
                 piel=None, pelo=None, pistas=True):
        self.semilla = semilla
        self.mapa, self.ciudad = mapa_compartido()
        self.social = grafo_social()
        self.arbol = ArbolMutaciones()
        self.decisiones = arbol_publicacion()
        self.trafico = Trafico(semilla)
        self.rng = random.Random(semilla * 7919 + ronda)      # eventos (igual para todos)
        self.azar = random.Random(semilla * 31 + 5)           # detalles que no cambian la competencia
        self.duracion = duracion
        self.tiempo = float(duracion)
        self.t = 0.0
        self.tranquilo = tranquilo
        self.ronda = ronda
        self.pistas_on = pistas
        self.terminado = False
        self.fx = []
        self.vecinos = {}
        for nombre, tipo, var, zona, pos in VECINOS:
            v = Vecino(nombre, tipo, var, zona, pos)
            v.espera = self.azar.uniform(0, 2)
            self.vecinos[nombre] = v
        sx, sy = NODOS["Cebra plaza"]
        self.jugador = Jugador(personaje, sx * TILE, sy * TILE + 2, piel, pelo)
        self.bulos = {}
        self.pulsos = []
        self.estrellas = []
        self.proyectiles = []
        self.peleas = []
        self.viral = None
        self.antenas = []
        self.pasaron = set()      # Bulos que ya se pasaron a un amigo (para el árbol al final)
        self._sig_id = 1
        self.rumores = {c: 0 for c in CANDIDATOS}
        self.defendidos = {c: 0 for c in CANDIDATOS}
        self.ind = {"informacion": 50.0, "confianza": 55.0, "convivencia": 70.0, "bienestar": 65.0,
                    "desinformacion": 18.0, "conflictos": 8.0}
        self.rotos = []           # hilos que se rompieron por peleas
        self.nuevos = []          # hilos nuevos por campañas
        self.pistas_vistas = set()
        self.pista = None
        self._preparar_guion()

    # ------------------------------------------------------------- guion de la ronda (igual para todos)
    def _preparar_guion(self):
        r = self.rng
        d = self.duracion
        self.orden_antenas = r.sample(range(len(ANTENAS)), len(ANTENAS))
        self.k_antena = 0
        self.t_antena = 3.0
        # cada ronda es un poco más difícil: la antena suelta Bulos más seguido y en la noche hay dos
        self.ritmo_ronda = {1: 1.0, 2: 0.9}.get(self.ronda, 0.85)
        self.kiosco = [(r.uniform(-30, 30), r.uniform(-6, 18)) for _ in range(40)]
        self.k_kiosco = 0
        self.t_kiosco = 6.0
        tipos = ["pelea", "verdad", "rumor", "reporte", "falsa", "campana", "pelea", "verdad", "rumor"]
        r.shuffle(tipos)
        self.guion = []
        t = 16.0
        for tipo in tipos:
            if t > d - 10:
                break
            self.guion.append([t, tipo, r.random()])
            t += r.uniform(13, 18)
        self.guion.append([d * r.uniform(0.4, 0.55), "viral", r.random()])
        if self.ronda >= 3 or d >= 150:
            self.guion.append([d * (0.45 if self.ronda >= 3 else 0.7), "antena2", r.random()])
        self.guion.sort()
        puntos = []
        while len(puntos) < 40:
            x, y = r.uniform(2, 62) * TILE, r.uniform(7, 44) * TILE
            if self.mapa.libre(pygame.Rect(int(x) - 6, int(y) - 6, 12, 10)) and not self.mapa.es_calzada(x, y):
                puntos.append((x, y))
        self.puntos_sueltos = puntos
        self.k_suelto = 0

    def _id(self):
        self._sig_id += 1
        return self._sig_id

    def _punto_suelto(self):
        p = self.puntos_sueltos[self.k_suelto % len(self.puntos_sueltos)]
        self.k_suelto += 1
        return p

    # ------------------------------------------------------------- efectos para la pantalla
    def emitir(self, *fx):
        self.fx.append(fx)

    def texto(self, x, y, s, color=(255, 255, 255), grande=False):
        self.emitir("texto", x, y, s, color, grande)

    def aviso(self, palabra, color=(255, 205, 50)):
        """Una o dos palabras grandes arriba de la pantalla (nunca párrafos encima del juego)."""
        self.emitir("aviso", palabra, color)

    def sonar(self, nombre, x=None, y=None):
        self.emitir("sonido", nombre, x, y)

    def mostrar_pista(self, clave, texto):
        if not self.pistas_on or clave in self.pistas_vistas:
            return
        self.pistas_vistas.add(clave)
        self.pista = [texto, (), 3.5]

    def sumar(self, puntos, x, y):
        j = self.jugador
        j.puntos += puntos
        if puntos:
            color = (255, 230, 90) if puntos > 0 else (255, 110, 110)
            self.texto(x, y - 10, f"{'+' if puntos > 0 else ''}{puntos}", color)

    def ajustar(self, **cambios):
        for k, v in cambios.items():
            if k in self.ind:
                self.ind[k] = max(0.0, min(100.0, self.ind[k] + v))

    def cargar(self, n):
        j = self.jugador
        antes = j.carga
        j.carga = min(100.0, j.carga + n)
        if antes < 100 <= j.carga:
            self.sonar("listo")

    def _hoja(self, camino, x=None, y=None):
        """Baja por el árbol de decisiones de la publicación y aplica las consecuencias de la hoja."""
        hoja = self.decisiones.recorrer(camino)
        ef = hoja.efecto
        if ef.get("puntos") and x is not None:
            self.sumar(ef["puntos"], x, y)
        self.ajustar(**{k: v for k, v in ef.items() if k != "puntos"})
        return hoja

    # ------------------------------------------------------------- consultas
    def infectados(self):
        return [v for v in self.vecinos.values() if v.bulo is not None]

    def salvados(self):
        return sum(1 for v in self.vecinos.values() if v.bulo is None)

    def bulos_libres(self):
        return [b for b in self.bulos.values() if b.estado == "libre"]

    def indicadores(self):
        """Los 6 indicadores de la ciudad: lo acumulado más lo que se ve ahora en el barrio."""
        n = len(self.vecinos)
        inf = len(self.infectados()) / n
        prot = sum(1 for v in self.vecinos.values() if v.escudo > 0) / n
        peleas = sum(1 for p in self.peleas if not p.get("fin"))
        res = dict(self.ind)
        res["desinformacion"] = self.ind["desinformacion"] + 55 * inf + 1.5 * len(self.bulos_libres())
        res["informacion"] = self.ind["informacion"] + 25 * prot - 10 * inf
        res["bienestar"] = self.ind["bienestar"] - 30 * inf
        res["conflictos"] = self.ind["conflictos"] + 14 * peleas + 6 * len(self.rotos)
        res["convivencia"] = self.ind["convivencia"] - 8 * peleas
        res["confianza"] = self.ind["confianza"] - 15 * inf
        return {k: int(max(0, min(100, v))) for k, v in res.items()}

    # ------------------------------------------------------------- bucle principal
    def actualizar(self, dt, entrada):
        if self.terminado:
            return
        dt = min(dt, 0.05)
        self.t += dt
        self.tiempo -= dt
        if self.pista:
            self.pista[2] -= dt
            if self.pista[2] <= 0:
                self.pista = None
        self._jugador(dt, entrada)
        self._vecinos(dt)
        self._bulos(dt)
        self._pulsos(dt)
        self._proyectiles(dt)
        self._estrellas(dt)
        self._antenas(dt)
        self._viral(dt)
        self._peleas(dt)
        self._guion(dt)
        peatones = [self.jugador.rect()] + [v.rect() for v in self.vecinos.values()]
        self.trafico.actualizar(dt, peatones)
        for c in self.trafico.carros:
            if c.pito == 0.6:
                r = c.rect()
                self.sonar("pito", r.centerx, r.centery)
        if self.tiempo <= 10 and int(self.tiempo + dt) != int(self.tiempo) and self.tiempo > 0:
            self.sonar("tic")
        if self.tiempo <= 0:
            self.tiempo = 0
            self._cerrar()

    # ------------------------------------------------------------- jugador
    def _jugador(self, dt, e):
        j = self.jugador
        dx = (1 if e.get("der") else 0) - (1 if e.get("izq") else 0)
        dy = (1 if e.get("abajo") else 0) - (1 if e.get("arriba") else 0)
        vel = VELOCIDAD_JUGADOR * (1.22 if j.clave == "caro" else 1.0)
        j.mov = bool(dx or dy)
        if j.mov:
            n = math.hypot(dx, dy)
            j.vec = (dx / n, dy / n)
            if abs(dx) >= abs(dy) and dx:
                j.dir = "der" if dx > 0 else "izq"
            else:
                j.dir = "abajo" if dy > 0 else "arriba"
            self._mover(j, j.vec[0] * vel * dt, j.vec[1] * vel * dt)
            j.paso += dt * 9
        else:
            j.paso = 0
        j.enfriar = max(0.0, j.enfriar - dt)
        j.lanzo = max(0.0, j.lanzo - dt)
        j.poder_t = max(0.0, j.poder_t - dt)
        j.t_combo -= dt
        if j.t_combo <= 0:
            j.combo = 0
        # tocar una estrella = compartir una noticia verdadera
        for s in list(self.estrellas):
            if math.hypot(s.x - j.x, s.y - (j.y - 6)) < 15:
                self.estrellas.remove(s)
                self._compartir(s)
        if e.get("accion") and j.enfriar <= 0:
            self._lanzar()
        if e.get("poder"):
            self._poder()

    def _mover(self, ent, mx, my):
        m = self.mapa
        carros = self.trafico.rects()
        for paso_x, paso_y in ((mx, 0), (0, my)):
            if not paso_x and not paso_y:
                continue
            nx, ny = ent.x + paso_x, ent.y + paso_y
            r = ent.rect(nx, ny)
            if m.libre(r) and r.collidelist(carros) == -1:
                ent.x, ent.y = nx, ny
                continue
            # deslizar en las esquinas (hasta 5 px) para no quedar trabado
            for empuje in (1, 2, 3, 4, 5):
                hecho = False
                for s in (1, -1):
                    ox, oy = (0, s * empuje) if paso_x else (s * empuje, 0)
                    r2 = ent.rect(nx + ox, ny + oy)
                    if m.libre(r2) and r2.collidelist(carros) == -1:
                        ent.x, ent.y = nx + ox * 0.4, ny + oy * 0.4
                        if not m.libre(ent.rect()):
                            ent.x, ent.y = nx + ox, ny + oy
                        hecho = True
                        break
                if hecho:
                    break

    def _lanzar(self):
        """Lanza la herramienta del personaje. Cada uno lanza distinto (ver ROLES)."""
        j = self.jugador
        j.enfriar = {"ana": 0.22, "beto": 0.34}.get(j.clave, 0.28)
        j.lanzo = 0.18
        ox, oy = j.x + j.vec[0] * 6, j.y - 12 + j.vec[1] * 4
        vx, vy = j.vec
        vel, vida, radio, perfora, alcance = 240, 0.5, 10, 1, 135
        if j.clave == "ana":            # el periódico sale rápido, vuela lejos y atraviesa
            vel, vida, radio, perfora, alcance = 290, 0.62, 12, 3, 175
        elif j.clave == "beto":         # los corazones flotan más despacio
            vel, vida = 200, 0.52
        elif j.clave == "caro":         # la red es ancha
            radio = 18
        # un poco de puntería automática: busca el blanco más cercano frente al jugador
        mejor, dmin = None, alcance
        for pos in self._blancos():
            d = _dist(pos, (ox, oy))
            if 4 < d < dmin:
                ang = math.atan2(pos[1] - oy, pos[0] - ox) - math.atan2(vy, vx)
                ang = (ang + math.pi) % (2 * math.pi) - math.pi
                if abs(ang) < math.radians(38):
                    mejor, dmin = pos, d
        if mejor:
            d = _dist(mejor, (ox, oy))
            vx, vy = (mejor[0] - ox) / d, (mejor[1] - oy) / d
        from .personajes import PERSONAJES
        self.proyectiles.append(Proyectil(ox, oy, vx * vel, vy * vel, PERSONAJES[j.clave]["color"], j.clave,
                                          vida, radio, perfora))
        self.sonar("lanzar")

    def _blancos(self):
        """Todo lo que se arregla lanzándole algo."""
        res = [b.pos for b in self.bulos.values() if b.estado == "libre"]
        res += [self.vecinos[b.vecino].cuerpo for b in self.bulos.values() if b.estado == "cabeza"]
        res += [self._pos_pulso(p) for p in self.pulsos]
        res += [(a.x, a.y - 18) for a in self.antenas]
        if self.viral:
            res.append((self.viral.x, self.viral.y - 10))
        res += [self._pos_pelea(p) for p in self.peleas if p.get("activa") and not p.get("fin")]
        return res

    def _compartir(self, s):
        """Recoger una estrella es compartir una noticia verdadera: le llega al vecino más cercano y a sus
        amigos por la red social (BFS de 1 nivel; con Beto, el influencer, 2 niveles). A quien tenía un
        Bulo lo cura y a todos los protege un rato."""
        j = self.jugador
        self._hoja(["verdadera", "compartir"], s.x, s.y - 10)
        j.stats["compartidas"] += 1
        origen = min(self.vecinos.values(), key=lambda v: _dist(v.pos, j.pos))
        niveles = 2 if j.clave == "beto" else 1
        dur = ESCUDO * (1.6 if j.clave == "dani" else 1.0)
        alcanzados = 0
        for u, nivel, padre in self.social.bfs(origen.nombre, max_nivel=niveles):
            w = self.vecinos[u]
            if w.bulo is not None and w.bulo in self.bulos:
                self._atrapar(w.bulo)
            w.escudo = max(w.escudo, dur * (1.0 if nivel == 0 else 0.75))
            w.salto = 0.4
            alcanzados += 1
            self.emitir("ola", u, nivel, (255, 214, 70))
            if padre is not None:
                self.emitir("hilo", padre, u, (255, 220, 80))
        self.ajustar(informacion=0.5 * alcanzados)
        self.emitir("verdad", s.x, s.y, origen.nombre)
        self.sonar("entregar")
        self.cargar(14)

    def _calmar(self, p):
        j = self.jugador
        p["fin"] = "paz"
        a, b = self.vecinos[p["a"]], self.vecinos[p["b"]]
        a.pelea = b.pelea = None
        if self.social.tiene_arista(a.nombre, b.nombre):
            self.social.agregar_arista(a.nombre, b.nombre, min(3, self.social.peso(a.nombre, b.nombre) + 1))
        else:
            self.social.agregar_arista(a.nombre, b.nombre, 1)
        j.stats["peleas"] += 1
        self.sumar(20, (a.x + b.x) / 2, (a.y + b.y) / 2 - 20)
        self.ajustar(convivencia=8, conflictos=-4, bienestar=3)
        self.emitir("corazones", (a.x + b.x) / 2, (a.y + b.y) / 2 - 22)
        self.emitir("hilo", a.nombre, b.nombre, (120, 230, 140))
        self.sonar("paz")
        self.cargar(15)
        if j.clave == "caro":
            a.escudo = max(a.escudo, ESCUDO)
            b.escudo = max(b.escudo, ESCUDO)

    def _poder(self):
        j = self.jugador
        if j.carga < 100:
            return
        j.carga = 0
        j.poder_t = 0.8
        j.stats["poderes"] += 1
        c = j.clave
        self.emitir("poder", c, j.x, j.y)
        self.sonar("poder")
        nombre = ROLES[c]["poder"].upper()
        if c == "ana":
            for b in self.bulos.values():
                if b.estado == "libre" and _dist(b.pos, j.pos) < 240:
                    b.congelado = 6.0
            for p in self.pulsos:
                p.congelado = 6.0
            if self.viral and _dist((self.viral.x, self.viral.y), j.pos) < 240:
                self.viral.congelado = 3.0
        elif c == "beto":
            n = 0
            for v in self.vecinos.values():
                if _dist(v.pos, j.pos) < 230:
                    v.escudo = max(v.escudo, 10.0)
                    v.salto = 0.4
                    n += 1
            self.sumar(4 * n, j.x, j.y - 30)
            self.ajustar(informacion=n, confianza=2)
        elif c == "caro":
            for b in list(self.bulos.values()):
                if b.id in self.bulos and b.estado == "libre" and _dist(b.pos, j.pos) < 120:
                    self._atrapar(b.id)
            for p in list(self.pulsos):
                if _dist(self._pos_pulso(p), j.pos) < 120:
                    self.pulsos.remove(p)
            if self.viral and _dist((self.viral.x, self.viral.y), j.pos) < 120:
                self._golpe_viral(2)
        elif c == "dani":
            for v in self.vecinos.values():
                if v.bulo is not None and _dist(v.pos, j.pos) < 110 and v.bulo in self.bulos:
                    self._atrapar(v.bulo)
            for b in self.bulos.values():
                if b.estado == "libre":
                    d = _dist(b.pos, j.pos)
                    if 0 < d < 130:
                        b.vx += (b.x - j.x) / d * 140
                        b.vy += (b.y - j.y) / d * 140
                        b.aturdido = 1.5
            self.ajustar(confianza=4)
        self.texto(j.x, j.y - 40, f"¡{nombre}!", (255, 250, 210), True)

    # ------------------------------------------------------------- vecinos
    def _vecinos(self, dt):
        for v in self.vecinos.values():
            v.escudo = max(0.0, v.escudo - dt)
            v.salto = max(0.0, v.salto - dt)
            v.triste = max(0.0, v.triste - dt)
            if v.bulo is not None:
                v.t_prop -= dt
                if v.t_prop <= 0:
                    self._reenviar(v)
            if v.pelea and v.pelea.get("activa"):
                v.mov = False
                otro = self.vecinos[v.pelea["b"] if v.pelea["a"] == v.nombre else v.pelea["a"]]
                v.dir = "der" if otro.x > v.x else "izq"
                continue
            if v.espera > 0:
                v.espera -= dt
                v.mov = False
                continue
            if not v.ruta:
                self._nuevo_destino(v)
                continue
            tx, ty = v.ruta[0]
            d = _dist((tx, ty), v.pos)
            vel = 24 if v.bulo is None else 17
            if v.pelea:
                vel = 34
            if d < 2:
                v.ruta.pop(0)
                if not v.ruta:
                    v.espera = self.azar.uniform(1.0, 4.0)
                continue
            mx, my = (tx - v.x) / d * vel * dt, (ty - v.y) / d * vel * dt
            if abs(mx) > abs(my):
                v.dir = "der" if mx > 0 else "izq"
            else:
                v.dir = "abajo" if my > 0 else "arriba"
            nx, ny = v.x + mx, v.y + my
            r = pygame.Rect(int(nx) - 4, int(ny) - 3, 8, 4)
            carros = self.trafico.rects()
            if self.mapa.libre(r) and r.collidelist(carros) == -1:
                v.x, v.y = nx, ny
                v.mov = True
                v.paso += dt * 7
            else:
                v.mov = False
                if r.collidelist(carros) == -1:
                    v.ruta = []
                    v.espera = 0.5

    def _nuevo_destino(self, v):
        if v.pelea:
            otro = self.vecinos[v.pelea["b"] if v.pelea["a"] == v.nombre else v.pelea["a"]]
            v.ruta = ruta(self.ciudad, self.mapa, v.pos, (otro.x - 10 if otro.x > v.x else otro.x + 10, otro.y))
            return
        if self.azar.random() < 0.12:
            v.zona = self.azar.choice(list(ZONAS_VECINO))
        x0, y0, x1, y1 = ZONAS_VECINO[v.zona]
        for _ in range(12):
            p = (self.azar.uniform(x0, x1) * TILE + 8, self.azar.uniform(y0, y1) * TILE + 8)
            if self.mapa.libre(pygame.Rect(int(p[0]) - 5, int(p[1]) - 4, 10, 6)):
                v.ruta = ruta(self.ciudad, self.mapa, v.pos, p)
                return
        v.espera = 1.0

    def _espera_reenvio(self, v):
        """Cuánto tarda un vecino morado en pasarle el Bulo a un amigo: los más conectados, más rápido."""
        return max(7.5, 14.0 - 0.7 * self.social.grado(v.nombre)) * (1.4 if self.tranquilo else 1.0)

    def _reenviar(self, v):
        """El vecino con Bulo se lo pasa a un amigo por un hilo del grafo social."""
        v.t_prop = self._espera_reenvio(v)
        b = self.bulos.get(v.bulo)
        if b is None or b.reenvios >= 1:      # cada Bulo se reenvía una sola vez (la cadena crece en fila)
            return
        opciones = [(u, p) for u, p in self.social.vecinos(v.nombre).items()
                    if self.vecinos[u].bulo is None and self.vecinos[u].escudo <= 0
                    and not any(pl.hasta == u for pl in self.pulsos)]
        if not opciones:
            return
        mayor = max(p for _, p in opciones)
        u = self.azar.choice([u for u, p in opciones if p == mayor])
        dist = _dist(v.pos, self.vecinos[u].pos)
        b.reenvios += 1
        self.pulsos.append(Pulso(v.bulo, v.nombre, u, max(2.4, min(4.2, dist / 70))))
        self.sonar("reenvio", v.x, v.y)

    # ------------------------------------------------------------- Bulos
    def nuevo_bulo(self, x, y, padre=None, candidato=None):
        b = Bulo(self._id(), x, y, candidato=candidato)
        if padre is None:
            self.arbol.crear_raiz(b.id, origen="antena")
        else:
            self.arbol.insertar(b.id, padre)
        self.bulos[b.id] = b
        return b

    def _volver_morado(self, v, b):
        """El vecino se creyó el Bulo: lo tiene en la cabeza y se pone morado."""
        b.estado = "cabeza"
        b.vecino = v.nombre
        v.bulo = b.id
        v.t_prop = self._espera_reenvio(v)
        v.triste = 2.0
        v.salto = 0.3
        self.ajustar(confianza=-1.5, bienestar=-1)
        if b.candidato:
            self.rumores[b.candidato] += 1
        self.emitir("contagio", v.x, v.y - 22)
        self.sonar("contagio", v.x, v.y)
        self.mostrar_pista("morado", "¡Lánzale al morado para curarlo!")

    def _infectar(self, v, padre):
        """Le sube un Bulo nuevo a la cabeza (hijo de 'padre' en el árbol de mutaciones)."""
        if v.bulo is not None:
            return None
        b = self.nuevo_bulo(v.x, v.y - 19, padre)
        self._volver_morado(v, b)
        return b.id

    def _bulos(self, dt):
        j = self.jugador
        vel_base = VELOCIDAD_BULO * (0.72 if self.tranquilo else 1.0)
        for b in list(self.bulos.values()):
            b.t += dt
            if b.estado == "cabeza":
                v = self.vecinos.get(b.vecino)
                if v:
                    b.x, b.y = v.cabeza
                continue
            if b.congelado > 0:
                b.congelado -= dt
                if _dist(b.pos, (j.x, j.y - 10)) < 12:
                    self._atrapar(b.id)
                continue
            if b.aturdido > 0:
                b.aturdido -= dt
                b.x += b.vx * dt
                b.y += b.vy * dt
                b.vx *= 0.9
                b.vy *= 0.9
                continue
            obj = self.vecinos.get(b.objetivo)
            if obj is None or obj.bulo is not None or obj.escudo > 0:
                obj = self._elegir_objetivo(b)
                b.objetivo = obj.nombre if obj else None
            if obj is None:
                tx, ty = b.x + math.cos(b.t) * 20, b.y + math.sin(b.t * 0.7) * 20
            else:
                tx, ty = obj.cabeza
            d = _dist((tx, ty), b.pos)
            if obj is not None and d < 8:
                if obj.escudo > 0:
                    self._rebote(b)
                else:
                    self._volver_morado(obj, b)
                continue
            vx, vy = ((tx - b.x) / d, (ty - b.y) / d) if d > 0 else (0, 0)
            # esquiva al jugador cuando lo tiene cerca
            dj = _dist(b.pos, (j.x, j.y - 10))
            huida = 0.0
            if 0 < dj < 46:
                px_, py_ = -(j.y - 10 - b.y) / dj, (j.x - b.x) / dj
                lado = 1 if (b.id % 2) else -1
                vx += px_ * 0.7 * lado
                vy += py_ * 0.7 * lado
                huida = 14
            ondula = math.sin(b.t * 5) * 0.35
            vx, vy = vx - vy * ondula, vy + vx * ondula
            n = math.hypot(vx, vy) or 1
            vel = vel_base + huida
            b.x += vx / n * vel * dt
            b.y += vy / n * vel * dt
            b.x = max(4, min(self.mapa.superficie.get_width() - 4, b.x))
            b.y = max(8, min(self.mapa.superficie.get_height() - 4, b.y))

    def _elegir_objetivo(self, b):
        """Los Bulos buscan a los vecinos con más amigos (más grado en el grafo social)."""
        mejor, puntaje = None, -1e9
        for v in self.vecinos.values():
            if v.bulo is not None or v.escudo > 0:
                continue
            d = _dist(v.pos, b.pos)
            p = self.social.grado(v.nombre) * 45 - d
            if p > puntaje:
                mejor, puntaje = v, p
        return mejor

    def _rebote(self, b):
        """El vecino protegido por la verdad no se lo cree: el Bulo revienta."""
        v = self.vecinos[b.objetivo]
        self.emitir("pop", b.x, b.y, (255, 220, 90))
        v.salto = 0.3
        self._hoja(["falsa", "atrapar"])
        self.sumar(5, v.x, v.y - 30)
        self.arbol.eliminar_subarbol(b.id)
        self.bulos.pop(b.id, None)

    def _atrapar(self, ident, puntos=True):
        """Atrapa un Bulo y todo su subárbol de mutaciones (si era la raíz, cae toda la cadena).
        Atrapar uno libre es REPORTARLO; quitárselo de la cabeza a un vecino es VERIFICAR (se cura).
        puntos=False: la cura llegó sola (la cadena de Beto) y no suma puntos ni combo."""
        if ident not in self.arbol:
            return 0
        j = self.jugador
        ids = self.arbol.eliminar_subarbol(ident)
        cadena = []
        extra = 0
        for i in ids:
            b = self.bulos.pop(i, None)
            if b is None:
                continue
            if b.estado == "cabeza":
                v = self.vecinos.get(b.vecino)
                if v:
                    v.bulo = None
                    v.salto = 0.4
                    v.escudo = max(v.escudo, INMUNE * (5 if j.clave == "dani" else 1))
                    j.stats["curados"] += 1
                    self._hoja(["falsa", "llega", "curar"])
                    extra += 7 if j.clave == "dani" else 5       # el candidato gana confianza al curar
            else:
                self._hoja(["falsa", "atrapar"])
                if j.clave == "ana":
                    extra += 5          # la periodista detecta las publicaciones falsas antes de que lleguen
            if b.candidato:
                self.defendidos[b.candidato] += 1
                if j.clave == "dani":
                    extra += 10          # el candidato enfrenta los rumores sobre los candidatos
            cadena.append(b.pos)
        # los reenvíos que venían de esos Bulos también se cortan
        self.pulsos = [p for p in self.pulsos if p.padre in self.arbol]
        if not cadena:
            return 0
        if not puntos:
            self.sumar(12 * len(cadena), *cadena[0])
            self.emitir("cadena", cadena)
            self.sonar("pop", *cadena[0])
            return len(cadena)
        j.combo += 1
        j.t_combo = 2.5
        j.stats["combo_max"] = max(j.stats["combo_max"], j.combo)
        mult = 1 + min(3, (j.combo - 1) // 4)
        n = len(cadena)
        j.stats["bulos"] += n
        j.stats["cadena"] = max(j.stats["cadena"], n)
        puntos = (10 * n + 5 * (n - 1) + extra) * mult
        x, y = cadena[0]
        self.sumar(puntos, x, y)
        self.emitir("cadena", cadena)
        self.sonar("pop" if n == 1 else "cadena", x, y)
        if n >= 3:
            self.emitir("temblor", 4)
            self.aviso(f"¡CADENA DE {n}!", (200, 160, 255))
        self.cargar(9 + 3 * n)
        return n

    def _cura_en_cadena(self, v):
        """Beto (influencer): cuando cura a alguien, la cura les llega también a sus amigos (BFS de 1 nivel)."""
        for u, nivel, padre in self.social.bfs(v.nombre, max_nivel=1)[1:]:
            w = self.vecinos[u]
            if w.bulo is not None and w.bulo in self.bulos:
                self._atrapar(w.bulo, puntos=False)
            w.escudo = max(w.escudo, 5.0)
            self.emitir("hilo", v.nombre, u, (255, 150, 200))
            self.emitir("ola", u, 1, (255, 150, 200))

    def _pos_pulso(self, p):
        a, b = self.vecinos[p.desde], self.vecinos[p.hasta]
        (x0, y0), (x1, y1) = a.cabeza, b.cabeza
        f = p.f
        return (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f - math.sin(f * math.pi) * 14)

    def _pulsos(self, dt):
        for p in list(self.pulsos):
            if p.congelado > 0:
                p.congelado -= dt
                continue
            p.f += dt / p.dur
            if p.f >= 1:
                self.pulsos.remove(p)
                u = self.vecinos[p.hasta]
                if u.escudo > 0:
                    self.emitir("pop", u.x, u.y - 22, (255, 220, 90))
                    continue
                if u.bulo is None and p.padre in self.arbol:
                    self._infectar(u, p.padre)
                    self.pasaron.add(p.padre)
                    self._hoja(["falsa", "llega", "pasar"])
                    self.jugador.stats["regados"] += 1

    # ------------------------------------------------------------- proyectiles
    def _proyectiles(self, dt):
        for pr in list(self.proyectiles):
            pr.rastro.append((pr.x, pr.y))
            pr.rastro = pr.rastro[-5:]
            pr.x += pr.vx * dt
            pr.y += pr.vy * dt
            pr.vida -= dt
            if self._impacto(pr):
                pr.perfora -= 1
            fuera = not (0 <= pr.x < self.mapa.superficie.get_width() and 0 <= pr.y < self.mapa.superficie.get_height())
            if pr.perfora <= 0 or pr.vida <= 0 or fuera:
                self.proyectiles.remove(pr)
                if pr.perfora > 0:
                    self.emitir("puff", pr.x, pr.y)

    def _impacto(self, pr):
        """¿Le dio a algo? Bulos libres, vecinos morados (en cualquier parte del cuerpo), reenvíos en
        el aire, antenas, el viral y las peleas: todo se arregla lanzándole."""
        j = self.jugador
        punto = (pr.x, pr.y)
        r = pr.radio
        for b in list(self.bulos.values()):
            if b.estado == "libre":
                if _dist(b.pos, punto) < r:
                    self._atrapar(b.id)
                    return True
            else:
                v = self.vecinos.get(b.vecino)
                if v and (_dist(v.cabeza, punto) < r or _dist(v.cuerpo, punto) < r + 3):
                    self._atrapar(b.id)
                    if j.clave == "beto":
                        self._cura_en_cadena(v)
                    return True
        for p in list(self.pulsos):
            if _dist(self._pos_pulso(p), punto) < r:
                self.pulsos.remove(p)
                j.stats["pulsos"] += 1
                self._hoja(["falsa", "atrapar"])
                self.sumar(8, pr.x, pr.y)
                self.emitir("pop", pr.x, pr.y, (180, 110, 255))
                self.sonar("pop", pr.x, pr.y)
                self.cargar(6)
                return True
        for a in list(self.antenas):
            if id(a) not in pr.golpeados and a.rect().inflate(r - 6, r - 6).collidepoint(punto):
                pr.golpeados.add(id(a))
                self._golpe_antena(a)
                return True
        if self.viral and "viral" not in pr.golpeados and _dist((self.viral.x, self.viral.y - 10), punto) < 16 + r / 2:
            pr.golpeados.add("viral")
            self._golpe_viral(1)
            return True
        for p in self.peleas:
            if p.get("activa") and not p.get("fin") and id(p) not in pr.golpeados:
                a, b = self.vecinos[p["a"]], self.vecinos[p["b"]]
                if min(_dist(a.cuerpo, punto), _dist(b.cuerpo, punto), _dist(self._pos_pelea(p), punto)) < r + 4:
                    pr.golpeados.add(id(p))
                    p["golpes"] = p.get("golpes", 0) + (GOLPES_PELEA if j.clave == "caro" else 1)
                    self.emitir("chispas", pr.x, pr.y, (255, 230, 150))
                    if p["golpes"] >= GOLPES_PELEA:
                        self._calmar(p)
                    else:
                        self.sonar("golpe", pr.x, pr.y)
                    return True
        return False

    # ------------------------------------------------------------- estrellas (noticias verdaderas)
    def _estrellas(self, dt):
        self.t_kiosco -= dt
        if self.t_kiosco <= 0:
            self.t_kiosco = 12.0
            if len(self.estrellas) < 2:
                ox, oy = self.kiosco[self.k_kiosco % len(self.kiosco)]
                self.k_kiosco += 1
                x, y = 27.5 * TILE + ox, 37.2 * TILE + oy
                if self.mapa.libre(pygame.Rect(int(x) - 5, int(y) - 5, 10, 8)):
                    self.estrellas.append(Estrella(self._id(), x, y))
                    self.emitir("aparece", x, y)
        for s in list(self.estrellas):
            s.t += dt
            s.vida -= dt
            if s.vida <= 0:
                self.estrellas.remove(s)
                self.emitir("puff", s.x, s.y)
                self._hoja(["verdadera", "ignorar"])

    # ------------------------------------------------------------- antenas del Bot
    def _antenas(self, dt):
        if not self.antenas and self.t_antena > 0:
            self.t_antena -= dt
            if self.t_antena <= 0:
                self._poner_antena()
        for a in list(self.antenas):
            a.golpe = max(0.0, a.golpe - dt)
            a.t -= dt
            if a.t <= 0:
                a.t = max(6.5, 10.0 - self.t * 0.03) * self.ritmo_ronda * (1.4 if self.tranquilo else 1.0)
                if len(self.bulos_libres()) < MAX_BULOS_LIBRES:
                    b = self.nuevo_bulo(a.x, a.y - 34)
                    b.vx, b.vy = 0, -30
                    self.emitir("onda", a.x, a.y - 30)
                    self.sonar("antena", a.x, a.y)

    def _poner_antena(self, extra=False):
        k = self.orden_antenas[self.k_antena % len(self.orden_antenas)]
        self.k_antena += 1
        x, y = ANTENAS[k]
        a = Antena(x * TILE + 8, y * TILE + 14, 4 if self.tranquilo else 6)
        self.antenas.append(a)
        self.emitir("aparece", a.x, a.y - 20)
        if extra:
            self.aviso("¡OTRA ANTENA!", (255, 120, 120))

    def _golpe_antena(self, a):
        j = self.jugador
        a.vida -= 1
        a.golpe = 0.25
        self.emitir("chispas", a.x, a.y - 20, (255, 140, 90))
        self.sonar("golpe", a.x, a.y)
        if a.vida <= 0:
            self.antenas.remove(a)
            j.stats["antenas"] += 1
            self.sumar(50, a.x, a.y - 30)
            self.ajustar(desinformacion=-6, informacion=3)
            self.emitir("explosion", a.x, a.y - 16)
            self.emitir("temblor", 7)
            self.sonar("explosion", a.x, a.y)
            self.cargar(20)
            if not self.antenas:
                self.t_antena = 14.0

    # ------------------------------------------------------------- viral (decisión con tiempo)
    def _viral(self, dt):
        v = self.viral
        if not v:
            return
        v.golpe = max(0.0, v.golpe - dt)
        if v.congelado > 0:
            v.congelado -= dt
            return
        v.t -= dt
        obj = self.vecinos[v.objetivo]
        d = _dist((v.x, v.y), obj.cabeza)
        if d > 6:
            v.x += (obj.cabeza[0] - v.x) / d * 12 * dt
            v.y += (obj.cabeza[1] - v.y) / d * 12 * dt
        if v.t <= 0:
            self._estalla_viral()

    def _golpe_viral(self, n):
        v = self.viral
        v.vida -= n
        v.golpe = 0.3
        self.emitir("chispas", v.x, v.y - 10, (200, 140, 255))
        self.sonar("golpe", v.x, v.y)
        if v.vida <= 0:
            j = self.jugador
            j.stats["viral"] += 1
            self._hoja(["falsa", "atrapar"])
            self.sumar(60, v.x, v.y - 20)
            self.ajustar(desinformacion=-8, informacion=5, confianza=4)
            self.emitir("explosion", v.x, v.y - 10)
            self.emitir("temblor", 6)
            self.aviso("¡VIRAL DETENIDO!", (120, 230, 140))
            self.sonar("victoria")
            self.viral = None
            self.cargar(25)

    def _estalla_viral(self):
        """Se hizo viral: la mentira recorre el grafo social por anchura (BFS) dos niveles."""
        v = self.viral
        self.viral = None
        origen = v.objetivo
        orden = self.social.bfs(origen, filtro=lambda u: self.vecinos[u].escudo <= 0, max_nivel=2)
        ids = {}
        alcanzados = 0
        for u, nivel, padre in orden:
            w = self.vecinos[u]
            if w.escudo > 0:
                continue
            if w.bulo is not None:
                ids[u] = w.bulo
                continue
            if alcanzados >= MAX_VIRAL:
                break
            nuevo = self._infectar(w, ids.get(padre))
            if nuevo:
                ids[u] = nuevo
                alcanzados += 1
                self._hoja(["falsa", "llega", "pasar"])
                self.emitir("ola", u, nivel, (255, 110, 160))
        self.jugador.stats["regados"] += alcanzados
        self.emitir("temblor", 6)
        self.sonar("viral_mal")
        self.ajustar(desinformacion=10, confianza=-6, bienestar=-4)
        self.aviso("¡SE REGÓ!", (255, 110, 140))

    # ------------------------------------------------------------- peleas
    def _pos_pelea(self, p):
        a, b = self.vecinos[p["a"]], self.vecinos[p["b"]]
        return ((a.x + b.x) / 2, min(a.y, b.y) - 34)

    def _peleas(self, dt):
        for p in self.peleas:
            if p.get("fin"):
                continue
            a, b = self.vecinos[p["a"]], self.vecinos[p["b"]]
            if not p["activa"]:
                p["espera"] -= dt
                if _dist(a.pos, b.pos) < 30 or p["espera"] <= 0:
                    p["activa"] = True
                    if _dist(a.pos, b.pos) > 50:
                        # no alcanzó a llegar: se ponen frente a frente
                        for dx in (16, -16, 0):
                            if self.mapa.libre(pygame.Rect(int(a.x + dx) - 4, int(a.y) - 3, 8, 4)):
                                b.x, b.y = a.x + dx, a.y
                                break
                    p["t"] = 15.0 if not self.tranquilo else 20.0
                    a.ruta, b.ruta = [], []
                    self.emitir("pelea", a.nombre, b.nombre)
                    self.aviso("¡PELEA!", (255, 150, 90))
                    self.sonar("pelea", a.x, a.y)
                continue
            p["t"] -= dt
            if p["t"] <= 0:
                p["fin"] = "rota"
                a.pelea = b.pelea = None
                a.triste = b.triste = 4.0
                if self.social.eliminar_arista(a.nombre, b.nombre):
                    self.rotos.append((a.nombre, b.nombre))
                self.ajustar(convivencia=-10, conflictos=8, bienestar=-4)
                self.aviso("¡AMISTAD ROTA!", (255, 130, 110))
                self.sonar("mal")

    def _empezar_pelea(self, azar):
        opciones = [(a, b) for a, b, _ in self.social.aristas()
                    if not self.vecinos[a].pelea and not self.vecinos[b].pelea
                    and _dist(self.vecinos[a].pos, self.vecinos[b].pos) < 200]
        if not opciones:
            return
        a, b = opciones[int(azar * len(opciones)) % len(opciones)]
        p = {"a": a, "b": b, "activa": False, "espera": 6.0, "t": 0, "golpes": 0}
        self.peleas.append(p)
        va, vb = self.vecinos[a], self.vecinos[b]
        va.pelea = vb.pelea = p
        va.ruta = []
        vb.ruta, vb.espera = [], 6.0
        va.espera = 0
        self._nuevo_destino(va)

    # ------------------------------------------------------------- eventos al azar
    def _guion(self, dt):
        while self.guion and self.guion[0][0] <= self.t:
            _, tipo, azar = self.guion.pop(0)
            self._evento(tipo, azar)

    def _evento(self, tipo, azar):
        if tipo == "falsa":                 # aparece una noticia falsa: un grupito de Bulos
            x, y = self._punto_suelto()
            for k in range(3):
                self.nuevo_bulo(x + (k - 1) * 14, y - 20)
            self.emitir("aparece", x, y - 20)
            self.sonar("antena", x, y)
        elif tipo == "verdad":              # se publica una noticia verdadera
            for _ in range(2):
                x, y = self._punto_suelto()
                self.estrellas.append(Estrella(self._id(), x, y))
                self.emitir("aparece", x, y)
            self.aviso("¡NOTICIAS!", (255, 220, 90))
        elif tipo == "rumor":               # rumor sobre un candidato (se ve su color en el Bulo)
            cand = CANDIDATOS[int(azar * 3)]
            for k in range(2):
                x, y = self._punto_suelto()
                self.nuevo_bulo(x, y - 20, candidato=cand)
                self.emitir("aparece", x, y - 20)
        elif tipo == "pelea":
            self._empezar_pelea(azar)
        elif tipo == "reporte":             # un vecino reporta el Bulo por su cuenta
            inf = sorted(self.infectados(), key=lambda v: v.nombre)
            if inf:
                v = inf[int(azar * len(inf)) % len(inf)]
                ids = self.arbol.eliminar_subarbol(v.bulo)
                for i in ids:
                    b = self.bulos.pop(i, None)
                    if b and b.estado == "cabeza" and b.vecino in self.vecinos:
                        self.vecinos[b.vecino].bulo = None
                        self._hoja(["falsa", "llega", "curar"])
                self.pulsos = [p for p in self.pulsos if p.padre in self.arbol]
                self.emitir("pop", v.x, v.y - 20, (255, 255, 255))
                self.ajustar(informacion=3, confianza=2)
            else:
                self._evento("verdad", azar)
        elif tipo == "campana":             # campaña de convivencia digital: nuevas amistades
            for p in self.peleas:
                if not p.get("fin"):
                    p["fin"] = "paz"
                    self.vecinos[p["a"]].pelea = self.vecinos[p["b"]].pelea = None
            nombres = sorted(self.vecinos)
            hechas = 0
            r = random.Random(int(azar * 1e6))
            for _ in range(30):
                a, b = r.sample(nombres, 2)
                if not self.social.tiene_arista(a, b):
                    self.social.agregar_arista(a, b, 1)
                    self.nuevos.append((a, b))
                    self.emitir("hilo", a, b, (120, 230, 140))
                    hechas += 1
                    if hechas == 2:
                        break
            self.ajustar(convivencia=8, conflictos=-6, bienestar=5)
            self.sonar("paz")
        elif tipo == "viral":
            sanos = [v for v in self.vecinos.values() if v.bulo is None and v.escudo <= 0]
            if not sanos:
                return
            obj = max(sanos, key=lambda v: (self.social.grado(v.nombre), v.nombre))
            x, y = obj.x + (60 if obj.x < 900 else -60), obj.y - 50
            self.viral = Viral(x, y, obj.nombre)
            self.aviso("¡VIRAL!", (255, 90, 140))
            self.sonar("alarma", x, y)
            self.emitir("temblor", 3)
        elif tipo == "antena2":
            self._poner_antena(extra=True)

    # ------------------------------------------------------------- fin del turno
    def _cerrar(self):
        self.terminado = True
        # los que se quedaron con el Bulo sin pasarlo: "alguien se la creyó" y quedó así
        for v in self.infectados():
            if v.bulo not in self.pasaron:
                self.decisiones.recorrer(["falsa", "llega"])
        self.sonar("fin")

    def resumen(self):
        j = self.jugador
        salvados = self.salvados()
        bono = salvados * 10
        total = j.puntos + bono
        n = len(self.vecinos)
        reputacion = 3 if salvados >= n * 0.78 else 2 if salvados >= n * 0.5 else 1
        return {"personaje": j.clave, "puntos": j.puntos, "salvados": salvados, "vecinos": n,
                "bono": bono, "total": total, "reputacion": reputacion, "stats": dict(j.stats),
                "indicadores": self.indicadores(), "rumores": dict(self.rumores),
                "defendidos": dict(self.defendidos), "rotos": list(self.rotos), "nuevos": list(self.nuevos),
                "arbol": [(n_.clave, n_.texto, n_.veces, n_.padre.clave if n_.padre else None, n_.es_hoja)
                          for n_ in self.decisiones.preorden()],
                "cadena_max": self.arbol.mayor_cadena,
                "red": {"estados": {nom: ("bulo" if v.bulo is not None else "protegido" if v.escudo > 0 else "sano")
                                    for nom, v in self.vecinos.items()},
                        "aristas": [list(a) for a in self.social.aristas()],
                        "comunidades": len(self.social.componentes()),
                        "mas_conectado": self.social.mas_conectado()}}

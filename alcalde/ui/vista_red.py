"""Vista del grafo social de Civitas: caras conectadas, pulsos de propagación y herramientas."""
import math

import pygame
import pygame.gfxdraw

from ..estructuras.grafo import Grafo
from ..modelo.mapa import ZONAS, nombre_zona
from . import recursos
from .efectos import suave
from .juego_comun import EXPRESION, cara, color_caso, color_estado, forma_creencia
from .tema import TEMA
from .widgets import Boton, chip, circulo, forma_estado, parrafo, recortar, sticker, texto

HERRAMIENTAS = [("bfs", "BFS", "waypoints"), ("dfs", "DFS", "git-branch"), ("burbujas", "Burbujas", "users-round"),
                ("super", "Grados", "megaphone"), ("confianza", "Confianza", "route")]
COLORES_COMP = [(108, 77, 245), (255, 111, 97), (46, 176, 168), (242, 153, 74), (58, 134, 255)]
ETIQUETAS = {"falso": "Cree algo falso", "veraz": "Cree la verdad", "corregido": "Corregido",
             "duda": "Dudó", "nada": "No lo ha visto"}


class VistaRed:
    def __init__(self, juego, rect):
        self.j = juego
        self.rect = pygame.Rect(rect)
        self.area = pygame.Rect(self.rect.x + 44, self.rect.y + 116, self.rect.w - 88, self.rect.h - 196)
        self.pos = {}
        self.objetivo = {}
        self.caso_id = None
        self.pulsos = []
        self.flashes = {}
        self.rotas = []
        self.fantasmas = []
        self.nacidos = {}
        self.hover = None
        self.origen = None
        self.herr = None
        self.herr_t0 = 0
        self.herr_datos = {}
        self.chips = []
        x = self.rect.x + 14
        self.botones = []
        for clave, nombre, ic in HERRAMIENTAS:
            self.botones.append(Boton((x, self.rect.bottom - 52, 108, 40), nombre, clave, icono=ic, tam=14,
                                      sombra=3, estilo="suave"))
            x += 114

    @property
    def p(self):
        return self.j.p

    # ------------------------------------------------------------------ disposición
    def _ancla(self, zona):
        x, y = ZONAS[zona]["pos"]
        return self.area.x + x * self.area.w, self.area.y + y * self.area.h

    def calcular_layout(self):
        p = self.p
        por_zona = {}
        for v in p.red.vertices():
            por_zona.setdefault(p.red.dato(v).zona, []).append(v)
        self.objetivo = {}
        for zona, gente in por_zona.items():
            if zona not in ZONAS:
                continue
            ax, ay = self._ancla(zona)
            gente.sort(key=lambda v: (p.red.dato(v).jugador is None, str(v)))
            n = len(gente)
            radio = 0 if n == 1 else 16 + 6 * n
            giro = (hash(zona) % 628) / 100
            for i, v in enumerate(gente):
                a = giro + 2 * math.pi * i / max(1, n)
                self.objetivo[v] = (ax + math.cos(a) * radio, ay + math.sin(a) * radio * 0.78)
        ahora = pygame.time.get_ticks()
        for v, (x, y) in self.objetivo.items():
            if v not in self.pos:
                self.pos[v] = [x, y]
                self.nacidos[v] = ahora
        for v in list(self.pos):
            if v not in self.objetivo:
                self.fantasmas.append((v, *self.pos[v], ahora))
                del self.pos[v]

    def nodo_en(self, punto):
        for v, (x, y) in self.pos.items():
            r = 22 if self.p.jugador_de(v) else 18
            if (x - punto[0]) ** 2 + (y - punto[1]) ** 2 <= (r + 3) ** 2:
                return v
        return None

    # ------------------------------------------------------------------ animaciones
    def animar(self, ev):
        t = ev.get("t")
        ahora = pygame.time.get_ticks()
        pasos = ev.get("pasos") or []
        if t in ("ola", "difusion", "caso") and pasos:
            paso = min(55, 2600 / max(1, len(pasos)))
            for i, (u, v, cid, tipo, que) in enumerate(pasos):
                self.pulsos.append(dict(u=u, v=v, t0=ahora + i * paso, dur=520, tipo=tipo, que=que))
        elif t == "alerta":
            for i, v in enumerate(ev.get("a", [])):
                self.pulsos.append(dict(u=ev["de"], v=v, t0=ahora + i * 60, dur=480, tipo="correccion", que="corrige"))
        elif t == "bfs":
            for k, nivel in enumerate(ev.get("niveles", [])[1:]):
                for v in nivel:
                    padre = self._padre_bfs(ev["origen"], v)
                    self.pulsos.append(dict(u=padre, v=v, t0=ahora + k * 520, dur=480, tipo="correccion", que="corrige"))
        elif t == "confianza":
            for i, ruta in enumerate(ev.get("rutas", {}).values()):
                for k in range(len(ruta) - 1):
                    self.pulsos.append(dict(u=ruta[k], v=ruta[k + 1], t0=ahora + i * 160 + k * 380, dur=360,
                                            tipo="correccion", que="corrige" if k == len(ruta) - 2 else "recibe"))
        elif t == "rastreo":
            ruta = ev.get("ruta", [])
            for k in range(len(ruta) - 1, 0, -1):
                self.pulsos.append(dict(u=ruta[k], v=ruta[k - 1], t0=ahora + (len(ruta) - 1 - k) * 380, dur=360,
                                        tipo="rastreo", que="recibe"))
        elif t == "arista_rota":
            self.rotas.append((ev["u"], ev["v"], ahora))
        elif t == "vertice_nuevo":
            self.nacidos[ev["v"]] = ahora
        elif t == "charla":
            for v in ev.get("a", []):
                self.flashes[v] = (ahora, color_estado("corregido"), "check")

    def _padre_bfs(self, origen, v):
        if origen in self.p.red:
            _, _, padre = self.p.red.bfs(origen, max_nivel=2)
            return padre.get(v) or origen
        return origen

    def herramienta(self, clave):
        p = self.p
        red = p.red
        origen = self.origen if self.origen in red else self.j.yo().nombre
        self.herr, self.herr_t0, self.herr_datos = clave, pygame.time.get_ticks(), {}
        if clave == "bfs":
            orden, nivel, padre = red.bfs(origen)
            niveles = red.bfs_niveles(origen)
            partes = [f"{k} salto{'s' if k > 1 else ''}: " + ", ".join(map(str, n)) for k, n in enumerate(niveles[1:4], 1)]
            self.herr_datos = dict(nivel=nivel, padre=padre, origen=origen,
                                   texto=f"Recorrido en anchura (cola) desde {origen}: así avanza un rumor, una ola "
                                         f"por nivel. " + "; ".join(partes) + ("…" if len(niveles) > 4 else "."))
        elif clave == "dfs":
            orden = red.dfs(origen)
            self.herr_datos = dict(orden=orden, origen=origen,
                                   texto=f"Recorrido en profundidad (pila) desde {origen}: llega a {len(orden)} "
                                         "personas siguiendo una cadena hasta el fondo antes de volver.")
        elif clave == "burbujas":
            comps = red.componentes_conexas()
            comp_de = {v: i for i, comp in enumerate(comps) for v in comp}
            if len(comps) == 1:
                txt = "Componentes conexas (con DFS): toda la red está conectada, un desmentido puede llegarle a todos."
            else:
                txt = (f"Componentes conexas (con DFS): hay {len(comps)} grupos. El más pequeño tiene "
                       f"{len(comps[-1])} personas aisladas: una burbuja donde no entran los desmentidos de afuera.")
            self.herr_datos = dict(comp=comp_de, texto=txt)
        elif clave == "super":
            top = red.centralidad_grado(3)
            self.herr_datos = dict(top={v: i for i, (v, _) in enumerate(top)},
                                   texto="Grado de salida (seguidores): " + ", ".join(f"{v} {g}" for v, g in top)
                                         + ". Si uno de ellos comparte algo, llega lejos en una sola ola.")
        elif clave == "confianza":
            yo = self.j.yo().nombre
            destino = self.origen if self.origen in red and self.origen != yo else None
            conf, prev = red.confianza_maxima(yo)
            if destino is None:
                self.herr_datos = dict(texto="Haz clic en una persona de la red y vuelve a pulsar Confianza para ver "
                                             "el camino en el que más confía (Dijkstra con -log del peso).")
            elif destino not in conf:
                self.herr_datos = dict(texto=f"No hay ningún camino desde {yo} hasta {destino}: están en burbujas distintas.")
            else:
                ruta = Grafo.reconstruir(prev, destino)
                pesos = " × ".join(f"{red.peso(ruta[k], ruta[k + 1]):.2f}" for k in range(len(ruta) - 1))
                self.herr_datos = dict(ruta=ruta, texto=f"Camino de máxima confianza: {' › '.join(map(str, ruta))}. "
                                                        f"Confianza total {pesos} = {conf[destino]:.2f}.")

    # ------------------------------------------------------------------ eventos
    def evento(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.hover = self.nodo_en(e.pos) if self.area.inflate(40, 40).collidepoint(e.pos) else None
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for r, cid in self.chips:
                if r.collidepoint(e.pos):
                    self.caso_id = cid
                    self.j.app.sonar("click")
                    return True
            for b in self.botones:
                if b.clic(e.pos):
                    self.herramienta(b.clave)
                    self.j.app.sonar("click")
                    return True
            v = self.nodo_en(e.pos)
            if v is not None:
                self.origen = v
                self.j.app.sonar("pop")
                self.j.seleccionar_de_autor(v, self.caso_id)
                if self.herr:
                    self.herramienta(self.herr)
                return True
        return False

    # ------------------------------------------------------------------ dibujo
    def dibujar(self, sup):
        p = self.p
        c = TEMA.c
        ahora = pygame.time.get_ticks()
        mov = not TEMA.op["menos_movimiento"]
        self.calcular_layout()
        for v, (tx, ty) in self.objetivo.items():
            q = self.pos[v]
            q[0] += (tx - q[0]) * (0.15 if mov else 1)
            q[1] += (ty - q[1]) * (0.15 if mov else 1)
        caso = p.caso_por_id(self.caso_id) if self.caso_id else None
        if caso is not None and not caso.abierto:
            self.caso_id, caso = None, None
        self._chips(sup, caso)
        # fondo de zonas
        for zona in ZONAS:
            ax, ay = self._ancla(zona)
            pygame.draw.circle(sup, c["papel2"], (ax, ay), 44)
            texto(sup, nombre_zona(zona), (ax, ay + 52), 11, c["tenue"], peso=800, ancla="c")
        datos = self.herr_datos
        e_herr = (ahora - self.herr_t0)
        if self.herr == "burbujas":
            for v, (x, y) in self.pos.items():
                col = COLORES_COMP[datos["comp"].get(v, 0) % len(COLORES_COMP)]
                pygame.gfxdraw.filled_circle(sup, round(x), round(y), 30, (*col, 70))
        # aristas
        capa = pygame.Surface(sup.get_size(), pygame.SRCALPHA)
        resaltadas = set()
        if self.herr == "bfs":
            lim = e_herr / 600
            for v, u in datos["padre"].items():
                if u is not None and datos["nivel"][v] <= lim:
                    resaltadas.add((u, v))
        if self.herr == "confianza" and "ruta" in datos:
            ruta = datos["ruta"]
            resaltadas |= {(ruta[k], ruta[k + 1]) for k in range(len(ruta) - 1)}
        hover_v = self.hover
        propagacion = set()
        if caso is not None:
            for receptor, nid in caso.receptores.items():
                nodo = caso.arbol.buscar(nid) if isinstance(nid, int) and nid >= 0 else None
                if nodo is not None and nodo.autor != receptor:
                    propagacion.add((nodo.autor, receptor))
        for u, v, a in p.red.aristas():
            if u not in self.pos or v not in self.pos:
                continue
            mutua = p.red.tiene_arista(v, u)
            if mutua and str(u) > str(v) and (u, v) not in resaltadas and (u, v) not in propagacion:
                continue
            if mutua and (v, u) in propagacion and (u, v) not in propagacion:
                continue
            x1, y1 = self.pos[u]
            x2, y2 = self.pos[v]
            w = 1 + round(1.6 * a["peso"])
            col = (*c["arista"], 85 if not TEMA.alto_contraste else 160)
            if (u, v) in propagacion:
                col, w = (*color_caso(caso.id), 235), w + 2
            if hover_v in (u, v):
                col, w = (*c["acento"], 235), w + 1
            if (u, v) in resaltadas or (v, u) in resaltadas:
                col, w = (*c["resalte"], 255), w + 3
            pygame.draw.line(capa, col, (x1, y1), (x2, y2), w)
            if not mutua or (u, v) in propagacion:
                ang = math.atan2(y2 - y1, x2 - x1)
                rx, ry = x2 - math.cos(ang) * 22, y2 - math.sin(ang) * 22
                pts = [(rx, ry), (rx - math.cos(ang - 0.45) * 10, ry - math.sin(ang - 0.45) * 10),
                       (rx - math.cos(ang + 0.45) * 10, ry - math.sin(ang + 0.45) * 10)]
                pygame.draw.polygon(capa, col, pts)
        sup.blit(capa, (0, 0))
        for u, v, t0 in list(self.rotas):
            e = (ahora - t0) / 2600
            if e > 1:
                self.rotas.remove((u, v, t0))
                continue
            if u in self.pos and v in self.pos:
                (x1, y1), (x2, y2) = self.pos[u], self.pos[v]
                pygame.draw.line(sup, c["malo"], (x1, y1), (x2, y2), 4)
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                circulo(sup, (mx, my), 11, c["malo"], c["borde"], 2)
                sup.blit(recursos.icono("x", 14, c["sobre_color"], 3), (mx - 7, my - 7))
        # pulsos
        vivos = []
        for pu in self.pulsos:
            e = (ahora - pu["t0"]) / pu["dur"]
            if e < 0:
                vivos.append(pu)
                continue
            if pu["u"] not in self.pos or pu["v"] not in self.pos:
                continue
            col = c["resalte"] if pu["tipo"] == "rastreo" else color_estado(
                "falso" if pu["tipo"] == "falso" else "veraz" if pu["tipo"] == "veraz" else "corregido")
            if e >= 1:
                icono = {"reenvia": "repeat-2", "duda": "circle-help", "corrige": "check"}.get(pu["que"])
                self.flashes[pu["v"]] = (ahora, col, icono)
                continue
            (x1, y1), (x2, y2) = self.pos[pu["u"]], self.pos[pu["v"]]
            k = suave(e)
            x, y = x1 + (x2 - x1) * k, y1 + (y2 - y1) * k
            pygame.gfxdraw.filled_circle(sup, round(x), round(y), 11, (*col, 90))
            circulo(sup, (x, y), 6, col, c["borde"], 2)
            vivos.append(pu)
        self.pulsos = vivos
        # fantasmas (cuentas suspendidas)
        quedan = []
        for v, x, y, t0 in self.fantasmas:
            e = (ahora - t0) / 1200
            if e < 1:
                quedan.append((v, x, y, t0))
                pygame.draw.circle(sup, c["malo"], (x, y), max(1, round(22 * (1 - e))), 4)
                texto(sup, "suspendida", (x, y - 30 - 20 * e), 12, c["malo"], peso=900, ancla="c")
        self.fantasmas = quedan
        # nodos
        sel = self.j.nodo_sel()
        yo = self.j.yo().nombre
        actual = p.jugador_actual.nombre
        for v, (x, y) in sorted(self.pos.items(), key=lambda kv: kv[1][1]):
            dato = p.red.dato(v)
            jugador = dato.jugador is not None
            r = 20 if jugador else 15
            nac = ahora - self.nacidos.get(v, -10_000)
            if nac < 500 and mov:
                r *= 0.4 + 0.6 * suave(nac / 500)
            est = "nada" if jugador else p.estado_ciudadano(v, caso)
            if dato.bot:
                est_col = c["malo"]
            else:
                est_col = color_estado(est) if est != "nada" else c["borde"]
            fl = self.flashes.get(v)
            if fl and ahora - fl[0] < 900:
                ef = (ahora - fl[0]) / 900
                pygame.gfxdraw.filled_circle(sup, round(x), round(y), round(r + 6 + 10 * ef), (*fl[1], round(120 * (1 - ef))))
            if v == actual:
                pul = 3 * math.sin(ahora / 160) if mov else 0
                pygame.draw.circle(sup, p.jugador_actual.color, (x, y), r + 7 + pul, 4)
            img = cara(p, v, round(2 * r), expresion=EXPRESION.get(est, "neutral"), borde=est_col,
                       grosor=4 if est != "nada" else 2)
            sup.blit(img, (x - img.get_width() / 2, y - img.get_height() / 2))
            if est != "nada" and not jugador:
                forma_estado(sup, forma_creencia(est), (x + r * 0.75, y + r * 0.75), 5)
            if sel is not None and sel.autor == v:
                pygame.draw.circle(sup, c["acento"], (x, y), r + 4, 3)
            if self.origen == v:
                pygame.draw.circle(sup, c["resalte"], (x, y), r + 9, 3)
            if p.red.grado_salida(v) >= 8 and not jugador:
                circulo(sup, (x + r * 0.8, y - r * 0.8), 8, c["mango"], c["borde"], 2)
                sup.blit(recursos.icono("megaphone", 10, c["texto"], 2.6), (x + r * 0.8 - 5, y - r * 0.8 - 5))
            if jugador:
                texto(sup, recortar(v, 12, 80, 800), (x, y + r + 9), 12, c["texto"], peso=900, ancla="c")
            if fl and ahora - fl[0] < 900 and fl[2]:
                circulo(sup, (x - r * 0.8, y - r * 0.8), 9, fl[1], c["borde"], 2)
                sup.blit(recursos.icono(fl[2], 12, c["sobre_color"], 3), (x - r * 0.8 - 6, y - r * 0.8 - 6))
            self._marca_herramienta(sup, v, x, y, r, e_herr)
        self._leyenda(sup)
        for b in self.botones:
            b.seleccionado = b.clave == self.herr
            b.dibujar(sup)
        if self.herr and datos.get("texto"):
            self._resultado(sup, datos["texto"])
        if self.hover is not None and self.hover in self.pos:
            self._tooltip(sup, self.hover, caso)

    def _marca_herramienta(self, sup, v, x, y, r, e_herr):
        c = TEMA.c
        datos = self.herr_datos
        etiqueta = None
        if self.herr == "bfs" and v in datos.get("nivel", {}) and datos["nivel"][v] <= e_herr / 600:
            etiqueta = str(datos["nivel"][v])
        elif self.herr == "dfs" and v in datos.get("orden", []):
            i = datos["orden"].index(v)
            if i <= e_herr / 260:
                etiqueta = str(i + 1)
        elif self.herr == "super" and v in datos.get("top", {}):
            etiqueta = f"#{datos['top'][v] + 1}"
            pygame.draw.circle(sup, c["mango"], (x, y), r + 6, 4)
        if etiqueta:
            circulo(sup, (x - r * 0.85, y + r * 0.85), 10, c["resalte"], c["borde"], 2)
            texto(sup, etiqueta, (x - r * 0.85, y + r * 0.85), 11, c["texto"], peso=900, ancla="c")

    def _chips(self, sup, caso):
        c = TEMA.c
        self.chips = []
        x = self.rect.x + 14
        y = self.rect.y + 14
        r = chip(sup, "Todas", (x, y), c["acento"] if self.caso_id is None else c["papel"],
                 c["sobre_color"] if self.caso_id is None else c["texto"], "users", 13)
        self.chips.append((r, None))
        x = r.right + 8
        for cs in self.p.casos_abiertos():
            sel = cs.id == self.caso_id
            nombre = recortar(cs.hecho.titulo, 13, 150, 800)
            r = chip(sup, nombre, (x, y), color_caso(cs.id) if sel else c["papel"],
                     c["sobre_color"] if sel else c["texto"], None, 13, punto=None if sel else color_caso(cs.id))
            self.chips.append((r, cs.id))
            x = r.right + 8
            if x > self.rect.right - 120:
                break

    def _leyenda(self, sup):
        c = TEMA.c
        x, y = self.rect.x + 18, self.rect.y + 56
        for est in ("falso", "veraz", "corregido", "duda", "nada"):
            forma_estado(sup, forma_creencia(est), (x + 6, y + 8), 6, color=color_estado(est))
            r = texto(sup, ETIQUETAS[est], (x + 16, y), 12, c["tinta2"], peso=800)
            x = r.right + 14
        nota = ("Línea de color: el camino que siguió esta historia (su árbol)." if self.caso_id else
                "Flecha: a quién le llega lo que publica. Grosor: confianza.")
        texto(sup, nota, (self.rect.x + 18, y + 20), 12, c["tenue"], peso=800)

    def _resultado(self, sup, s):
        c = TEMA.c
        r = pygame.Rect(self.rect.x + 14, self.rect.bottom - 128, self.rect.w - 28, 68)
        sticker(sup, r, c["mango2"], 14, 3, 2)
        parrafo(sup, s, r.x + 12, r.y + 9, r.w - 24, 13, c["texto"], peso=700, max_lineas=3)

    def _tooltip(self, sup, v, caso):
        p = self.p
        c = TEMA.c
        d = p.red.dato(v)
        x, y = self.pos[v]
        lineas = [str(v) + (" (cuenta bot)" if d.bot else ""),
                  f"Vive en {nombre_zona(d.zona)}",
                  f"{p.red.grado_salida(v)} seguidores, sigue a {p.red.grado_entrada(v)}"]
        if d.es_npc and not d.bot:
            lineas.append(("Muy crédulo" if d.credulidad > 0.6 else "Crédulo" if d.credulidad > 0.4 else "Escéptico")
                          + (", muy activo" if d.actividad > 0.7 else ", activo" if d.actividad > 0.5 else ", tranquilo"))
            lineas.append(ETIQUETAS[p.estado_ciudadano(v, caso)])
        w = max(recursos.fuente(13, 800).size(l)[0] for l in lineas) + 26
        h = 14 + 19 * len(lineas)
        bx = min(max(self.rect.x + 6, x - w / 2), self.rect.right - w - 6)
        by = y - 30 - h if y - 30 - h > self.rect.y + 80 else y + 28
        sticker(sup, (bx, by, w, h), c["papel"], 12, 3, 2)
        for i, l in enumerate(lineas):
            texto(sup, l, (bx + 13, by + 8 + i * 19), 13, c["texto"] if i == 0 else c["tinta2"], peso=900 if i == 0 else 700)

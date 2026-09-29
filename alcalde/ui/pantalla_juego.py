import math

import pygame

from ..modelo.afirmacion import DISTORSIONES
from ..modelo.ciudad import NEGATIVOS, NOMBRES
from .tema import TEMA
from .vista_arbol import VistaArbol
from .vista_avl import dibujar_avl
from .widgets import Boton, panel, parrafo, texto, envolver

SONIDO_POR_TIPO = {"bueno": "bueno", "malo": "malo", "logro": "logro", "evento": "evento"}

class PantallaJuego:
    def __init__(self, app, partida):
        self.app = app
        self.p = partida
        self.caso_idx = 0
        self.sel = None                                        
        self.vista = VistaArbol((274, 106, 690, 440))
        self.leidos = 0
        self.ronda_vista = partida.ronda
        self.banner_t0 = pygame.time.get_ticks()
        self.mostrar_avl = False
        self.avl_ruta = []
        self.viral_t0 = None
        self.ultimo_tick = -1
        self.ind_prev = dict(partida.ciudad.v)
        self.modo_profesor = False
        self._casos_turno = set()
        self._turno_actual_id = None

        self.botones_acc = []
        self.btn_fin = Boton((988, 700, 268, 40), "Terminar turno  (Enter)", tam=15)
        self.botones_rec = []
        x = 274
        for clave, nombre, w in (("pre", "Preorden", 110), ("post", "Postorden", 110),
                                 ("bfs", "Por niveles", 116), ("camino", "Camino a raíz", 132),
                                 ("avl", "Archivo AVL", 128)):
            self.botones_rec.append(Boton((x, 554, w, 38), nombre, clave, tam=14))
            x += w + 8
        self.btn_ayuda = Boton((1000, 12, 84, 32), "Ayuda", tam=13)
        self.btn_contraste = Boton((1090, 12, 96, 32), "Contraste", tam=13)
        self.btn_sonido = Boton((1192, 12, 76, 32), "Sonido", tam=13)
        self.tabs = []
        self._procesar_mensajes()

    @property
    def caso(self):
        abiertos = self.p.casos_abiertos()
        if not abiertos:
            return None
        self.caso_idx %= len(abiertos)
        return abiertos[self.caso_idx]

    @property
    def arbol(self):
        return self.caso.arbol if self.caso else None

    def _cambiar_caso(self, idx):
        self.caso_idx = idx
        self.sel = None
        self.vista.olvidar()
        self.vista.seleccionado = None

    def _procesar_mensajes(self):
        nuevos = self.p.mensajes[self.leidos:]
        self.leidos = len(self.p.mensajes)
        sonado = False
        for m in nuevos:
            if m.tipo != "info" or "Verific" in m.texto or "compart" in m.texto:
                self.app.toasts.agregar(m.texto, m.tipo)
            if not sonado and m.tipo in SONIDO_POR_TIPO:
                self.app.snd.play(SONIDO_POR_TIPO[m.tipo])
                sonado = True

    def _aplicar_resaltado(self):
        r = self.p.ultimo_resaltado
        self.vista.resaltar(camino=r.get("camino", []), mutacion=r.get("mutacion", []),
                            inmunes=r.get("inmunes", []))
        if "avl_ruta" in r:
            self.avl_ruta = r["avl_ruta"]
        if "podados" in r:
            self.app.snd.play("rama")

    def _accion(self, clave):
        if self.sel is None or self.caso is None or self.sel.id not in self.arbol:
            return
            
        caso_id_actual = self.caso.id
        
        self.p.ejecutar(clave, self.caso, self.sel)
        self._aplicar_resaltado()
        
        if self.arbol is None or self.sel.id not in self.arbol:
            self._casos_turno.add(caso_id_actual)
            self.sel = None
            self.vista.seleccionado = None
                                                                                    
        elif clave == "verificar":
            pass                                                         
                                                                            
        elif not self.modo_profesor:
            self._casos_turno.add(caso_id_actual)
            self.sel = None
            self.vista.seleccionado = None
        self._procesar_mensajes()

    def _terminar_turno(self):
        self.ind_prev = dict(self.p.ciudad.v)
        self.p.terminar_turno()
        self.sel = None
        self.vista.seleccionado = None
        self.vista.secuencia = []
        if self.p.ronda != self.ronda_vista:
            self.ronda_vista = self.p.ronda
            self.banner_t0 = pygame.time.get_ticks()
        self._procesar_mensajes()
        if self.p.evento_viral:
            self.viral_t0 = pygame.time.get_ticks()
            self.app.snd.play("viral")
                                                    
            abiertos = self.p.casos_abiertos()
            if self.p.evento_viral.caso in abiertos:
                self._cambiar_caso(abiertos.index(self.p.evento_viral.caso))
        if self.p.terminada:
            self.app.fin_partida(self.p)

    def _recorrido(self, clave):
        a = self.arbol
        if clave == "avl":
            self.mostrar_avl = True
            return
        if a is None or a.raiz is None:
            return
        if clave == "pre":
            self.vista.animar_recorrido("Preorden", [n.id for n in a.preorden()])
        elif clave == "post":
            self.vista.animar_recorrido("Postorden", [n.id for n in a.postorden()])
        elif clave == "bfs":
            self.vista.animar_recorrido("Por niveles", [n.id for nivel in a.por_niveles() for n in nivel])
        elif clave == "camino":
            if self.sel is None:
                self.app.toasts.agregar("Selecciona un nodo para ver su camino a la raíz.", "info")
                return
            self.vista.animar_recorrido("Camino a raíz", [n.id for n in a.camino_a_raiz(self.sel.id)])
        self.app.snd.play("click")

    def evento(self, e):
        if self.p.evento_viral:
            return self._evento_viral(e)
        if self.mostrar_avl:
            if (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE) or \
                    (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1):
                self.mostrar_avl = False
            return
        if e.type == pygame.MOUSEMOTION:
            if self.modo_profesor:
                self.vista.hover = self.vista.nodo_en(self.arbol, e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.modo_profesor:
                n = self.vista.nodo_en(self.arbol, e.pos)
                if n is not None:
                    self.sel = n
                    self.vista.seleccionado = n.id
                    self.app.snd.play("click")
                    return
            for b in self.botones_acc:
                if b.clic(e.pos):
                    self._accion(b.clave)
                    return
            if self.modo_profesor:
                for i, (r, _) in enumerate(self.tabs):
                    if r.collidepoint(e.pos):
                        self._cambiar_caso(i)
                        return
                for b in self.botones_rec:
                    if b.clic(e.pos):
                        self._recorrido(b.clave)
                        return
            if self.btn_fin.clic(e.pos):
                self._terminar_turno()
            elif self.btn_ayuda.clic(e.pos):
                self.app.mostrar_ayuda = True
            elif self.btn_contraste.clic(e.pos):
                TEMA.alternar_contraste()
            elif self.btn_sonido.clic(e.pos):
                self.app.snd.activo = not self.app.snd.activo
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_TAB:
                self.modo_profesor = not self.modo_profesor
                self.app.snd.play("click")
            elif e.key == pygame.K_RIGHT and self.modo_profesor and self.p.casos_abiertos():
                self._cambiar_caso((self.caso_idx + 1) % len(self.p.casos_abiertos()))
            elif e.key == pygame.K_LEFT and self.modo_profesor and self.p.casos_abiertos():
                self._cambiar_caso((self.caso_idx - 1) % len(self.p.casos_abiertos()))
            elif e.key == pygame.K_RETURN:
                self._terminar_turno()
            elif pygame.K_1 <= e.key <= pygame.K_6:
                i = e.key - pygame.K_1
                if i < len(self.botones_acc) and self.botones_acc[i].activo:
                    self._accion(self.botones_acc[i].clave)

    def _evento_viral(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for b in self._botones_viral():
                if b.clic(e.pos):
                    self._resolver_viral(b.clave)

    def _botones_viral(self):
        bs = []
        x = 640 - 255
        for clave, nombre in (("verificar", "VERIFICAR"), ("compartir", "COMPARTIR"),
                              ("reportar", "REPORTAR"), ("ignorar", "IGNORAR")):
            bs.append(Boton((x, 478, 120, 44), nombre, clave, tam=15))
            x += 130
        return bs

    def _resolver_viral(self, clave):
        ev = self.p.evento_viral
        self.sel = ev.nodo
        self.vista.seleccionado = ev.nodo.id
        self.p.resolver_viral(clave)
        self._aplicar_resaltado()
        self.viral_t0 = None
        if self.arbol is None or self.sel.id not in self.arbol:
            self.sel = None
            self.vista.seleccionado = None
        self._procesar_mensajes()

    def actualizar(self):
                                                       
        turno_id = id(self.p.jugador_actual)
        if turno_id != self._turno_actual_id:
            self._turno_actual_id = turno_id
            self._casos_turno.clear()

        if self.p.evento_viral:
            if self.viral_t0 is None:
                self.viral_t0 = pygame.time.get_ticks()
            restante = self.p.evento_viral.segundos - (pygame.time.get_ticks() - self.viral_t0) / 1000
            if int(restante) != self.ultimo_tick:
                self.ultimo_tick = int(restante)
                self.app.snd.play("tick")
            if restante <= 0:
                self._resolver_viral(None)
        cid = self.caso.id if self.caso else None
        if cid != getattr(self, "_caso_visto", None):
            self._caso_visto = cid
            self.vista.olvidar()

        if not self.modo_profesor and self.sel is None:
            abiertos = self.p.casos_abiertos()
            
            casos_bloqueados = getattr(self, "_casos_turno", set())
            disponibles = [c for c in abiertos if c.id not in casos_bloqueados]
            
            if not disponibles and self.p.jugador_actual.atencion > 0:
                self.p._nuevo_caso(falso=self.p.rng.random() < 0.6)
                self.p._recalcular()
                abiertos = self.p.casos_abiertos()

            nombre_jugador = self.p.jugador_actual.nombre
            mejor = None
            for i in range(len(abiertos)):
                idx = (self.caso_idx + i) % len(abiertos)
                caso_temp = abiertos[idx]
                                                           
                if caso_temp.id in self._casos_turno:
                    continue
                if not caso_temp.arbol or caso_temp.arbol.raiz is None:
                    continue
                for nivel in caso_temp.arbol.por_niveles():
                    for nodo in nivel:
                        if nodo.inmune or nodo.verificado:
                            continue
                        if nodo.autor == nombre_jugador:
                            continue
                        mejor = (idx, nodo)
                        break
                    if mejor:
                        break
                if mejor:
                    break
            if mejor:
                self.caso_idx = mejor[0]
                self.sel = mejor[1]
                self.vista.seleccionado = mejor[1].id

        self.vista.calcular_layout(self.arbol)

    def dibujar(self, sup):
        c = TEMA.c
        sup.fill(c["fondo"])
        self._barra_superior(sup)
        self._panel_ciudad(sup)
        
        if self.modo_profesor:
            self._tabs(sup)
            self.vista.dibujar(sup, self.arbol)
            self._leyenda(sup)
            self._barra_recorridos(sup)
            self._registro(sup, 274, 600, 690, 150)
            self._panel_publicacion(sup)
        else:
            self._dibujar_celular(sup)
            self._registro(sup, 840, 66, 420, 614)
            self.btn_fin.rect.topleft = (988, 700)
            self.btn_fin.seleccionado = self.p.jugador_actual.atencion == 0
            self.btn_fin.dibujar(sup)

        self.app.toasts.dibujar(sup, 574, 506, 382, abajo=True)
        self._banner_ronda(sup)
        if self.mostrar_avl:
            dibujar_avl(sup, self.p.archivo, pygame.Rect(60, 50, 1160, 660), self.avl_ruta, self.p.hechos)
        if self.p.evento_viral:
            self._modal_viral(sup)

    def _barra_superior(self, sup):
        c = TEMA.c
        pygame.draw.rect(sup, c["panel"], (0, 0, 1280, 56))
        pygame.draw.line(sup, c["borde"], (0, 56), (1280, 56))
        texto(sup, "ALCALDE DIGITAL", (16, 8), 22, c["texto"], True)
        texto(sup, "Civitas · Ciudad Nova", (18, 33), 13, c["acento"])
        texto(sup, f"RONDA {min(self.p.ronda, self.p.rondas_totales)} / {self.p.rondas_totales}",
              (330, 18), 18, c["texto"], True)
        j = self.p.jugador_actual
        x = 500
        pygame.draw.circle(sup, j.color, (x + 16, 28), 16)
        texto(sup, j.info_rol["simbolo"], (x + 16, 28), 16, (10, 12, 20), True, centro=True)
        texto(sup, f"Turno de {j.nombre}", (x + 42, 9), 17, c["texto"], True)
        texto(sup, j.info_rol["nombre"] + (f" · {j.candidato}" if j.candidato else ""),
              (x + 42, 31), 13, c["tenue"])
        texto(sup, "Atención", (800, 10), 12, c["tenue"])
        for i in range(3):
            lleno = i < j.atencion
            pygame.draw.circle(sup, c["aviso"] if lleno else c["panel2"], (812 + i * 26, 38), 9)
            pygame.draw.circle(sup, c["aviso"], (812 + i * 26, 38), 9, 1)
        self.btn_ayuda.dibujar(sup)
        self.btn_contraste.seleccionado = TEMA.alto_contraste
        self.btn_contraste.dibujar(sup)
        self.btn_sonido.etiqueta = "Sonido" if self.app.snd.activo else "Mudo"
        self.btn_sonido.dibujar(sup)

    def _panel_ciudad(self, sup):
        c = TEMA.c
        r = pygame.Rect(12, 66, 250, 684)
        panel(sup, r)
        texto(sup, "CIUDAD NOVA", (26, 78), 15, c["acento"], True)
        salud = self.p.ciudad.salud()
        texto(sup, str(salud), (246, 72), 30, c["bueno"] if salud >= 55 else c["malo"], True, derecha=True)
        texto(sup, "salud", (246, 106), 11, c["tenue"], derecha=True)
        y = 124
        for k, v in self.p.ciudad.v.items():
            negativo = k in NEGATIVOS
            texto(sup, NOMBRES[k], (26, y), 13)
            texto(sup, str(v), (246, y), 13, c["texto"], True, derecha=True)
            d = v - self.ind_prev.get(k, v)
            if d:
                bueno = (d < 0) if negativo else (d > 0)
                texto(sup, f"{d:+d}", (212, y), 12, c["bueno"] if bueno else c["malo"], True, derecha=True)
            pygame.draw.rect(sup, c["panel2"], (26, y + 19, 220, 8), border_radius=4)
            col = c["malo"] if negativo else c["acento"]
            pygame.draw.rect(sup, col, (26, y + 19, int(220 * v / 100), 8), border_radius=4)
            if negativo:                                                                
                for xx in range(26, 26 + int(220 * v / 100), 7):
                    pygame.draw.line(sup, c["fondo"], (xx, y + 26), (xx + 5, y + 19), 1)
            y += 42
        y += 6
        pygame.draw.line(sup, c["borde"], (24, y), (250, y))
        texto(sup, "JUGADORES", (26, y + 10), 15, c["acento"], True)
        y += 36
        for i, j in enumerate(self.p.jugadores):
            actual = i == self.p.turno_idx
            box = pygame.Rect(20, y - 4, 234, 58)
            if actual:
                pygame.draw.rect(sup, c["panel2"], box, border_radius=8)
                pygame.draw.rect(sup, j.color, box, 2, border_radius=8)
            pygame.draw.circle(sup, j.color, (40, y + 16), 13)
            texto(sup, j.info_rol["simbolo"], (40, y + 16), 14, (10, 12, 20), True, centro=True)
            texto(sup, j.nombre, (60, y), 14, c["texto"], True)
            texto(sup, f"{j.puntos} pts", (246, y), 14, c["aviso"], True, derecha=True)
            texto(sup, f"Reputación {j.reputacion}", (60, y + 18), 12, c["tenue"])
            texto(sup, f"{len(j.logros)} logros", (246, y + 18), 12, c["logro"], derecha=True)
            pygame.draw.rect(sup, c["panel2"], (60, y + 37, 186, 5), border_radius=3)
            pygame.draw.rect(sup, j.color, (60, y + 37, int(186 * j.reputacion / 100), 5), border_radius=3)
            y += 64

    def _tabs(self, sup):
        c = TEMA.c
        self.tabs = []
        x = 274
        abiertos = self.p.casos_abiertos()
        ancho = min(228, (690 - 8 * (len(abiertos) - 1)) // max(1, len(abiertos)))
        for i, caso in enumerate(abiertos):
            r = pygame.Rect(x, 66, ancho, 34)
            sel = caso is self.caso
            pygame.draw.rect(sup, c["panel2"] if sel else c["panel"], r, border_radius=8)
            pygame.draw.rect(sup, c["acento"] if sel else c["borde"], r, 2 if sel else 1, border_radius=8)
            t = f"Caso {caso.id} · {caso.hecho.titulo}"
            while TEMA.fuente(13, True).size(t)[0] > ancho - 44 and len(t) > 8:
                t = t[:-2]
            texto(sup, t if t.endswith(caso.hecho.titulo) else t + "…", (x + 10, 75), 13,
                  c["texto"] if sel else c["tenue"], True)
            texto(sup, str(len(caso.arbol)), (r.right - 10, 75), 13, c["aviso"], True, derecha=True)
            self.tabs.append((r, caso))
            x += ancho + 8

    def _leyenda(self, sup):
        c = TEMA.c
        x, y = 290, 524
        from .widgets import poligono_regular
        items = [("sin verificar", "c", c["n_desconocido"]), ("verdadero", "s", c["n_veraz"]),
                 ("falso", "t", c["n_falso"]), ("desmentido", "d", c["n_correccion"])]
        for nombre, forma, col in items:
            if forma == "c":
                pygame.draw.circle(sup, col, (x, y), 6)
            elif forma == "s":
                pygame.draw.rect(sup, col, (x - 6, y - 6, 12, 12), border_radius=2)
            elif forma == "t":
                pygame.draw.polygon(sup, col, poligono_regular((x, y + 1), 8, 3, -math.pi / 2))
            else:
                pygame.draw.polygon(sup, col, poligono_regular((x, y), 8, 4))
            r = texto(sup, nombre, (x + 12, y - 8), 12, c["tenue"])
            x = r.right + 18
        if self.arbol and self.arbol.raiz:
            e = self.arbol.estadisticas()
            texto(sup, f"{e['nodos']} nodos · altura {e['altura']} · {e['olas']} olas · "
                       f"{e['alcance']} personas", (950, y - 8), 12, c["tenue"], derecha=True)

    def _barra_recorridos(self, sup):
        for b in self.botones_rec:
            b.activo = not (b.clave == "camino" and self.sel is None)
            b.dibujar(sup)

    def _registro(self, sup, x, y_pos, w, h):
        c = TEMA.c
        r = pygame.Rect(x, y_pos, w, h)
        panel(sup, r)
        y = r.y + 8
        v = self.vista
        if v.secuencia:
            paso = v.paso_actual()
            nombres = []
            for nid in v.secuencia[:paso]:
                n = self.arbol.buscar(nid) if self.arbol else None
                nombres.append(n.autor.split()[0] if n else "?")
            lineas = envolver(f"{v.sec_nombre}: " + " → ".join(nombres), 13, r.w - 24, True)
            for l in lineas[-2:]:
                texto(sup, l, (r.x + 12, y), 13, c["aviso"], True)
                y += 18
            y += 4
        texto(sup, "REGISTRO", (r.right - 12, r.y + 8), 11, c["tenue"], True, derecha=True)
        colores = {"bueno": c["bueno"], "malo": c["malo"], "logro": c["logro"], "evento": c["acento"]}
        restantes = (r.bottom - y - 4) // 18
        for m in self.p.mensajes[-restantes:] if restantes > 0 else []:
            t = m.texto
            while TEMA.fuente(13).size(t)[0] > r.w - 110 and len(t) > 10:
                t = t[:-4] + "…"
            texto(sup, t, (r.x + 12, y), 13, colores.get(m.tipo, c["tenue"]))
            y += 18

    def _panel_publicacion(self, sup):
        c = TEMA.c
        r = pygame.Rect(976, 66, 292, 684)
        panel(sup, r)
        texto(sup, "PUBLICACIÓN", (990, 78), 15, c["acento"], True)
        n = self.sel if (self.sel and self.arbol and self.sel.id in self.arbol) else None
        y = 104
        if n is None:
            y = parrafo(sup, "Haz clic en un nodo del árbol para ver la publicación. Pasa el "
                             "mouse por encima para leerla rápido.", 990, y, 262, 14, c["tenue"])
        else:
            estado = ("DESMENTIDO" if n.es_correccion else "SIN VERIFICAR" if not n.verificado
                      else "VERDADERO" if n.es_veraz else "FALSO")
            col = {"FALSO": c["n_falso"], "VERDADERO": c["n_veraz"], "DESMENTIDO": c["n_correccion"]}.get(
                estado, c["n_desconocido"])
            pygame.draw.rect(sup, col, (990, y, 124, 22), border_radius=5)
            texto(sup, estado, (1052, y + 11), 12, (10, 12, 20), True, centro=True)
            if n.inmune:
                texto(sup, "rama contenida", (1124, y + 3), 12, c["n_inmune"], True)
            y += 32
            texto(sup, n.autor, (990, y), 16, c["texto"], True)
            y += 22
            texto(sup, ("Publicación original" if n.es_raiz else f"Reenvío · ola {n.profundidad}")
                  + f" · {n.alcance} personas", (990, y), 12, c["tenue"])
            y += 24
            y = parrafo(sup, '"' + n.afirmacion.texto() + '"', 990, y, 262, 15, c["texto"]) + 8
            if n.verificado and not n.es_veraz:
                texto(sup, "Distorsiones detectadas:", (990, y), 13, c["malo"], True)
                y += 20
                for d in n.afirmacion.distorsiones:
                    texto(sup, "· " + DISTORSIONES[d], (996, y), 13, c["malo"])
                    y += 18
            if n.verificado and n.distorsion and "+" not in n.distorsion:
                y = parrafo(sup, f"En este reenvío apareció: {DISTORSIONES[n.distorsion]}",
                            990, y + 4, 262, 12, c["aviso"])
            if n.hijos:
                texto(sup, f"{len(n.hijos)} reenvíos directos", (990, y + 4), 12, c["tenue"])

        yb = 440
        texto(sup, "ACCIONES", (990, yb - 24), 15, c["acento"], True)
        self.botones_acc = []
        motivo = ""
        for i, a in enumerate(self.p.acciones_para(n)):
            b = Boton((988, yb, 268, 34), f"{i + 1}. {a['nombre']}", a["clave"], a["costo"], tam=14,
                      color=c["logro"] if a.get("especial") else None)
            b.activo = a["ok"]
            b.dibujar(sup)
            if not a["ok"] and b.rect.collidepoint(pygame.mouse.get_pos()):
                motivo = a["motivo"]
            self.botones_acc.append(b)
            yb += 40
        if motivo:
            texto(sup, motivo, (1122, yb + 2), 12, c["aviso"], centro=True)
        elif self.p.jugador_actual.atencion == 0:
            texto(sup, "Sin atención: termina tu turno", (1122, yb + 2), 12, c["aviso"], centro=True)
        self.btn_fin.seleccionado = self.p.jugador_actual.atencion == 0
        self.btn_fin.dibujar(sup)

    def _banner_ronda(self, sup):
        edad = pygame.time.get_ticks() - self.banner_t0
        if edad > 1600:
            return
        c = TEMA.c
        a = 255 if edad < 1100 else int(255 * (1600 - edad) / 500)
        capa = pygame.Surface((690, 90), pygame.SRCALPHA)
        pygame.draw.rect(capa, (*c["panel2"], 230), capa.get_rect(), border_radius=12)
        texto(capa, f"RONDA {min(self.p.ronda, self.p.rondas_totales)}", (345, 32), 34, c["texto"], True, centro=True)
        texto(capa, "Ola de propagación completada" if self.p.ronda > 1 else "La campaña comienza",
              (345, 66), 14, c["acento"], centro=True)
        capa.set_alpha(a)
        sup.blit(capa, (274, 280))

    def _modal_viral(self, sup):
        c = TEMA.c
        ev = self.p.evento_viral
        capa = pygame.Surface(sup.get_size(), pygame.SRCALPHA)
        capa.fill((0, 0, 0, 180))
        sup.blit(capa, (0, 0))
        r = pygame.Rect(355, 210, 570, 330)
        panel(sup, r, c["panel"], 14)
        pygame.draw.rect(sup, c["aviso"], r, 3, border_radius=14)
        t = pygame.time.get_ticks()
        from .widgets import poligono_regular
        pygame.draw.polygon(sup, c["aviso"], poligono_regular((402, 244), 16 + 2 * math.sin(t / 100), 3, -math.pi / 2))
        texto(sup, "!", (402, 246), 16, (10, 10, 10), True, centro=True)
        texto(sup, "INFORMACIÓN VIRAL", (428, 230), 24, c["aviso"], True)
        texto(sup, f"Decide {ev.jugador.nombre} ({ev.jugador.info_rol['nombre']}) · no gasta atención",
              (390, 264), 13, c["tenue"])
        y = parrafo(sup, '"' + ev.nodo.afirmacion.texto() + '"', 390, 292, 500, 17, c["texto"])
        texto(sup, "Esta publicación está siendo compartida rápidamente.", (390, y + 8), 14, c["tenue"])
        restante = max(0.0, ev.segundos - (t - (self.viral_t0 or t)) / 1000)
        texto(sup, f"Tiempo restante: {math.ceil(restante)} s", (390, 426), 15, c["texto"], True)
        pygame.draw.rect(sup, c["panel2"], (390, 450, 500, 10), border_radius=5)
        pygame.draw.rect(sup, c["malo"] if restante < 4 else c["aviso"],
                         (390, 450, int(500 * restante / ev.segundos), 10), border_radius=5)
        for b in self._botones_viral():
            b.dibujar(sup)

    def _dibujar_celular(self, sup):
        c = TEMA.c
        phone_rect = pygame.Rect(350, 66, 450, 684)
        pygame.draw.rect(sup, c["panel"], phone_rect, border_radius=30)
        pygame.draw.rect(sup, c["borde"], phone_rect, 4, border_radius=30)
        
        texto(sup, "PRESIONA [TAB] PARA VER MODO PROFESOR (ESTRUCTURAS)", (575, 765), 11, c["tenue"], centro=True)
        
        if self.sel is None:
            texto(sup, "No hay nuevas publicaciones", (575, 300), 20, c["tenue"], True, centro=True)
            return

        n = self.sel
        texto(sup, "CIVITAS", (575, 100), 24, c["acento"], True, centro=True)
        pygame.draw.line(sup, c["borde"], (350, 140), (800, 140), 2)
        
        pygame.draw.circle(sup, c["texto"], (400, 180), 20)
        texto(sup, n.autor[:2].upper(), (400, 182), 16, c["fondo"], True, centro=True)
        texto(sup, "@" + n.autor.replace(" ", "").lower(), (430, 170), 18, c["texto"], True)
        texto(sup, "Ola " + str(n.profundidad), (770, 170), 14, c["tenue"], derecha=True)
        
        y = parrafo(sup, n.afirmacion.texto(), 380, 230, 390, 20, c["texto"]) + 20
        
        if n.verificado:
            if n.es_veraz:
                pygame.draw.rect(sup, c["n_veraz"], (455, y, 240, 30), border_radius=8)
                texto(sup, "VERDADERO", (575, y+15), 16, c["fondo"], True, centro=True)
            elif n.es_correccion:
                pygame.draw.rect(sup, c["n_correccion"], (455, y, 240, 30), border_radius=8)
                texto(sup, "DESMENTIDO OFICIAL", (575, y+15), 16, c["fondo"], True, centro=True)
            else:
                pygame.draw.rect(sup, c["n_falso"], (455, y, 240, 30), border_radius=8)
                texto(sup, "FALSO", (575, y+15), 16, c["fondo"], True, centro=True)
            y += 45

        self.botones_acc = []
        yb = 480
        acciones = self.p.acciones_para(n)
        for i, a in enumerate(acciones):
            color = c["logro"] if a.get("especial") else c["panel2"]
            b = Boton((400, yb, 350, 45), f"{a['nombre'].upper()}", a["clave"], a["costo"], tam=16, color=color)
            b.activo = a["ok"]
            b.dibujar(sup)
            self.botones_acc.append(b)
            yb += 55

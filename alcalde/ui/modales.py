"""Ventanas emergentes del juego: viral, verificación, confirmación, Archivo AVL, noche y turno."""
import math

import pygame

from ..modelo.mapa import nombre_zona
from . import personajes, recursos
from .escena import lienzo_total
from .efectos import EFECTOS, rebote, suave
from .juego_comun import cara
from .tema import TEMA
from .widgets import Boton, ancho_texto, circulo, parrafo, recortar, sticker, texto, titulo


def velo(sup, alpha=150, rect=None, color=None):
    """Oscurece todo el lienzo (también lo que queda a los lados de la pantalla del juego)."""
    c = TEMA.c
    base, ox = lienzo_total(sup)
    capa = pygame.Surface(base.get_size(), pygame.SRCALPHA)
    capa.fill((*(color or c["tinta"]), alpha))
    if rect is not None:
        capa.fill((0, 0, 0, 0), pygame.Rect(rect).move(ox, 0))
    base.blit(capa, (0, 0))


class ModalViral:
    bloquea = True

    def __init__(self, juego):
        self.j = juego
        self.t0 = pygame.time.get_ticks()
        self.ultimo_tick = None
        self.rect = pygame.Rect(330, 150, 620, 420)
        x = self.rect.x + 30
        self.botones = []
        for clave, nombre, ic, estilo in (("verificar", "Verificar", "search", "primario"),
                                          ("reportar", "Reportar", "flag", "secundario"),
                                          ("compartir", "Compartir", "share-2", "secundario"),
                                          ("ignorar", "Ignorar", "eye-off", "secundario")):
            self.botones.append(Boton((x, self.rect.bottom - 82, 132, 54), nombre, clave, icono=ic, tam=16,
                                      estilo=estilo))
            x += 142
        self.j.app.sonar("viral")
        EFECTOS.sacudir()

    def total(self):
        ev = self.j.p.evento_viral
        return ev.segundos + (10 if TEMA.op["mas_tiempo"] else 0) if ev else 1

    def restante(self):
        r = self.j.ctrl.viral_restante()
        if r is not None:
            return r
        return max(0.0, self.total() - (pygame.time.get_ticks() - self.t0) / 1000)

    def evento(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.j.ctrl.decido_viral():
            for b in self.botones:
                if b.clic(e.pos):
                    self.j.resolver_viral(b.clave)
                    return
        elif e.type == pygame.KEYDOWN and self.j.ctrl.decido_viral():
            k = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3}.get(e.key)
            if k is not None:
                self.j.resolver_viral(self.botones[k].clave)

    def actualizar(self):
        r = self.restante()
        seg = math.ceil(r)
        if seg != self.ultimo_tick:
            self.ultimo_tick = seg
            if seg <= 5:
                self.j.app.sonar("tick")
        if r <= 0 and not self.j.ctrl.en_red:
            self.j.resolver_viral(None)

    def dibujar(self, sup):
        c = TEMA.c
        p = self.j.p
        ev = p.evento_viral
        if ev is None:
            return
        ahora = pygame.time.get_ticks()
        velo(sup, 165)
        e = min(1, (ahora - self.t0) / 380)
        r = self.rect.move(0, round((1 - rebote(e)) * 60)) if not TEMA.op["menos_movimiento"] else self.rect
        sticker(sup, r, c["papel"], 26, 8, 4, color_borde=c["tinta"])
        banda = pygame.Rect(r.x + 3, r.y + 3, r.w - 6, 64)
        pygame.draw.rect(sup, c["mango"], banda, border_top_left_radius=23, border_top_right_radius=23)
        pygame.draw.line(sup, c["tinta"], (r.x + 2, banda.bottom), (r.right - 3, banda.bottom), 3)
        bob = math.sin(ahora / 90) * 3 if not TEMA.op["menos_movimiento"] else 0
        sup.blit(recursos.icono("flame", 34, c["malo"], 2.8), (r.x + 26, r.y + 17 + bob))
        titulo(sup, "¡Se está volviendo viral!", (r.x + 72, r.y + 15), 30, c["texto"])
        y = r.y + 84
        sup.blit(cara(p, ev.nodo.autor, 54), (r.x + 30, y))
        seguidores = p.red.grado_salida(ev.nodo.autor) if ev.nodo.autor in p.red else 0
        texto(sup, str(ev.nodo.autor), (r.x + 96, y + 6), 19, c["texto"], peso=900)
        texto(sup, f"{seguidores} seguidores. Lo están compartiendo muy rápido.", (r.x + 96, y + 32), 14,
              c["tinta2"], peso=700)
        yy = parrafo(sup, "“" + ev.nodo.afirmacion.texto() + "”", r.x + 30, y + 70, r.w - 60,
                     TEMA.escala_texto(18), c["texto"], peso=700, max_lineas=4)
        rest = self.restante()
        tot = max(1, self.total())
        barra = pygame.Rect(r.x + 30, r.bottom - 118, r.w - 60, 18)
        pygame.draw.rect(sup, c["papel3"], barra, border_radius=9)
        w = round(barra.w * min(1, rest / tot))
        col = c["malo"] if rest < 4 else c["mango"]
        if w > 0:
            pygame.draw.rect(sup, col, (barra.x, barra.y, max(18, w), barra.h), border_radius=9)
        pygame.draw.rect(sup, c["borde"], barra, 2, border_radius=9)
        decide = ev.jugador
        quien = "Tú decides" if self.j.ctrl.decido_viral() and self.j.en_red() else f"Decide {decide.nombre}"
        texto(sup, f"{quien} ({decide.info_rol['nombre']}). No gasta atención.", (barra.x, barra.y - 24), 14,
              c["tinta2"], peso=800)
        reloj = texto(sup, f"{math.ceil(rest)} s", (barra.right, barra.y - 26), 20, col, peso=700, fam="titulo",
                      ancla="tr")
        sup.blit(recursos.icono("timer", 20, col, 2.6), (reloj.x - 26, reloj.y + 2))
        decido = self.j.ctrl.decido_viral()
        for i, b in enumerate(self.botones):
            b.activo = decido
            b.rect.y = r.bottom - 82
            b.dibujar(sup)
        if not decido:
            texto(sup, f"{decide.nombre} está decidiendo…", (r.centerx, r.bottom - 14), 13, c["tinta2"],
                  peso=800, ancla="c")


class HojaVerificacion:
    """Resultado de verificar: compara la publicación con el hecho oficial del Archivo."""
    bloquea = True

    def __init__(self, juego, caso, nodo, datos):
        self.j = juego
        self.caso, self.nodo, self.datos = caso, nodo, datos
        cel = juego.celular
        self.rect = pygame.Rect(cel.pantalla.x + 6, cel.r_post.y - 6, cel.pantalla.w - 12,
                                cel.r_acciones.bottom - cel.r_post.y + 12)
        self.t0 = pygame.time.get_ticks()
        self.b_ok = Boton((self.rect.x + 14, self.rect.bottom - 62, self.rect.w - 28, 48), "Entendido", "ok",
                          icono="check", estilo="primario", tam=17)
        self.b_avl = Boton((self.rect.x + 14, self.rect.bottom - 118, self.rect.w - 28, 44), "Ver el Archivo",
                           "avl", icono="archive", tam=15, sombra=3)
        inconclusa = datos.get("inconclusa")
        falsa = bool(datos.get("diferencias"))
        juego.app.sonar("sello")
        if not inconclusa and falsa:
            EFECTOS.chispas(self.rect.centerx, self.rect.y + 60, TEMA.c["malo"], 18)

    def evento(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.b_ok.clic(e.pos):
                self.j.cerrar_modal()
            elif self.b_avl.clic(e.pos):
                self.j.abrir_archivo()
        elif e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
            self.j.cerrar_modal()

    def dibujar(self, sup):
        c = TEMA.c
        p = self.j.p
        r = self.rect
        ahora = pygame.time.get_ticks()
        velo(sup, 90, None)
        sticker(sup, r, c["papel"], 22, 6, 3)
        d = self.datos
        hecho = self.caso.hecho
        if d.get("inconclusa"):
            sello, col = "Sin datos", c["aviso"]
        elif d.get("diferencias"):
            sello, col = "Falsa", c["malo"]
        else:
            sello, col = "Verdadera", c["n_veraz"]
        e = min(1, (ahora - self.t0) / 260)
        esc = 1.6 - 0.6 * suave(e) if not TEMA.op["menos_movimiento"] else 1
        s = pygame.Surface((230, 70), pygame.SRCALPHA)
        pygame.draw.rect(s, col, s.get_rect(), 6, border_radius=14)
        texto(s, sello, (115, 36), 38, col, peso=700, fam="titulo", ancla="c")
        s = pygame.transform.rotozoom(s, 8, esc)
        sup.blit(s, s.get_rect(center=(r.centerx, r.y + 52)))
        y = r.y + 100
        if d.get("inconclusa"):
            y = parrafo(sup, f"El hecho «{hecho.titulo}» no está en el Archivo de hechos, así que no se puede "
                             "comparar todavía.", r.x + 16, y, r.w - 32, 14, c["texto"], peso=700) + 10
            parrafo(sup, f"Ve a {nombre_zona(hecho.lugar)} y verifica en persona, o pídele a un periodista que lo "
                         "investigue.", r.x + 16, y, r.w - 32, 14, c["tinta2"])
        elif d.get("diferencias"):
            texto(sup, "Qué cambió frente al hecho oficial", (r.x + 16, y), 14, c["texto"], peso=900)
            y += 26
            difs = self.nodo.afirmacion.explicar_diferencias(hecho)
            limite = self.b_avl.rect.y - 30
            for k, (nombre, dice, oficial) in enumerate(difs):
                if y + 62 > limite:
                    texto(sup, f"y {len(difs) - k} cambio{'s' if len(difs) - k > 1 else ''} más", (r.x + 16, y), 13,
                          c["malo"], peso=900)
                    break
                texto(sup, nombre, (r.x + 16, y), 14, c["malo"], peso=900)
                y += 20
                y = parrafo(sup, f"Dice: {dice}", r.x + 24, y, r.w - 44, 13, c["tinta2"], peso=700, max_lineas=2,
                            interlineado=3)
                y = parrafo(sup, f"Oficial: {oficial}", r.x + 24, y, r.w - 44, 13, c["bueno"], peso=800,
                            max_lineas=2, interlineado=3) + 6
        else:
            y = parrafo(sup, "Coincide palabra por palabra con el hecho oficial:", r.x + 16, y, r.w - 32, 14,
                        c["texto"], peso=800) + 6
            parrafo(sup, "“" + hecho.afirmacion_real().texto() + "”", r.x + 16, y, r.w - 32, 14, c["tinta2"],
                    max_lineas=6)
        comps = d.get("comps")
        if comps:
            texto(sup, f"Búsqueda en el árbol AVL: {comps} comparaciones", (r.x + 16, self.b_avl.rect.y - 22), 12,
                  c["tinta2"], peso=800)
        self.b_avl.dibujar(sup)
        self.b_ok.dibujar(sup)


class ModalConfirmar:
    """Civi te pregunta antes de compartir algo sin verificar."""
    bloquea = True

    def __init__(self, juego, texto_pregunta, si, no, accion_si, accion_no):
        self.j = juego
        self.texto = texto_pregunta
        self.rect = pygame.Rect(390, 236, 500, 250)
        self.b_no = Boton((self.rect.x + 24, self.rect.bottom - 74, 214, 52), no, "no", icono="search",
                          estilo="primario", tam=17)
        self.b_si = Boton((self.rect.right - 238, self.rect.bottom - 74, 214, 52), si, "si", icono="share-2", tam=17)
        self.accion_si, self.accion_no = accion_si, accion_no
        self.t0 = pygame.time.get_ticks()

    def evento(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.b_no.clic(e.pos):
                self.j.cerrar_modal()
                self.accion_no()
            elif self.b_si.clic(e.pos):
                self.j.cerrar_modal()
                self.accion_si()
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.j.cerrar_modal()

    def dibujar(self, sup):
        c = TEMA.c
        velo(sup, 140)
        r = self.rect
        sticker(sup, r, c["papel"], 24, 7, 3)
        t = (pygame.time.get_ticks() - self.t0) / 1000
        img = personajes.civi("neutral", 150, parpadeo=(t % 3) < 0.12)
        sup.blit(img, (r.x - 60, r.y - 40))
        titulo(sup, "¿Seguro?", (r.x + 60, r.y + 22), 28, c["texto"])
        parrafo(sup, self.texto, r.x + 60, r.y + 64, r.w - 90, 16, c["tinta2"], peso=700)
        self.b_no.dibujar(sup)
        self.b_si.dibujar(sup)


class ModalArchivo:
    """El Archivo de hechos: el árbol AVL con alturas, balance y la última ruta de búsqueda."""
    bloquea = True

    def __init__(self, juego, ruta=(), nuevo=None, volver=None):
        self.j = juego
        self.ruta = list(ruta)
        self.nuevo = nuevo
        self.volver = volver
        self.rect = pygame.Rect(40, 40, 1200, 640)
        self.b_cerrar = Boton((self.rect.right - 66, self.rect.y + 18, 46, 42), "", "x", icono="x", sombra=3)
        self.t0 = pygame.time.get_ticks()

    def evento(self, e):
        if (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1) or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
            if self.volver is not None and (e.type == pygame.KEYDOWN or self.b_cerrar.clic(e.pos) or
                                            not self.rect.collidepoint(e.pos)):
                self.j.modal = self.volver
            elif e.type == pygame.KEYDOWN or self.b_cerrar.clic(e.pos) or not self.rect.collidepoint(e.pos):
                self.j.cerrar_modal()

    def dibujar(self, sup):
        c = TEMA.c
        p = self.j.p
        archivo = p.archivo
        velo(sup, 160)
        r = self.rect
        sticker(sup, r, c["papel"], 26, 8, 3)
        sup.blit(recursos.icono("archive", 30, c["acento"], 2.6), (r.x + 24, r.y + 24))
        titulo(sup, "Archivo de hechos", (r.x + 64, r.y + 18), 32, c["texto"])
        valido = archivo.es_avl_valido()
        texto(sup, f"Árbol AVL con {len(archivo)} hechos oficiales, altura {archivo.altura}. Balanceado: "
                   f"{'sí' if valido else 'no'}. Cada nodo muestra su altura (h) y su factor de balance (fb).",
              (r.x + 26, r.y + 64), 14, c["tinta2"], peso=700)
        area = pygame.Rect(r.x + 20, r.y + 100, r.w - 330, r.h - 120)
        paso = (pygame.time.get_ticks() - self.t0) // 420
        ruta = self.ruta
        orden = [k for k, _ in archivo.inorden()]
        indice = {k: i for i, k in enumerate(orden)}
        dx = (area.w - 110) / max(1, len(orden) - 1)
        dy = min(90, (area.h - 60) / max(1, archivo.altura - 1))
        pos = {}

        def ubicar(n, prof):
            if n is None:
                return
            pos[n.clave] = (area.x + 55 + indice[n.clave] * dx, area.y + 30 + prof * dy)
            ubicar(n.izq, prof + 1)
            ubicar(n.der, prof + 1)

        ubicar(archivo.raiz, 0)
        visibles = set(ruta[:paso + 1])

        def aristas(n):
            if n is None:
                return
            for hijo in (n.izq, n.der):
                if hijo:
                    en_ruta = n.clave in visibles and hijo.clave in visibles
                    if en_ruta:
                        pygame.draw.line(sup, c["tinta"], pos[n.clave], pos[hijo.clave], 9)
                    pygame.draw.line(sup, c["resalte"] if en_ruta else c["arista"], pos[n.clave], pos[hijo.clave],
                                     5 if en_ruta else 3)
                    aristas(hijo)

        aristas(archivo.raiz)

        def nodos(n):
            if n is None:
                return
            x, y = pos[n.clave]
            caja = pygame.Rect(0, 0, 104, 42)
            caja.center = (x, y)
            k = ruta.index(n.clave) if n.clave in ruta else -1
            en_ruta = 0 <= k <= paso
            fondo = c["mango2"] if en_ruta else (c["bueno2"] if n.clave == self.nuevo else c["papel2"])
            sticker(sup, caja, fondo, 12, 3 if en_ruta else 0, 3 if en_ruta else 2)
            texto(sup, recortar(n.clave, 11, 94, 900), (x, y - 8), 11, c["texto"], peso=900, ancla="c")
            bal = (n.izq.altura if n.izq else 0) - (n.der.altura if n.der else 0)
            texto(sup, f"h={n.altura}  fb={bal:+d}", (x, y + 10), 11, c["tinta2"], peso=800, ancla="c")
            if en_ruta:
                circulo(sup, (caja.right - 2, caja.y), 11, c["resalte"], c["borde"], 2)
                texto(sup, str(k + 1), (caja.right - 2, caja.y), 12, c["texto"], peso=900, ancla="c")
            nodos(n.izq)
            nodos(n.der)

        nodos(archivo.raiz)
        lx = r.right - 292
        sticker(sup, (lx - 10, r.y + 100, 282, r.h - 120), c["papel2"], 18, 0, 2)
        texto(sup, "Inorden por clave (A a la Z)", (lx + 4, r.y + 112), 15, c["texto"], peso=900)
        y = r.y + 138
        for clave, h in archivo.inorden():
            col = c["bueno"] if clave == self.nuevo else c["texto"]
            t = texto(sup, recortar(clave, 12, 130, 900), (lx + 4, y), 12, col, peso=900)
            texto(sup, recortar(h.titulo, 12, 250 - (t.right - lx), 700), (t.right + 8, y), 12, c["tinta2"], peso=700)
            y += 18
        y += 10
        texto(sup, "Última búsqueda", (lx + 4, y), 15, c["texto"], peso=900)
        y += 24
        y = parrafo(sup, " › ".join(ruta) if ruta else "Verifica una publicación para ver la ruta.", lx + 4, y, 256,
                    12, c["aviso"], peso=800, max_lineas=4) + 8
        texto(sup, "Rotaciones recientes", (lx + 4, y), 15, c["texto"], peso=900)
        y += 24
        for l in (archivo.bitacora[-4:] or ["Todavía ninguna"]):
            y = parrafo(sup, l, lx + 4, y, 256, 12, c["tinta2"], peso=700)
        self.b_cerrar.dibujar(sup)


class SecuenciaNoche:
    """La noche: la ola de propagación recorre la red y luego se resumen los eventos."""
    bloquea = True

    def __init__(self, juego, dia, mensajes):
        self.j = juego
        self.dia = dia
        self.mensajes = [m for m in mensajes if m.tipo in ("evento", "malo", "bueno", "logro")
                         and not m.texto.startswith(("Turno de", "Día "))]
        self.t0 = pygame.time.get_ticks()
        self.rect = pygame.Rect(0, 0, 560, 360)
        self.rect.center = juego.r_centro.center
        self.b_ok = Boton((self.rect.x + 24, self.rect.bottom - 70, self.rect.w - 48, 52),
                          "", "ok", icono="sun", estilo="primario", tam=18)
        juego.app.sonar("noche")

    def listo(self):
        return pygame.time.get_ticks() - self.t0 > (900 if TEMA.op["menos_movimiento"] else 3400)

    def evento(self, e):
        if not self.listo():
            if e.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                self.t0 -= 10_000
            return
        if (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.b_ok.clic(e.pos)) or \
                (e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE)):
            self.j.terminar_noche()

    def dibujar(self, sup):
        c = TEMA.c
        p = self.j.p
        e = (pygame.time.get_ticks() - self.t0) / 1000
        centro = self.j.r_centro
        alpha = round(min(1, e / 0.6) * 150)
        base, ox = lienzo_total(sup)
        capa = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        capa.fill((20, 18, 60, alpha))
        capa.fill((20, 18, 60, alpha // 3), centro.move(ox, 0))
        base.blit(capa, (0, 0))
        leyenda = f"Noche del día {self.dia}: las publicaciones viajan"
        etiqueta = pygame.Rect(0, 0, ancho_texto(leyenda, 14, 900) + 72, 50)
        etiqueta.midtop = (centro.centerx, centro.y + 8)
        sticker(sup, etiqueta, c["tinta"] if not TEMA.alto_contraste else (0, 0, 0), 25, 0, 3,
                color_borde=c["papel"] if not TEMA.alto_contraste else c["mango"])
        sup.blit(recursos.icono("moon", 24, c["mango"], 2.6), (etiqueta.x + 18, etiqueta.y + 13))
        texto(sup, leyenda, (etiqueta.x + 52, etiqueta.centery), 14, (255, 255, 255), peso=900, ancla="ml")
        if not self.listo():
            return
        r = self.rect
        sticker(sup, r, c["papel"], 24, 7, 3)
        titulo(sup, f"Amanece el día {min(self.dia + 1, p.rondas_totales)}" if not p.terminada else "Último día",
               (r.x + 24, r.y + 20), 28, c["texto"])
        faltan = p.rondas_totales - p.ronda
        texto(sup, "Esta noche se acaba la campaña: mañana se vota." if faltan <= 0 else
              "Falta 1 día para la elección." if faltan == 1 else f"Faltan {faltan} días para la elección.",
              (r.x + 26, r.y + 60), 14, c["tinta2"], peso=800)
        y = r.y + 92
        for m in self.mensajes[-5:]:
            ic = {"evento": "sparkles", "malo": "triangle-alert", "bueno": "circle-check", "logro": "trophy"}[m.tipo]
            col = {"evento": c["acento"], "malo": c["malo"], "bueno": c["bueno"], "logro": c["logro"]}[m.tipo]
            sup.blit(recursos.icono(ic, 18, col, 2.6), (r.x + 24, y + 1))
            y = parrafo(sup, m.texto, r.x + 52, y, r.w - 78, 13, c["texto"], peso=700, max_lineas=2) + 6
            if y > self.b_ok.rect.y - 24:
                break
        self.b_ok.etiqueta = "Ver la elección" if p.terminada else "Empezar el día"
        self.b_ok.dibujar(sup)


class BannerTurno:
    bloquea = False

    def __init__(self, juego, jugador, propio=None):
        self.j = juego
        self.jug = jugador
        self.propio = propio
        self.t0 = pygame.time.get_ticks()
        juego.app.sonar("turno")

    def vivo(self):
        return pygame.time.get_ticks() - self.t0 < 1900

    def dibujar(self, sup):
        c = TEMA.c
        e = (pygame.time.get_ticks() - self.t0) / 1900
        if e >= 1:
            return
        centro = self.j.r_centro
        r = pygame.Rect(0, 0, centro.w - 40, 150)
        r.center = (centro.centerx, centro.centery - 20)
        if not TEMA.op["menos_movimiento"]:
            r.x += round((1 - suave(min(1, e * 4))) * -80 + max(0, e - 0.8) * 5 * 120)
        alpha = 255 if e < 0.8 else round(255 * (1 - (e - 0.8) / 0.2))
        capa = pygame.Surface((r.w + 12, r.h + 16), pygame.SRCALPHA)
        sticker(capa, (4, 4, r.w, r.h), c["papel"], 26, 7, 3)
        pygame.draw.rect(capa, self.jug.color, (7, 7, 150, r.h - 6), border_top_left_radius=23,
                         border_bottom_left_radius=23)
        img = personajes.cuerpo(self.jug.look, self.jug.rol, "feliz", alto=150, color_extra=(58, 110, 230))
        capa.blit(img, (82 - img.get_width() // 2, 0))
        if self.propio is True:
            t = "¡Es tu turno!"
        elif self.propio is False:
            t = f"Turno de {self.jug.nombre}"
        else:
            t = f"Turno de {self.jug.nombre}"
        titulo(capa, t, (180, 34), 34, c["texto"])
        texto(capa, f"{self.jug.info_rol['nombre']}: te llegó una publicación. ¿Qué harás con ella?", (182, 86), 15,
              c["tinta2"], peso=800)
        capa.set_alpha(alpha)
        sup.blit(capa, (r.x - 4, r.y - 4))

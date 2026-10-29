"""El celular con la app Civitas: historias, la publicación elegida y los botones de acción."""

import pygame

from ..modelo.mapa import nombre_zona
from . import personajes, recursos
from .ayuda import ICONO_ROL
from .juego_comun import cara, color_caso, color_estado, estado_nodo
from .tema import TEMA
from .widgets import Boton, chip, circulo, forma_estado, parrafo, recortar, sticker, texto

ICONOS = dict(verificar="search", compartir="share-2", reportar="flag", ignorar="eye-off", borrar="trash-2")
NOMBRE_ESTADO = dict(nada="Sin verificar", veraz="Verdadera", falso="Falsa", correccion="Desmentido")


class Celular:
    def __init__(self, juego, rect):
        self.j = juego
        self.rect = pygame.Rect(rect)
        self.pantalla = self.rect.inflate(-18, -18)
        s = self.pantalla
        self.r_historias = pygame.Rect(s.x + 10, s.y + 70, s.w - 20, 56)
        self.r_post = pygame.Rect(s.x + 10, s.y + 134, s.w - 20, s.h - 134 - 222)
        self.r_acciones = pygame.Rect(s.x + 10, s.bottom - 214, s.w - 20, 200)
        self.historias = []
        self.botones = []
        self.b_prev = Boton((0, 0, 30, 28), "", "prev", icono="chevron-left", sombra=0, radio=10)
        self.b_next = Boton((0, 0, 30, 28), "", "next", icono="chevron-right", sombra=0, radio=10)
        self.hover_accion = None
        self._armar_botones()

    @property
    def p(self):
        return self.j.p

    def _armar_botones(self):
        a = self.r_acciones
        w = (a.w - 8) // 2
        y = a.y + 30
        self.botones = [
            Boton((a.x, y, w, 46), "Verificar", "verificar", icono="search", tam=17, sombra=3),
            Boton((a.x + w + 8, y, w, 46), "Compartir", "compartir", icono="share-2", tam=17, sombra=3),
            Boton((a.x, y + 54, w, 46), "Reportar", "reportar", icono="flag", tam=17, sombra=3),
            Boton((a.x + w + 8, y + 54, w, 46), "Ignorar", "ignorar", icono="eye-off", tam=17, sombra=3),
            Boton((a.x, y + 108, a.w, 48), "Especial", "especial", icono="sparkles", tam=16,
                  estilo="especial", sombra=3),
            Boton((a.right - 52, y + 108, 52, 48), "", "borrar", icono="trash-2", sombra=3),
        ]
        for b in self.botones:
            b.clave_real = b.clave

    # ------------------------------------------------------------------ eventos
    def evento(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for r, caso_id, nodo_id in self.historias:
                if r.collidepoint(e.pos):
                    self.j.seleccionar(caso_id, nodo_id)
                    self.j.app.sonar("pop")
                    return True
            if self.b_prev.clic(e.pos):
                self.j.mover_seleccion(-1)
                return True
            if self.b_next.clic(e.pos):
                self.j.mover_seleccion(1)
                return True
            for b in self.botones:
                if b.clic(e.pos):
                    self.j.accion(b.clave_real)
                    return True
            return self.rect.collidepoint(e.pos)
        if e.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            self.j.mover_seleccion(-1 if e.y > 0 else 1)
            return True
        return False

    def tecla(self, k):
        if 0 <= k < 6:
            b = self.botones[k]
            if b.visible and b.activo:
                self.j.accion(b.clave_real)
                return True
        return False

    # ------------------------------------------------------------------ dibujo
    def dibujar(self, sup):
        c = TEMA.c
        p = self.p
        sticker(sup, self.rect, c["tinta"] if not TEMA.alto_contraste else c["papel2"], 42, 6, 3)
        s = self.pantalla
        sticker(sup, s, c["papel"], 34, 0, 0)
        notch = pygame.Rect(0, 0, 96, 20)
        notch.midtop = (s.centerx, s.y + 6)
        pygame.draw.rect(sup, c["tinta"], notch, border_radius=10)
        texto(sup, f"Día {min(p.ronda, p.rondas_totales)}", (s.x + 26, s.y + 16), 12, c["texto"], peso=900, ancla="ml")
        sup.blit(recursos.icono("wifi", 14, c["texto"], 2.6), (s.right - 64, s.y + 9))
        bat = pygame.Rect(s.right - 44, s.y + 10, 22, 12)
        pygame.draw.rect(sup, c["texto"], bat, 2, border_radius=3)
        pygame.draw.rect(sup, c["bueno"], bat.inflate(-6, -6), border_radius=1)
        pygame.draw.rect(sup, c["texto"], (bat.right, bat.y + 4, 2, 4))
        # encabezado de la app
        civi = personajes.civi("feliz", 40)
        sup.blit(civi, (s.x + 14, s.y + 26))
        texto(sup, "Civitas", (s.x + 46, s.y + 48), 24, c["acento"], peso=700, fam="titulo", ancla="ml")
        feed = self.j.feed()
        chip(sup, f"Para ti ({len(feed)})", (s.right - 14, s.y + 48), c["acento2"], c["acento"], None, 12, ancla="mr")
        self._historias(sup, feed)
        n, caso = self.j.nodo_sel(), self.j.caso_sel()
        if n is None:
            r = self.r_post
            parrafo(sup, "Tu feed está tranquilo. Revisa el mapa: quizá hay vecinos con los que conversar.",
                    r.x + 10, r.y + 40, r.w - 20, 15, c["tinta2"], peso=700, centrado=True)
        else:
            self._post(sup, n, caso, feed)
        self._acciones(sup, n, caso)
        pygame.draw.rect(sup, c["tinta"], (s.centerx - 50, s.bottom - 10, 100, 5), border_radius=3)

    def _historias(self, sup, feed):
        c = TEMA.c
        p = self.p
        self.historias = []
        sel = self.j.sel
        r = self.r_historias
        tam = 42
        paso = 48
        visibles = feed[:6]
        if sel and sel not in [(cs.id, n.id) for cs, n, _ in visibles]:
            for k, (cs, n, tag) in enumerate(feed):
                if (cs.id, n.id) == sel:
                    visibles = feed[max(0, k - 5):k + 1]
                    break
        for i, (cs, n, tag) in enumerate(visibles):
            x = r.x + 4 + i * paso
            y = r.y + 4
            elegido = sel == (cs.id, n.id)
            col = color_caso(cs.id)
            pygame.draw.circle(sup, col, (x + tam // 2, y + tam // 2), tam // 2 + 3)
            if elegido:
                pygame.draw.circle(sup, c["tinta"], (x + tam // 2, y + tam // 2), tam // 2 + 6, 3)
            img = cara(self.p, n.autor, tam - 4, borde=c["papel"], grosor=2)
            sup.blit(img, (x + 2, y + 2))
            forma_estado(sup, estado_nodo(n), (x + tam - 4, y + tam - 4), 5)
            if n.viral:
                circulo(sup, (x + 6, y + 6), 8, c["mango"], c["borde"], 2)
                sup.blit(recursos.icono("flame", 11, c["texto"], 2.6), (x + 1, y + 1))
            self.historias.append((pygame.Rect(x, y, tam, tam), cs.id, n.id))
        if not feed:
            texto(sup, "Sin publicaciones nuevas", r.center, 13, c["tenue"], peso=800, ancla="c")

    def _post(self, sup, n, caso, feed):
        c = TEMA.c
        p = self.p
        r = self.r_post
        sticker(sup, r, c["papel2"], 18, 0, 2)
        x, y = r.x + 12, r.y + 12
        sup.blit(cara(p, n.autor, 42), (x, y))
        texto(sup, recortar(str(n.autor), 16, 150, 900), (x + 50, y + 2), 16, c["texto"], peso=900)
        sub = "Publicó primero" if n.es_raiz else f"Reenvío de {n.padre.autor}"
        texto(sup, recortar(sub, 12, 150, 700), (x + 50, y + 23), 12, c["tinta2"], peso=700)
        idx = next((k for k, (cs, m, _) in enumerate(feed) if m is n), 0)
        self.b_prev.rect.topleft = (r.right - 72, y + 6)
        self.b_next.rect.topleft = (r.right - 38, y + 6)
        self.b_prev.activo = idx > 0
        self.b_next.activo = idx < len(feed) - 1
        self.b_prev.dibujar(sup)
        self.b_next.dibujar(sup)
        texto(sup, f"{idx + 1} de {len(feed)}", (r.right - 38, y + 44), 11, c["tinta2"], peso=800, ancla="c")
        y += 50
        tag = next((t for cs, m, t in feed if m is n), "")
        circulo(sup, (x + 6, y + 9), 6, color_caso(caso.id))
        texto(sup, recortar(f"{caso.hecho.titulo}", 12, r.w - 40, 800), (x + 18, y + 1), 12, c["tinta2"], peso=800)
        y += 22
        est = estado_nodo(n)
        col = color_estado(est)
        forma_estado(sup, est, (x + 8, y + 12), 7)
        rr = chip(sup, NOMBRE_ESTADO[est], (x + 22, y), col if est != "nada" else c["papel"],
                  c["sobre_color"] if est != "nada" else c["texto"], None, 13)
        xx = rr.right + 6
        if tag:
            rr = chip(sup, tag, (xx, y), c["acento2"], c["acento"], None, 12)
            xx = rr.right + 6
        if n.inmune and not n.es_correccion:
            rr = chip(sup, "Contenida", (xx, y), c["bueno2"], c["bueno"], "shield-check", 12)
            xx = rr.right + 6
        if n.viral:
            chip(sup, "Viral", (xx, y), c["mango"], c["texto"], "flame", 12)
        y += 34
        tam = 17 if TEMA.op["texto_grande"] else 15
        inter = 4 if TEMA.op["texto_grande"] else 6
        lineas_max = max(2, (r.bottom - 34 - y) // (tam + inter))
        parrafo(sup, n.afirmacion.texto(), x, y, r.w - 24, tam, c["texto"], interlineado=inter, peso=600,
                max_lineas=lineas_max)
        yb = r.bottom - 26
        sup.blit(recursos.icono("eye", 15, c["tinta2"], 2.4), (x, yb))
        t1 = texto(sup, f"le llegó a {n.alcance}", (x + 20, yb + 7), 12, c["tinta2"], peso=800, ancla="ml")
        sup.blit(recursos.icono("repeat-2", 15, c["tinta2"], 2.4), (t1.right + 14, yb))
        texto(sup, f"{len(n.hijos)} reenvíos", (t1.right + 34, yb + 7), 12, c["tinta2"], peso=800, ancla="ml")

    def _vista_previa(self, clave, n, caso):
        p = self.p
        j = p.jugador_actual
        if n is None or caso is None:
            return ""
        if clave == "verificar":
            if caso.hecho.id in p.archivo:
                return "Busca el hecho en el Archivo (árbol AVL) y te muestra qué cambió."
            if j.rol == "periodista":
                return "Ese hecho no está en el Archivo: como periodista lo investigas y lo registras."
            if j.zona == caso.hecho.lugar:
                return "No está en el Archivo, pero estás en el lugar: lo compruebas y lo registras."
            return f"Ese hecho no está en el Archivo. Ve a {nombre_zona(caso.hecho.lugar)} o pídele ayuda a un periodista."
        if clave == "compartir":
            k = p.red.grado_salida(j.nombre) if j.nombre in p.red else 0
            extra = "" if (n.verificado or n.es_correccion) else " Ojo: aún no la verificas."
            return f"Le llega a tus {k} seguidores.{extra}"
        if clave == "reportar":
            alc = caso.arbol.agregar(lambda m: m.alcance, n)[n.id]
            tam = len(list(caso.arbol.preorden(n)))
            return f"Retira esta y {tam - 1} reenvíos (le llegaron a {alc} personas)."
        if clave == "ignorar":
            return "La dejas pasar sin alimentarla."
        if clave == "alertar":
            return f"Avisa a tus {len(p.red.contactos(j.nombre))} contactos de la red."
        if clave == "rastrear":
            return f"Sube {n.profundidad} saltos hasta el origen y expone al paciente cero."
        if clave == "amplificar":
            return "Corrige a quienes están a uno o dos saltos de ti y contiene la rama."
        if clave == "desmentir":
            return "Convence a quien confía en ti por algún camino de la red."
        if clave == "borrar":
            return "Quitas tu publicación, pero sus reenvíos siguen circulando."
        return ""

    def _acciones(self, sup, n, caso):
        c = TEMA.c
        p = self.p
        j = p.jugador_actual
        a = self.r_acciones
        acciones = {x["clave"]: x for x in p.acciones_para(n)}
        esp_clave, esp_nombre, esp_costo = j.info_rol["especial"]
        puedo = self.j.puedo_actuar()
        raton = pygame.mouse.get_pos()
        hint, hint_col = "", c["tinta2"]
        for b in self.botones:
            clave = esp_clave if b.clave == "especial" else b.clave
            b.clave_real = clave
            info = acciones.get(clave)
            b.visible = info is not None or b.clave != "borrar"
            if b.clave == "especial":
                b.etiqueta = esp_nombre
                b.icono = ICONO_ROL[j.rol]
                b.costo = esp_costo
                b.rect.w = a.w - (60 if "borrar" in acciones else 0)
            if not b.visible:
                continue
            b.activo = bool(info and info["ok"]) and puedo
            if b.rect.collidepoint(raton):
                if not puedo:
                    hint, hint_col = self.j.motivo_espera(), c["aviso"]
                elif info and not info["ok"]:
                    hint, hint_col = info["motivo"], c["aviso"]
                else:
                    hint = self._vista_previa(clave, n, caso)
            b.dibujar(sup)
        if not hint:
            if not puedo:
                hint, hint_col = self.j.motivo_espera(), c["aviso"]
            elif j.atencion == 0:
                hint, hint_col = "Sin atención: termina tu turno.", c["aviso"]
            else:
                hint = "Cada acción gasta 1 rayo de atención." + (f" La especial gasta {esp_costo}." if esp_costo > 1 else "")
        parrafo(sup, hint, a.x + 2, a.y - 2, a.w, 12, hint_col, peso=800, max_lineas=2, interlineado=2)

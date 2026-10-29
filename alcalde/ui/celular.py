"""El celular con la app Civitas: la publicación que te tocó este turno y qué hacer con ella."""

import pygame

from ..modelo.mapa import ZONAS, nombre_zona
from ..modelo.partida import COSTO_MIN_DECIDIR, COSTO_MIN_VERIFICAR, PUBS_POR_TURNO
from . import personajes, recursos
from .ayuda import ICONO_ROL
from .juego_comun import cara, color_caso, color_estado, estado_nodo
from .tema import TEMA
from .widgets import Boton, chip, circulo, forma_estado, parrafo, recortar, sticker, texto

NOMBRE_ESTADO = dict(nada="Sin verificar", veraz="Verdadera", falso="Falsa", correccion="Desmentido")
ESPECIALES = ("alertar", "rastrear", "amplificar", "desmentir")
CORTO = dict(alertar="Alertar", rastrear="Rastrear", amplificar="Amplificar", desmentir="Desmentir")


def veredicto(resultado):
    """(tipo, título, explicación) para contar qué pasó con la decisión del jugador."""
    veraz, d = resultado["veraz"], resultado["decision"]
    frenar = d == "reportar" or d in ESPECIALES
    if not veraz and frenar:
        return "bueno", "¡Bien hecho!", "Era falsa y la frenaste."
    if not veraz and d == "ignorar":
        return "regular", "Más o menos", "Era falsa. No la alimentaste, pero reportarla la habría frenado."
    if not veraz:
        return "malo", "¡Uy!", "Era falsa y la ayudaste a circular."
    if d == "compartir":
        return "bueno", "¡Bien hecho!", "Era verdadera y la compartiste."
    if d == "ignorar":
        return "regular", "Más o menos", "Era verdadera: valía la pena compartirla."
    if d == "rastrear":
        return "regular", "Era verdadera", "El rastreo mostró que nadie la torció."
    return "malo", "¡Uy!", "Era verdadera y la trataste como falsa."


class Celular:
    def __init__(self, juego, rect):
        self.j = juego
        self.rect = pygame.Rect(rect)
        self.pantalla = self.rect.inflate(-18, -18)
        s = self.pantalla
        self.r_post = pygame.Rect(s.x + 10, s.y + 96, s.w - 20, 262)
        a = pygame.Rect(s.x + 10, self.r_post.bottom + 12, s.w - 20, s.bottom - self.r_post.bottom - 30)
        self.r_acciones = a
        w = (a.w - 8) // 2
        self.b_verificar = Boton((a.x, a.y, a.w, 50), "Verificar (3 pts · 2 min)", "verificar", icono="search",
                                 estilo="primario", tam=17)
        y = a.y + 92
        self.botones = [
            Boton((a.x, y, w, 50), "Compartir", "compartir", icono="share-2", tam=17, sombra=3),
            Boton((a.x + w + 8, y, w, 50), "Reportar", "reportar", icono="flag", tam=17, sombra=3),
            Boton((a.x, y + 58, w, 50), "Ignorar", "ignorar", icono="eye-off", tam=17, sombra=3),
            Boton((a.x + w + 8, y + 58, w, 50), "Especial", "especial", icono="sparkles", tam=15,
                  estilo="especial", sombra=3),
        ]
        for b in [self.b_verificar] + self.botones:
            b.clave_real = b.clave
        self.b_sig = Boton((a.x + 12, a.bottom - 70, a.w - 24, 46), "Siguiente publicación", "siguiente",
                           icono="arrow-right", estilo="primario", tam=16)
        self.b_sig.visible = False

    @property
    def p(self):
        return self.j.p

    # ------------------------------------------------------------------ eventos
    def evento(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.b_sig.visible and self.b_sig.clic(e.pos):
                self.j.siguiente()
                return True
            for b in [self.b_verificar] + self.botones:
                if b.visible and b.clic(e.pos):
                    self.j.accion(b.clave_real)
                    return True
            return self.rect.collidepoint(e.pos)
        return False

    def tecla(self, k):
        botones = [self.b_verificar] + self.botones
        if 0 <= k < len(botones):
            b = botones[k]
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
        sup.blit(personajes.civi("feliz", 40), (s.x + 14, s.y + 26))
        texto(sup, "Civitas", (s.x + 46, s.y + 48), 24, c["acento"], peso=700, fam="titulo", ancla="ml")
        jugador = p.jugador_actual
        caso, n = p.publicacion_turno()
        zona = p.zona_de(n) if n is not None else None
        desde = f" desde {nombre_zona(zona)}" if zona in ZONAS else ""
        titulo = f"Te llegó{desde}" if self.j.puedo_actuar() or not self.j.en_red() else \
            f"Le llegó a {jugador.nombre}{desde}"
        texto(sup, recortar(titulo, 14, s.w - 30, 900), (s.x + 16, s.y + 80), 14, c["tinta2"], peso=900, ancla="ml")
        resultado = p.turno.get("resultado")
        # Al reportar o desmentir, Civitas retira la publicación: el resultado se muestra igual.
        caso_res = p.caso_por_id(resultado["caso"]) if resultado else None
        if n is None:
            r = self.r_post
            sticker(sup, r, c["papel2"], 18, 0, 2)
            parrafo(sup, "Esa publicación ya no está en Civitas." if resultado else
                    "Hoy no te llegó ninguna publicación nueva. Camina por la ciudad o termina tu turno.",
                    r.x + 16, r.y + 90, r.w - 32, 15, c["tinta2"], peso=700, centrado=True)
        else:
            self._post(sup, n, caso)
        self.b_sig.visible = False
        if resultado and caso_res is not None:
            self._resultado(sup, resultado, caso_res)
        else:
            self._acciones(sup, n, caso)
        pygame.draw.rect(sup, c["tinta"], (s.centerx - 50, s.bottom - 10, 100, 5), border_radius=3)

    def _post(self, sup, n, caso):
        c = TEMA.c
        p = self.p
        r = self.r_post
        sticker(sup, r, c["papel2"], 18, 0, 2)
        x, y = r.x + 14, r.y + 14
        sup.blit(cara(p, n.autor, 48), (x, y))
        texto(sup, recortar(str(n.autor), 17, r.w - 90, 900), (x + 58, y + 4), 17, c["texto"], peso=900)
        sub = "Publicó primero" if n.es_raiz else f"Lo reenvió de {n.padre.autor}"
        texto(sup, recortar(sub, 12, r.w - 90, 700), (x + 58, y + 27), 12, c["tinta2"], peso=700)
        y += 60
        circulo(sup, (x + 6, y + 8), 6, color_caso(caso.id))
        texto(sup, recortar(caso.hecho.titulo, 12, r.w - 44, 800), (x + 18, y), 12, c["tinta2"], peso=800)
        y += 24
        if n.verificado:
            est = estado_nodo(n)
            forma_estado(sup, est, (x + 8, y + 12), 7)
            chip(sup, NOMBRE_ESTADO[est], (x + 22, y), color_estado(est), c["sobre_color"], None, 13)
            y += 32
        tam = 18 if TEMA.op["texto_grande"] else 16
        lineas_max = max(2, (r.bottom - 14 - y) // (tam + 6))
        parrafo(sup, n.afirmacion.texto(), x, y, r.w - 28, tam, c["texto"], interlineado=6, peso=600,
                max_lineas=lineas_max)

    def _vista_previa(self, clave, n, caso):
        p = self.p
        j = p.jugador_actual
        if n is None or caso is None:
            return ""
        if clave == "verificar":
            if caso.hecho.id in p.archivo:
                return "Te dice si es verdadera o falsa y qué le cambiaron. ¿Te acuerdas de esta historia? Ahórrate los puntos."
            if j.rol == "periodista":
                return "No está en el Archivo, pero como periodista lo investigas."
            if j.zona == caso.hecho.lugar:
                return "No está en el Archivo, pero estás en el lugar: lo compruebas en persona."
            return f"Este hecho no está en el Archivo: ve a {nombre_zona(caso.hecho.lugar)} para verificarlo."
        if clave == "compartir":
            k = p.red.grado_salida(j.nombre) if j.nombre in p.red else 0
            return f"Se la mandas a tus {k} seguidores. Gana si es verdadera. Decidir cuesta {COSTO_MIN_DECIDIR} min."
        if clave == "reportar":
            return f"Civitas la borra con sus reenvíos. Gana si es falsa. Decidir cuesta {COSTO_MIN_DECIDIR} min."
        if clave == "ignorar":
            return f"No haces nada con ella. Decidir cuesta {COSTO_MIN_DECIDIR} min."
        if clave in ESPECIALES:
            return j.info_rol["descripcion"] + " Solo sirve si es falsa."
        return ""

    def _acciones(self, sup, n, caso):
        c = TEMA.c
        p = self.p
        j = p.jugador_actual
        a = self.r_acciones
        acciones = {x["clave"]: x for x in p.acciones_para(n)}
        esp_clave, esp_nombre, _ = j.info_rol["especial"]
        puedo = self.j.puedo_actuar()
        raton = pygame.mouse.get_pos()
        hint, hint_col = "", c["tinta2"]
        texto(sup, "¿Qué haces con ella?", (a.x + 2, a.y + 66), 14, c["texto"], peso=900)
        for b in [self.b_verificar] + self.botones:
            clave = esp_clave if b.clave == "especial" else b.clave
            b.clave_real = clave
            info = acciones.get(clave)
            if b.clave == "especial":
                b.etiqueta = CORTO.get(esp_clave, esp_nombre)
                b.icono = ICONO_ROL[j.rol]
            b.activo = bool(info and info["ok"]) and puedo
            if b is self.b_verificar:
                b.etiqueta = ("Ya está verificada" if (n is not None and n.verificado)
                              else f"Verificar (3 pts · {COSTO_MIN_VERIFICAR} min)")
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
            else:
                hint, hint_col = self._presencia(n)
        parrafo(sup, hint, a.x + 2, self.botones[-1].rect.bottom + 10, a.w, 12, hint_col, peso=800, max_lineas=2,
                interlineado=2)

    def _presencia(self, n):
        """Dónde estás respecto a la zona del rumor: aquí, frenarlo rinde completo; lejos, la mitad."""
        c = TEMA.c
        p = self.p
        zona = p.zona_de(n) if n is not None else None
        if zona not in ZONAS:
            return "Si no te acuerdas si es verdad, verifícala primero.", c["tinta2"]
        j = p.jugador_actual
        if zona == j.zona:
            return f"Estás en {nombre_zona(zona)}: aquí frenar un rumor rinde completo.", c["bueno"]
        d = p.distancias().get(zona)
        lejos = f" ({int(d)} min)" if d is not None else ""
        return (f"Estás lejos de {nombre_zona(zona)}{lejos}: frenar este rumor desde aquí rinde la mitad. "
                "Camina hasta allá para que rinda completo."), c["aviso"]

    def _resultado(self, sup, resultado, caso):
        c = TEMA.c
        a = self.r_acciones
        tipo, titulo, cuerpo = veredicto(resultado)
        col = {"bueno": c["bueno"], "malo": c["malo"]}.get(tipo, c["aviso"])
        fondo = {"bueno": c["bueno2"], "malo": c["malo2"]}.get(tipo, c["mango2"])
        r = pygame.Rect(a.x, a.y, a.w, a.h - 4)
        sticker(sup, r, fondo, 18, 3, 3)
        circulo(sup, (r.x + 32, r.y + 32), 20, col, c["borde"], 2)
        icono = {"bueno": "check", "malo": "x"}.get(tipo, "info")
        sup.blit(recursos.icono(icono, 24, c["sobre_color"], 3), (r.x + 20, r.y + 20))
        texto(sup, titulo, (r.x + 62, r.y + 14), 20, c["texto"], peso=700, fam="titulo")
        pts = resultado["puntos"]
        texto(sup, f"{pts:+d} puntos", (r.right - 14, r.y + 20), 15, col, peso=900, ancla="tr")
        y = parrafo(sup, cuerpo, r.x + 62, r.y + 42, r.w - 76, 14, c["texto"], peso=800, max_lineas=3) + 6
        texto(sup, "Para recordar, el hecho real:", (r.x + 16, y), 12, c["tinta2"], peso=900)
        parrafo(sup, caso.hecho.afirmacion_real().texto(), r.x + 16, y + 18, r.w - 32, 13, c["tinta2"], peso=700,
                max_lineas=3)
        p = self.p
        ok, motivo = p.puede_siguiente()
        j = p.jugador_actual
        if ok:
            self.b_sig.rect.midbottom = (r.centerx, r.bottom - 26)
            self.b_sig.etiqueta = f"Siguiente publicación ({p.turno.get('atendidas', 0) + 1} de {PUBS_POR_TURNO})"
            self.b_sig.visible = self.j.puedo_actuar()
            self.b_sig.activo = self.b_sig.visible
            self.b_sig.dibujar(sup)
            texto(sup, f"Te quedan {j.minutos} min. También puedes caminar.", (r.centerx, r.bottom - 12), 11,
                  c["texto"], peso=900, ancla="c")
        else:
            texto(sup, recortar(motivo + ". Termina tu turno." if p.turno.get("atendidas", 0) >= PUBS_POR_TURNO
                                else motivo, 12, r.w - 24, 900), (r.centerx, r.bottom - 16), 12, c["texto"],
                  peso=900, ancla="c")

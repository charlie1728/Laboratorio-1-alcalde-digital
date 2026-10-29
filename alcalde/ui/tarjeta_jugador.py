"""Tarjeta para armar un personaje: nombre, rol y apariencia (se usa en local y en el lobby)."""
import math

import pygame

from ..modelo.apariencia import COLORES_PELO, EXTRAS, PEINADOS, TONOS_PIEL, normalizar
from ..modelo.roles import ORDEN_ROLES, ROLES
from . import personajes, recursos
from .ayuda import ICONO_ROL
from .tema import TEMA
from .widgets import Boton, chip, parrafo, recortar, sticker, texto

NOMBRES_PEINADO = dict(corto="Corto", rapado="Rapado", afro="Afro", largo="Largo", cola="Cola",
                       mono="Moño", ondulado="Ondulado", trenzas="Trenzas", calvo="Calvo")
NOMBRES_EXTRA = {"": "Ninguno", "gafas": "Gafas", "barba": "Barba", "bigote": "Bigote",
                 "aretes": "Aretes", "gorra": "Gorra"}


class TarjetaJugador:
    def __init__(self, rect, indice, color, nombre, rol, look, opcional=False, activo=True):
        self.rect = pygame.Rect(rect)
        self.i = indice
        self.color = color
        self.nombre = nombre
        self.rol = rol
        self.look = normalizar(look)
        self.opcional = opcional
        self.activo = activo
        self.editando = False
        self.personalizar = False
        self.cambio = False
        r = self.rect
        self.r_nombre = pygame.Rect(r.x + 16, r.y + 244, r.w - 32, 40)
        self.b_izq = Boton((r.x + 16, r.y + 292, 40, 40), "", "izq", icono="chevron-left", sombra=3)
        self.b_der = Boton((r.right - 56, r.y + 292, 40, 40), "", "der", icono="chevron-right", sombra=3)
        self.b_pers = Boton((r.right - 58, r.y + 184, 44, 40), "", "pers", icono="wand-sparkles", sombra=3,
                            estilo="especial")
        self.b_quitar = Boton((r.right - 44, r.y + 10, 32, 28), "", "quitar", icono="x", sombra=0, radio=10)
        self.b_agregar = Boton((r.x + 40, r.centery - 30, r.w - 80, 60), "Agregar jugador", "agregar",
                               icono="plus", tam=17)
        self.t0 = pygame.time.get_ticks() + indice * 700

    # ------------------------------------------------------------------ datos
    def perfil(self) -> dict:
        return dict(nombre=self.nombre.strip() or f"Jugador {self.i + 1}", rol=self.rol, look=dict(self.look))

    def _filas_look(self):
        r = self.rect
        y = r.y + 344
        return [("piel", y), ("pelo", y + 33), ("color_pelo", y + 66), ("ropa", y + 99), ("extra", y + 132)]

    def _muestras(self, clave, y):
        r = self.rect
        n = {"piel": TONOS_PIEL, "color_pelo": COLORES_PELO, "ropa": 8}[clave]
        x0 = r.x + 82
        paso = min(26, (r.w - 98) // n)
        return [(k, pygame.Rect(x0 + k * paso, y, paso - 4, 24)) for k in range(n)]

    # ------------------------------------------------------------------ eventos
    def evento(self, e, sonar=lambda *_: None) -> bool:
        """Devuelve True si la tarjeta consumió el evento."""
        self.cambio = False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if not self.activo:
                if self.opcional and self.b_agregar.clic(e.pos):
                    self.activo = True
                    self.cambio = True
                    sonar("pop")
                    return True
                return False
            self.editando = self.r_nombre.collidepoint(e.pos)
            if self.editando:
                if self.nombre == f"Jugador {self.i + 1}":
                    self.nombre = ""
                return True
            if self.opcional and self.b_quitar.clic(e.pos):
                self.activo = False
                self.cambio = True
                sonar("click")
                return True
            for b, paso in ((self.b_izq, -1), (self.b_der, 1)):
                if b.clic(e.pos):
                    k = (ORDEN_ROLES.index(self.rol) + paso) % len(ORDEN_ROLES)
                    self.rol = ORDEN_ROLES[k]
                    self.cambio = True
                    sonar("click")
                    return True
            if self.b_pers.clic(e.pos):
                self.personalizar = not self.personalizar
                sonar("click")
                return True
            if self.personalizar:
                for clave, y in self._filas_look():
                    if clave in ("pelo", "extra"):
                        opciones = PEINADOS if clave == "pelo" else EXTRAS
                        izq = pygame.Rect(self.rect.x + 80, y, 28, 26)
                        der = pygame.Rect(self.rect.right - 44, y, 28, 26)
                        for rr, paso in ((izq, -1), (der, 1)):
                            if rr.collidepoint(e.pos):
                                k = (opciones.index(self.look[clave]) + paso) % len(opciones)
                                self.look[clave] = opciones[k]
                                self.cambio = True
                                sonar("click")
                                return True
                    else:
                        for k, rr in self._muestras(clave, y):
                            if rr.collidepoint(e.pos):
                                self.look[clave] = k
                                self.cambio = True
                                sonar("click")
                                return True
            return self.rect.collidepoint(e.pos)
        if e.type == pygame.KEYDOWN and self.editando:
            if e.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_TAB, pygame.K_KP_ENTER):
                self.editando = False
            elif e.key == pygame.K_BACKSPACE:
                self.nombre = self.nombre[:-1]
            elif e.unicode and e.unicode.isprintable() and len(self.nombre) < 14:
                self.nombre += e.unicode
            self.cambio = True
            return True
        return False

    # ------------------------------------------------------------------ dibujo
    def dibujar(self, sup, etiqueta=None, solo_lectura=False):
        c = TEMA.c
        r = self.rect
        t = (pygame.time.get_ticks() - self.t0) / 1000
        mov = not TEMA.op["menos_movimiento"]
        if not self.activo:
            capa = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(capa, (*c["papel"], 120), capa.get_rect(), border_radius=22)
            sup.blit(capa, r)
            pygame.draw.rect(sup, c["tinta2"], r, 3, border_radius=22)
            texto(sup, f"Puesto {self.i + 1} libre", (r.centerx, r.centery - 64), 17, c["tinta2"], peso=800, ancla="c")
            self.b_agregar.dibujar(sup)
            return
        sticker(sup, r, c["papel"], 22, 6, 3)
        banda = pygame.Rect(r.x + 2, r.y + 2, r.w - 4, 46)
        pygame.draw.rect(sup, self.color, banda, border_top_left_radius=20, border_top_right_radius=20)
        pygame.draw.line(sup, c["tinta"], (r.x + 1, banda.bottom), (r.right - 2, banda.bottom), 3)
        texto(sup, etiqueta or f"Jugador {self.i + 1}", (r.x + 18, banda.centery + 1), 18, (255, 255, 255),
              peso=700, fam="titulo", ancla="ml")
        if self.opcional and not solo_lectura:
            self.b_quitar.dibujar(sup)
        foco = pygame.Rect(r.x + 16, r.y + 58, r.w - 32, 178)
        pygame.draw.rect(sup, c["papel2"], foco, border_radius=18)
        pygame.draw.ellipse(sup, self.color, (foco.centerx - 70, foco.bottom - 30, 140, 22))
        pygame.draw.ellipse(sup, c["tinta"], (foco.centerx - 70, foco.bottom - 30, 140, 22), 3)
        bob = math.sin(t * 2.2) * 3 if mov else 0
        parpadeo = (t % 4.2) < 0.13
        img = personajes.cuerpo(self.look, self.rol, "feliz" if self.editando else "neutral", alto=168,
                                parpadeo=parpadeo, color_extra=(58, 110, 230))
        sup.blit(img, (foco.centerx - img.get_width() // 2, foco.bottom - 174 + bob))
        if not solo_lectura:
            self.b_pers.seleccionado = self.personalizar
            self.b_pers.dibujar(sup)
        # nombre
        rn = self.r_nombre
        sticker(sup, rn, c["papel"] if not self.editando else c["acento2"], 12, 0, 3 if self.editando else 2,
                color_borde=c["acento"] if self.editando else c["borde"])
        sup.blit(recursos.icono("user", 18, c["tinta2"], 2.4), (rn.x + 10, rn.centery - 9))
        cursor = "|" if self.editando and (pygame.time.get_ticks() // 450) % 2 else ""
        if self.nombre or self.editando:
            texto(sup, recortar(self.nombre, 18, rn.w - 50, 800) + cursor, (rn.x + 36, rn.centery), 18,
                  c["texto"], peso=800, ancla="ml")
        else:
            texto(sup, "Escribe tu nombre", (rn.x + 36, rn.centery), 16, c["tenue"], peso=700, ancla="ml")
        # rol
        info = ROLES[self.rol]
        if not solo_lectura:
            self.b_izq.dibujar(sup)
            self.b_der.dibujar(sup)
        cx = r.centerx
        sup.blit(recursos.icono(ICONO_ROL[self.rol], 20, c["logro"], 2.6),
                 (cx - recursos.fuente(21, 600, "titulo").size(info["nombre"])[0] // 2 - 26, r.y + 302))
        texto(sup, info["nombre"], (cx, r.y + 313), 21, c["texto"], peso=600, fam="titulo", ancla="c")
        if self.personalizar and not solo_lectura:
            self._dibujar_personalizar(sup)
        else:
            y = r.y + 344
            esp = f"{info['especial'][1]}"
            chip(sup, esp, (r.x + 16, y), c["mango2"], c["texto"], "sparkles", 13)
            parrafo(sup, info["descripcion"], r.x + 16, y + 34, r.w - 32, 13, c["tinta2"], max_lineas=3)
            parrafo(sup, info["pasivo"], r.x + 16, y + 94, r.w - 32, 13, c["texto"], peso=700, max_lineas=3)

    def _dibujar_personalizar(self, sup):
        c = TEMA.c
        r = self.rect
        etiquetas = dict(piel="Piel", pelo="Peinado", color_pelo="Pelo", ropa="Ropa", extra="Detalle")
        for clave, y in self._filas_look():
            texto(sup, etiquetas[clave], (r.x + 18, y + 12), 13, c["tinta2"], peso=800, ancla="ml")
            if clave in ("pelo", "extra"):
                nombre = NOMBRES_PEINADO[self.look["pelo"]] if clave == "pelo" else NOMBRES_EXTRA[self.look["extra"]]
                for rr, ic in ((pygame.Rect(r.x + 80, y, 28, 26), "chevron-left"),
                               (pygame.Rect(r.right - 44, y, 28, 26), "chevron-right")):
                    sticker(sup, rr, c["papel2"], 8, 0, 2)
                    sup.blit(recursos.icono(ic, 18, c["texto"], 2.6), (rr.x + 5, rr.y + 4))
                texto(sup, nombre, ((r.x + 108 + r.right - 44) // 2, y + 13), 15, c["texto"], peso=800, ancla="c")
            else:
                for k, rr in self._muestras(clave, y):
                    hexa = {"piel": personajes.PIEL, "color_pelo": personajes.PELO, "ropa": personajes.ROPA}[clave][k]
                    col = recursos.hex_a_rgb(hexa)
                    pygame.draw.rect(sup, col, rr, border_radius=8)
                    sel = self.look[clave] == k
                    pygame.draw.rect(sup, c["acento"] if sel else c["borde"], rr.inflate(4, 4) if sel else rr,
                                     3 if sel else 2, border_radius=9)

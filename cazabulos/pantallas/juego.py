"""La pantalla del turno: cuenta regresiva, el barrio, pausa y '¡Tiempo!'."""

import pygame

from ..config import ALTO, ANCHO
from ..hud import Hud
from ..mundo import Mundo
from ..render import Render
from ..ui import render, tecla, texto
from .base import Botonera, Escena, instrucciones

TECLAS_ACCION = (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z, pygame.K_KP_ENTER)
TECLAS_PODER = (pygame.K_x, pygame.K_LSHIFT, pygame.K_RSHIFT)


class PantallaJuego(Escena):
    permite_mute = True
    inactividad = None          # el turno termina solo cuando se acaba el tiempo

    @property
    def mando_juego(self):
        """Con el control, B/X/Y son el poder mientras se juega (en la pausa B es volver)."""
        return self.estado in ("juego", "cuenta") and not self.pausa

    def __init__(self, app, partida, en_linea=None, indice=None):
        super().__init__(app)
        self.partida = partida
        self.red = en_linea
        self.indice = partida.actual if indice is None else indice
        j = partida.jugadores[self.indice]
        op = app.op
        pistas = op.get("pistas", True) and partida.ronda == 1
        self.m = Mundo(partida.semilla, j["clave"], partida.duracion, partida.tranquilo or op.get("tranquilo"),
                       partida.ronda, j["piel"], j["pelo"], pistas)
        self.r = Render(self.m, app.son, op)
        self.hud = Hud(self.m, self.r, j["nombre"], partida.ronda, partida.rondas, op)
        self.hud.mando = app.mando.en_uso
        self.r.cuenta = True
        self.estado = "cuenta"
        self.t_estado = 0.0
        self.ultimo_num = None
        self.pausa = None
        self.t_red = 0.0
        self.entrada = {}
        self.paso_cuenta = 1.1 if partida.ronda == 1 else 0.8

    # ------------------------------------------------------------- entrada
    def evento(self, e):
        if self.pausa:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.pausa = None
                return
            self.pausa.evento(e, self.app)
            return
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE and self.estado in ("juego", "cuenta"):
                self._pausar()
            elif e.key in TECLAS_ACCION and self.estado == "juego":
                self.entrada["accion"] = True
            elif e.key in TECLAS_PODER and self.estado == "juego":
                self.entrada["poder"] = True
        elif e.type == pygame.WINDOWFOCUSLOST and self.estado == "juego" and not self.red:
            self._pausar()

    def _pausar(self):
        if self.red:
            self.pausa = Botonera([("Seguir jugando", self._seguir), ("Salir al menú", self._salir)],
                                  centro=(ANCHO // 2, 400), ancho=360)
            return
        self.pausa = Botonera([("Seguir jugando", self._seguir), ("Reiniciar turno", self._reiniciar),
                               ("Salir al menú", self._salir)], centro=(ANCHO // 2, 420), ancho=360)

    def _seguir(self):
        self.pausa = None

    def _reiniciar(self):
        self.app.cambiar(PantallaJuego(self.app, self.partida, self.red, self.indice))

    def _salir(self):
        from .menu import Titulo
        if self.red:
            self.red.cerrar()
            self.app.red = None
        self.app.cambiar(Titulo(self.app))

    def _teclas(self):
        k = pygame.key.get_pressed()
        pad = self.app.mando.estado()
        e = {"izq": k[pygame.K_LEFT] or k[pygame.K_a] or pad["izq"], "der": k[pygame.K_RIGHT] or k[pygame.K_d] or pad["der"],
             "arriba": k[pygame.K_UP] or k[pygame.K_w] or pad["arriba"], "abajo": k[pygame.K_DOWN] or k[pygame.K_s] or pad["abajo"]}
        # mantener ESPACIO (o A) presionado también lanza (a los niños pequeños les pasa mucho)
        sostenido = k[pygame.K_SPACE] or k[pygame.K_z] or pad["accion"]
        if sostenido and self.m.jugador.enfriar <= 0:
            e["accion"] = True
        e.update(self.entrada)
        self.entrada = {}
        return e

    # ------------------------------------------------------------- tiempo
    def actualizar(self, dt):
        super().actualizar(dt)
        if self.pausa and not self.red:
            return
        self.t_estado += dt
        if self.estado == "cuenta":
            n = 3 - int(self.t_estado / self.paso_cuenta)
            if n != self.ultimo_num:
                self.ultimo_num = n
                self.app.son.tocar("cuenta" if n > 0 else "ya")
            if self.t_estado >= self.paso_cuenta * 4:
                self.estado = "juego"
                self.t_estado = 0.0
        elif self.estado == "juego":
            self.m.actualizar(dt, self._teclas() if not self.pausa else {})
            if self.m.terminado:
                self.estado = "fin"
                self.t_estado = 0.0
        elif self.estado == "fin" and self.t_estado > 2.0:
            self._terminar()
            return
        self.r.cuenta = self.estado == "cuenta"
        self.r.actualizar(dt)
        self.hud.mando = self.app.mando.en_uso
        self.hud.actualizar(dt)
        if self.red:
            self.t_red -= dt
            if self.t_red <= 0:
                self.t_red = 0.15
                j = self.m.jugador
                self.red.enviar_estado({"x": round(j.x, 1), "y": round(j.y, 1), "dir": j.dir, "paso": round(j.paso, 2),
                                        "puntos": j.puntos, "salvados": self.m.salvados()})
            self.r.fantasmas = self.red.fantasmas()
            self.hud.marcador = self.red.marcador()
            for aviso in self.red.avisos():
                self.r.avisos.append([aviso, (200, 220, 255), 0.0])

    def _terminar(self):
        pa = self.partida
        res = self.m.resumen()
        j = pa.jugadores[self.indice]
        res["nombre"] = j["nombre"]
        res["logros"] = self.app.logros.revisar(res)
        res["puesto"] = self.app.records.agregar(j["nombre"], j["clave"], res["total"], res["salvados"])
        from .final import ResultadoTurno
        if self.red:
            self.red.terminar(res)
        pa.guardar(self.indice, res)
        self.app.cambiar(ResultadoTurno(self.app, pa, self.indice, res, self.red))

    # ------------------------------------------------------------- dibujo
    def dibujar(self, pant):
        self.r.dibujar(pant)
        self.hud.sin_controles = self.estado == "cuenta" or bool(self.pausa)
        self.hud.dibujar(pant)
        if self.estado == "cuenta":
            n = 3 - int(self.t_estado / self.paso_cuenta)
            f = (self.t_estado % self.paso_cuenta) / self.paso_cuenta
            velo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
            velo.fill((16, 10, 36, 120))
            pant.blit(velo, (0, 0))
            s = "¡YA!" if n <= 0 else str(n)
            tam = int(130 + 50 * (1 - f))
            color = (255, 205, 50) if n > 0 else (120, 240, 150)
            texto(pant, s, (ANCHO // 2, 210), tam, color, "center", grosor=6)
            if n > 0:
                instrucciones(pant, (ANCHO // 2, 440), self.t, self.app.mando.en_uso)
        elif self.estado == "fin":
            velo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
            velo.fill((20, 14, 46, min(170, int(self.t_estado * 300))))
            pant.blit(velo, (0, 0))
            texto(pant, "¡TIEMPO!", (ANCHO // 2, ALTO // 2 - 40), 120, (255, 205, 50), "center", grosor=6)
            texto(pant, f"{self.m.salvados()} vecinos a salvo", (ANCHO // 2, ALTO // 2 + 60), 36, (255, 255, 255), "center")
        if self.pausa:
            velo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
            velo.fill((16, 10, 36, 190))
            pant.blit(velo, (0, 0))
            texto(pant, "Pausa", (ANCHO // 2, 160), 64, (255, 205, 50), "center", grosor=4)
            if self.red:
                texto(pant, "En línea el tiempo sigue corriendo", (ANCHO // 2, 220), 22, (255, 200, 200), "center", 600)
            self.pausa.dibujar(pant, self.t)
            filas = ((("CRUCETA", "moverse"), ("A", "lanzar"), ("B / X", "poder")) if self.app.mando.en_uso
                     else (("FLECHAS", "moverse"), ("ESPACIO", "lanzar"), ("X", "poder")))
            medidas = [(max(render(t_, 16, peso=700, borde=None).get_width() + 18, 30), render(d, 18, peso=600).get_width())
                       for t_, d in filas]
            x = ANCHO // 2 - (sum(a + 8 + b for a, b in medidas) + 36 * (len(filas) - 1)) // 2
            for (t_, d), (a, b) in zip(filas, medidas):
                rr = tecla(pant, t_, (x, ALTO - 120), 16)
                texto(pant, d, (rr.right + 8, ALTO - 116), 18, (240, 240, 250), peso=600)
                x = rr.right + 8 + b + 36

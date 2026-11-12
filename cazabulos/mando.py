"""Controles USB (gamepad): se traducen a teclas para que sirvan en todas las pantallas.

Pensado para la feria: un niño puede jugar con un control tipo Xbox sin tocar el teclado.
  Cruceta o palanca = flechas
  A = ESPACIO (lanzar, aceptar)
  B = atrás en los menús; en el juego es el poder (igual que X y Y)
  X = poder en el juego; en la selección cambia el color de pelo
  Y = poder en el juego; en los resultados muestra la red del barrio (TAB)
  Start = pausa en el juego; aceptar en los menús
"""
import pygame

ENCIENDE, APAGA = 0.55, 0.35          # la palanca se activa al 55 % y se suelta bajo el 35 % (sin temblores)
FLECHAS = {"izq": pygame.K_LEFT, "der": pygame.K_RIGHT, "arriba": pygame.K_UP, "abajo": pygame.K_DOWN}
EVENTOS = (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED, pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP,
           pygame.JOYHATMOTION, pygame.JOYAXISMOTION)

# Botones con la distribución estándar (XInput): 0=A 1=B 2=X 3=Y 6=Back 7=Start
EN_JUEGO = {0: pygame.K_SPACE, 1: pygame.K_x, 2: pygame.K_x, 3: pygame.K_TAB, 6: pygame.K_ESCAPE, 7: pygame.K_ESCAPE}
EN_MENU = {0: pygame.K_SPACE, 1: pygame.K_ESCAPE, 2: pygame.K_c, 3: pygame.K_TAB, 6: pygame.K_ESCAPE, 7: pygame.K_RETURN}


def tecla_falsa(k, abajo=True):
    return pygame.event.Event(pygame.KEYDOWN if abajo else pygame.KEYUP, key=k, mod=0, unicode="", scancode=0)


class Mandos:
    def __init__(self):
        self.palancas = {}                          # instance_id -> Joystick abierto
        self.cruceta = {d: False for d in FLECHAS}
        self.eje = {d: False for d in FLECHAS}
        self.boton_a = False
        self.usado = True                           # False cuando el último toque fue en el teclado
        try:
            pygame.joystick.init()
            for i in range(pygame.joystick.get_count()):
                self._abrir(i)
        except pygame.error:
            pass

    def _abrir(self, indice):
        try:
            j = pygame.joystick.Joystick(indice)
            j.init()
            self.palancas[j.get_instance_id()] = j
        except pygame.error:
            pass

    @property
    def conectado(self):
        return bool(self.palancas)

    @property
    def en_uso(self):
        """Hay un control y fue lo último que se tocó: las ayudas muestran sus botones."""
        return self.conectado and self.usado

    def estado(self):
        """Lo que está sostenido ahora mismo (para caminar en el juego)."""
        e = {d: self.cruceta[d] or self.eje[d] for d in FLECHAS}
        e["accion"] = self.boton_a
        return e

    def _soltar_todo(self):
        for d in FLECHAS:
            self.cruceta[d] = self.eje[d] = False
        self.boton_a = False

    def _cambios(self, fuente, nuevo):
        """Actualiza una fuente (cruceta o palanca) y devuelve las teclas que se presionan o sueltan."""
        otra = self.eje if fuente is self.cruceta else self.cruceta
        salida = []
        for d, k in FLECHAS.items():
            if nuevo[d] != fuente[d]:
                fuente[d] = nuevo[d]
                if not otra[d]:
                    salida.append(tecla_falsa(k, nuevo[d]))
        return salida

    def traducir(self, e, en_juego=False):
        """Convierte un evento del control en eventos de teclado (lista vacía si no hay nada que hacer)."""
        t = e.type
        if t == pygame.JOYDEVICEADDED:
            self._abrir(e.device_index)
            self.usado = True
            return []
        if t == pygame.JOYDEVICEREMOVED:
            self.palancas.pop(getattr(e, "instance_id", None), None)
            self._soltar_todo()
            return []
        if t == pygame.JOYBUTTONDOWN:
            self.usado = True
            if e.button == 0:
                self.boton_a = True
            k = (EN_JUEGO if en_juego else EN_MENU).get(e.button)
            return [tecla_falsa(k)] if k else []
        if t == pygame.JOYBUTTONUP:
            if e.button == 0:
                self.boton_a = False
            return []
        if t == pygame.JOYHATMOTION:
            if getattr(e, "hat", 0) != 0:
                return []
            x, y = e.value
            self.usado = self.usado or any(e.value)
            return self._cambios(self.cruceta, {"izq": x < 0, "der": x > 0, "arriba": y > 0, "abajo": y < 0})
        if t == pygame.JOYAXISMOTION and e.axis in (0, 1):
            neg, pos = ("izq", "der") if e.axis == 0 else ("arriba", "abajo")
            v = e.value
            nuevo = dict(self.eje)
            nuevo[neg] = v < -ENCIENDE or (self.eje[neg] and v < -APAGA)
            nuevo[pos] = v > ENCIENDE or (self.eje[pos] and v > APAGA)
            salida = self._cambios(self.eje, nuevo)
            if salida:
                self.usado = True
            return salida
        return []

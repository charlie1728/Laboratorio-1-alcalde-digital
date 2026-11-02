"""Logros: medallas que se ganan jugando en cualquier modo y se guardan en la carpeta del usuario.

El registro mira los eventos del nivel (los mismos que dibuja la pantalla) y el resultado de cada nivel.
Cuando se gana una medalla queda en ``nuevos`` para que la ventana la anuncie. No usa pygame.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

ARCHIVO = Path.home() / ".alcalde_digital_logros.json"

# id: (nombre, ícono, cómo se gana, meta del contador o None si se gana de una)
LOGROS = {
    "primer_corte": ("Primer tajo", "scissors", "Corta tu primera mentira.", None),
    "multi3": ("Triple tajo", "zap", "Corta 3 mentiras de un solo tajo.", None),
    "combo10": ("Imparable", "flame", "Haz un combo de 10.", None),
    "fiebre": ("¡Con fiebre!", "sparkles", "Entra en fiebre (8 mentiras seguidas).", None),
    "origen": ("Corta de raíz", "git-branch", "Corta un ORIGEN y tumba sus copias.", None),
    "detective": ("Detective", "search", "Verifica 3 alertas virales.", 3),
    "freno": ("Freno de mano", "shield-check", "Frena 3 mentiras virales reportándolas.", 3),
    "buena_fuente": ("Buena fuente", "share-2", "Verifica y comparte una noticia real.", None),
    "pacificador": ("Pacificador", "hand-heart", "Calma 5 peleas entre vecinos.", 5),
    "ojo": ("Ojo de águila", "eye", "Salva un barrio sin cortar ninguna verdad.", None),
    "perfecto": ("Perfecto", "star", "Consigue 3 estrellas en un barrio.", None),
    "cazador": ("Cazabots", "bot", "Corta 100 mentiras en total.", 100),
    "heroe": ("Héroe de Nova", "trophy", "Derrota al Bot Supremo.", None),
    "oro": ("Ciudad informada", "medal", "Termina la campaña con medalla de oro.", None),
    "coleccion": ("Coleccionista", "book-open", "Descubre las 12 pistas de mentira.", None),
    "record": ("Estrella de la feria", "crown", "Haz 500 puntos en ¡Jugar ya!", None),
    "en_red": ("En red", "network", "Juega un duelo en red.", None),
    "estilo": ("Con estilo", "wand-sparkles", "Personaliza a tu personaje.", None),
}


class Registro:
    def __init__(self, ruta: Optional[Path] = ARCHIVO, guardar: bool = True):
        self.ruta = ruta
        self.guardar_en_disco = guardar
        self.tiene: list[str] = []
        self.contadores: dict[str, int] = {}
        self.nuevos: list[str] = []          # recién ganados, para anunciarlos
        if ruta is not None:
            try:
                d = json.loads(ruta.read_text(encoding="utf-8"))
                self.tiene = [k for k in d.get("tiene", []) if k in LOGROS]
                self.contadores = {k: int(v) for k, v in d.get("contadores", {}).items()}
            except (OSError, ValueError, TypeError, AttributeError):
                pass

    def __contains__(self, k) -> bool:
        return k in self.tiene

    def _guardar(self):
        if not self.guardar_en_disco or self.ruta is None:
            return
        try:
            self.ruta.write_text(json.dumps(dict(tiene=self.tiene, contadores=self.contadores)), encoding="utf-8")
        except OSError:
            pass

    def ganar(self, k) -> bool:
        if k not in LOGROS or k in self.tiene:
            return False
        self.tiene.append(k)
        self.nuevos.append(k)
        self._guardar()
        return True

    def sumar(self, k, n=1):
        """Suma a un contador y gana el logro cuando llega a su meta."""
        self.contadores[k] = self.contadores.get(k, 0) + n
        meta = LOGROS[k][3]
        if meta is not None and self.contadores[k] >= meta:
            self.ganar(k)
        else:
            self._guardar()

    def progreso(self, k) -> tuple[int, int]:
        meta = LOGROS[k][3] or 1
        hecho = meta if k in self.tiene else min(meta, self.contadores.get(k, 0))
        return hecho, meta

    def sacar_nuevo(self) -> Optional[str]:
        return self.nuevos.pop(0) if self.nuevos else None

    # -------------------------------------------------------------- lo que pasa en un nivel
    def ver_evento(self, ev: dict):
        t = ev.get("t_")
        if t == "corte" and ev.get("bien") and getattr(ev.get("pub"), "tipo", "") == "falsa":
            self.ganar("primer_corte")
            self.sumar("cazador")
            if ev.get("combo", 0) >= 10:
                self.ganar("combo10")
        elif t == "multi" and ev.get("n", 0) >= 3:
            self.ganar("multi3")
        elif t == "fiebre":
            self.ganar("fiebre")
        elif t == "cadena":
            self.ganar("origen")
        elif t == "verificado":
            self.sumar("detective")
        elif t == "decision":
            if ev.get("clave") in ("v_no_reportar", "r_no"):
                self.sumar("freno")
            if ev.get("clave") == "v_si_compartir":
                self.ganar("buena_fuente")
        elif t == "paces":
            self.sumar("pacificador")
        elif t == "jefe_cae":
            self.ganar("heroe")

    def ver_resultado(self, res: dict, modo: str = ""):
        if res.get("estado") == "ganado":
            if res.get("errores", 1) == 0:
                self.ganar("ojo")
            if res.get("estrellas", 0) >= 3:
                self.ganar("perfecto")
        if modo == "rapido" and res.get("puntos", 0) >= 500:
            self.ganar("record")


REGISTRO = Registro()

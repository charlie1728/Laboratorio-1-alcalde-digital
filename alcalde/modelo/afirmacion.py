"""Una afirmación es el CONTENIDO de una publicación, descompuesto en partes
para que cada reenvío pueda torcer una sola de ellas (y el juego sepa cuál)."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

# Tipos de distorsión que puede sufrir un reenvío -------------------------
DISTORSIONES = {
    "exageracion":    "Cifra inflada",
    "sin_contexto":   "Contexto eliminado",
    "fuente_dudosa":  "Fuente inventada",
    "accion_torcida": "Hecho tergiversado",
    "atribucion":     "Atribución falsa",
}

FUENTES_DUDOSAS = [
    "Me llegó por cadena", "Dicen en el barrio", "Un primo que trabaja allá dice",
    "Audio anónimo", "Lo vi en un grupo", "Pásenlo antes de que lo borren",
]


@dataclass(frozen=True)
class Afirmacion:
    hecho_id: str
    fuente: str
    sujeto: str
    accion: str
    objeto: str
    cifra: Optional[int] = None
    cifra_tpl: str = ""
    contexto: Optional[str] = None
    distorsiones: tuple = ()

    def texto(self) -> str:
        t = f"{self.fuente}: {self.sujeto} {self.accion} {self.objeto}"
        if self.cifra is not None and self.cifra_tpl:
            t += " " + self.cifra_tpl.format(n=self.cifra)
        if self.contexto:
            t += " " + self.contexto
        return t + "."

    def posibles_distorsiones(self, hecho) -> list[str]:
        """Distorsiones que todavía se le pueden aplicar."""
        op = []
        if self.cifra is not None and "exageracion" not in self.distorsiones:
            op.append("exageracion")
        if self.contexto and "sin_contexto" not in self.distorsiones:
            op.append("sin_contexto")
        if "fuente_dudosa" not in self.distorsiones:
            op.append("fuente_dudosa")
        if hecho.acciones_falsas and "accion_torcida" not in self.distorsiones:
            op.append("accion_torcida")
        if hecho.sujetos_falsos and "atribucion" not in self.distorsiones:
            op.append("atribucion")
        return op

    def mutar(self, tipo: str, hecho, rng) -> "Afirmacion":
        """Devuelve una NUEVA afirmación con la distorsión `tipo` aplicada."""
        d = self.distorsiones + (tipo,)
        if tipo == "exageracion":
            return replace(self, cifra=self.cifra * rng.choice([5, 10, 20]), distorsiones=d)
        if tipo == "sin_contexto":
            return replace(self, contexto=None, distorsiones=d)
        if tipo == "fuente_dudosa":
            return replace(self, fuente=rng.choice(FUENTES_DUDOSAS), distorsiones=d)
        if tipo == "accion_torcida":
            return replace(self, accion=rng.choice(hecho.acciones_falsas), distorsiones=d)
        if tipo == "atribucion":
            return replace(self, sujeto=rng.choice(hecho.sujetos_falsos), distorsiones=d)
        raise ValueError(tipo)

    def comparar_con(self, hecho) -> list[str]:
        """Verificación: qué partes NO coinciden con el hecho oficial."""
        dif = []
        if self.cifra != hecho.cifra:
            dif.append("exageracion")
        if self.contexto != hecho.contexto:
            dif.append("sin_contexto")
        if self.fuente != hecho.fuente:
            dif.append("fuente_dudosa")
        if self.accion != hecho.accion:
            dif.append("accion_torcida")
        if self.sujeto != hecho.sujeto:
            dif.append("atribucion")
        return dif

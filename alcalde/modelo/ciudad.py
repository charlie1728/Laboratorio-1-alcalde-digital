"""Indicadores de Ciudad Nova (0..100)."""

POSITIVOS = ["info_verificada", "confianza", "convivencia", "bienestar"]
NEGATIVOS = ["desinformacion", "conflictos"]
NOMBRES = {
    "info_verificada": "Información verificada",
    "confianza": "Confianza ciudadana",
    "convivencia": "Convivencia",
    "bienestar": "Bienestar digital",
    "desinformacion": "Desinformación",
    "conflictos": "Conflictos",
}


class Ciudad:
    def __init__(self):
        self.v = dict(info_verificada=30, confianza=60, convivencia=65,
                      bienestar=60, desinformacion=20, conflictos=15)
        self.historial: list[dict] = [dict(self.v)]

    def ajustar(self, **deltas) -> None:
        for k, d in deltas.items():
            self.v[k] = max(0, min(100, round(self.v[k] + d)))

    def fijar(self, clave: str, valor: float) -> None:
        self.v[clave] = max(0, min(100, round(valor)))

    def salud(self) -> int:
        """Índice global de la ciudad (resultado general)."""
        pos = sum(self.v[k] for k in POSITIVOS) / len(POSITIVOS)
        neg = sum(self.v[k] for k in NEGATIVOS) / len(NEGATIVOS)
        return round((pos + (100 - neg)) / 2)

    def guardar(self) -> None:
        self.historial.append(dict(self.v))

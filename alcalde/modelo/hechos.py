"""Catálogo de hechos REALES de Ciudad Nova (la verdad del juego) y
candidatos. Cada hecho sabe cómo se puede torcer."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .afirmacion import Afirmacion

CANDIDATOS = [
    # nombre, color RGB (paleta Okabe-Ito: segura para daltonismo)
    ("Valentina Rondón", (0, 114, 178)),
    ("Tomás Arrieta", (213, 94, 0)),
    ("Luz Marina Pacheco", (0, 158, 115)),
    ("Emilio Sarmiento", (204, 121, 167)),
]


def _cand(i: int) -> str:
    """'El candidato Tomás Arrieta' / 'La candidata Valentina Rondón'."""
    return ("El candidato " if i in (1, 3) else "La candidata ") + CANDIDATOS[i][0]


@dataclass
class Hecho:
    id: str
    titulo: str
    lugar: str                         # zona de la ciudad (grafo, entrega 2)
    fuente: str
    sujeto: str
    accion: str
    objeto: str
    cifra: Optional[int] = None
    cifra_tpl: str = ""
    contexto: Optional[str] = None
    acciones_falsas: list = field(default_factory=list)
    sujetos_falsos: list = field(default_factory=list)
    en_archivo: bool = True            # ¿está registrado al iniciar?

    def afirmacion_real(self) -> Afirmacion:
        return Afirmacion(self.id, self.fuente, self.sujeto, self.accion,
                          self.objeto, self.cifra, self.cifra_tpl, self.contexto)


def catalogo() -> list[Hecho]:
    return [
        Hecho("alcaldia-auditoria", "Auditoría a la Alcaldía", "ALCALDÍA",
              "Contraloría de Nova", "La Contraloría", "revisa",
              "las cuentas de la Alcaldía", None, "",
              "en una auditoría de rutina",
              ["encontró un robo en", "congeló"],
              [_cand(1), _cand(0)]),
        Hecho("barrio-prado-agua", "Corte de agua en El Prado", "BARRIO",
              "Aguas de Nova", "Aguas de Nova", "cortará",
              "el servicio en el barrio El Prado", 8, "durante {n} horas",
              "para reparar un tubo roto",
              ["privatizará", "suspenderá para siempre"],
              [_cand(2)], en_archivo=False),
        Hecho("colegio-comedor", "Comedor del Colegio San José", "COLEGIO",
              "Rectoría Colegio San José", "El Colegio San José", "suspenderá",
              "el comedor escolar", 2, "por {n} días",
              "mientras renuevan la cocina",
              ["eliminará", "cerrará definitivamente"],
              [_cand(0), _cand(3)]),
        Hecho("debate-aplazado", "Debate de candidatos", "PLAZA",
              "Registraduría de Nova", "La Registraduría", "aplazó",
              "el debate de candidatos", 7, "por {n} días",
              "por la tormenta del martes",
              ["canceló", "prohibió"],
              [_cand(1), _cand(2)]),
        Hecho("hospital-vacunas", "Jornada de vacunación", "BARRIO",
              "Hospital Nova", "El Hospital Nova", "vacunará",
              "a los niños del barrio Norte", 300, "con {n} dosis",
              "en jornada gratuita",
              ["cobrará por vacunar", "obligará a vacunar"],
              [_cand(3)], en_archivo=False),
        Hecho("parque-fumigacion", "Cierre del Parque Central", "PARQUE",
              "Alcaldía de Ciudad Nova", "La Alcaldía", "cerrará",
              "el Parque Central", 3, "durante {n} días",
              "para fumigar contra el dengue",
              ["venderá a una constructora", "cerrará para siempre"],
              [_cand(0), _cand(1)]),
        Hecho("plaza-arriendos", "Arriendos en la Plaza de Mercado", "PLAZA",
              "Administración Plaza de Mercado", "La Plaza de Mercado", "subirá",
              "el arriendo de los puestos", 4, "un {n}%",
              "por el ajuste anual de ley",
              ["triplicará", "cobrará doble"],
              [_cand(2), _cand(3)]),
        Hecho("propuesta-ciclovia", "Propuesta de ciclovía", "PLAZA",
              "Campaña Luz Marina Pacheco", _cand(2), "propone ampliar",
              "la ciclovía", 4, "en {n} km", "con fondos nacionales",
              ["exige cobrar peaje para ampliar", "obligará a cerrar calles para ampliar"],
              [_cand(1)], en_archivo=False),
        Hecho("ruta-12", "Desvío de la ruta 12", "BARRIO",
              "Transporte Nova", "Transporte Nova", "desviará",
              "la ruta 12 de bus", 5, "durante {n} días",
              "por obras en la avenida",
              ["eliminará", "cobrará doble en"],
              [_cand(3)]),
    ]

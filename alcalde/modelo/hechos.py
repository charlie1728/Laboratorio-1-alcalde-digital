from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .afirmacion import Afirmacion

CANDIDATOS = [
    ("Valentina Rondón", (58, 110, 230)),
    ("Tomás Arrieta", (240, 138, 36)),
    ("Luz Marina Pacheco", (40, 168, 96)),
    ("Emilio Sarmiento", (196, 64, 150)),
]

LEMAS = {
    "Valentina Rondón": "Nova conectada",
    "Tomás Arrieta": "Obras que se ven",
    "Luz Marina Pacheco": "Primero la gente",
    "Emilio Sarmiento": "Orden y confianza",
}

def _cand(i: int) -> str:
    return ("El candidato " if i in (1, 3) else "La candidata ") + CANDIDATOS[i][0]

@dataclass
class Hecho:
    id: str
    titulo: str
    lugar: str
    fuente: str
    sujeto: str
    accion: str
    objeto: str
    cifra: Optional[int] = None
    cifra_tpl: str = ""
    contexto: Optional[str] = None
    acciones_falsas: list = field(default_factory=list)
    sujetos_falsos: list = field(default_factory=list)
    en_archivo: bool = True                                          

    def afirmacion_real(self) -> Afirmacion:
        return Afirmacion(self.id, self.fuente, self.sujeto, self.accion,
                          self.objeto, self.cifra, self.cifra_tpl, self.contexto)

def catalogo() -> list[Hecho]:
    return [
        Hecho("transporte-tarifa", "Tarifa de buses", "TERMINAL",
              "Secretaría de Transporte", "La Secretaría", "ajustará",
              "la tarifa del pasaje", 100, "con un incremento de {n} pesos",
              "por la inflación anual",
              ["multiplicará por tres", "eliminará"],
              [_cand(3), _cand(1)]),
        Hecho("parque-central", "Renovación del Parque Central", "PARQUE",
              "Alcaldía de Nova", "La Alcaldía", "cerrará",
              "el Parque Central", 3, "durante {n} meses",
              "para sembrar nuevos árboles",
              ["demolerá", "venderá a privados"],
              [_cand(0), _cand(2)]),
        Hecho("seguridad-policia", "Patrullaje nocturno", "NORTE",
              "Policía Metropolitana", "La Policía", "aumentará",
              "el patrullaje nocturno", 2, "con {n} nuevas unidades",
              "en las zonas comerciales",
              ["multará por salir en", "suspenderá"],
              [_cand(1), _cand(3)]),
        Hecho("hospital-camas", "Donación al Hospital", "HOSPITAL",
              "Ministerio de Salud", "El Ministerio", "entregará",
              "nuevos equipos al Hospital General", 50, "incluyendo {n} camas",
              "para urgencias",
              ["recortará el presupuesto de", "cerrará"],
              [_cand(0)]),
        Hecho("candidato-debate", "Ausencia en debate", "PLAZA",
              "Canal Nova TV", _cand(2), "se ausentó",
              "del debate televisivo", None, "",
              "por una laringitis comprobada",
              ["fue expulsada", "llegó ebria a"],
              [_cand(1), "El Alcalde actual"]),
        Hecho("impuestos-predial", "Descuento en predial", "ALCALDIA",
              "Secretaría de Hacienda", "La Alcaldía", "ofrecerá",
              "un descuento en el impuesto predial", 15, "del {n} por ciento",
              "por pronto pago",
              ["subirá", "cobrará doble"],
              [_cand(3)]),
        Hecho("basuras-horario", "Recolección de basuras", "PRADO",
              "Empresa de Aseo", "La Empresa de Aseo", "cambiará",
              "el horario de recolección", None, "",
              "para evitar el tráfico de la mañana",
              ["suspenderá indefinidamente", "dejará de hacer"],
              [_cand(2)]),
        Hecho("mascotas-registro", "Censo de mascotas", "PARQUE",
              "Centro Zoonosis", "Zoonosis", "iniciará",
              "un censo de mascotas", None, "",
              "para campañas de vacunación",
              ["cobrará impuestos por", "sacrificará a"],
              [_cand(0), "La Policía"]),
        Hecho("internet-gratis", "Puntos WiFi", "COLEGIO",
              "Ministerio TIC", "El Ministerio", "instalará",
              "puntos de internet gratis", 20, "en {n} parques",
              "para uso de los estudiantes",
              ["espiará a los ciudadanos en", "bloqueará las redes en"],
              [_cand(3), _cand(1)]),
        Hecho("deportes-estadio", "Cierre del Estadio", "ESTADIO",
              "Liga Deportiva", "La Liga", "cerrará",
              "el estadio municipal", 5, "durante {n} semanas",
              "para arreglar el techo",
              ["venderá", "clausurará por ruina"],
              [_cand(1)]),

        Hecho("alcaldia-auditoria", "Auditoría a la Alcaldía", "ALCALDIA",
              "Contraloría de Nova", "La Contraloría", "revisa",
              "las cuentas de la Alcaldía", None, "",
              "en una auditoría de rutina",
              ["encontró un robo en", "congeló"],
              [_cand(1), _cand(0)]),
        Hecho("barrio-prado-agua", "Corte de agua en El Prado", "PRADO",
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
        Hecho("hospital-vacunas", "Jornada de vacunación", "NORTE",
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
        Hecho("propuesta-ciclovia", "Propuesta de ciclovía", "ESTADIO",
              "Campaña Luz Marina Pacheco", _cand(2), "propone ampliar",
              "la ciclovía", 4, "en {n} km", "con fondos nacionales",
              ["exige cobrar peaje para ampliar", "obligará a cerrar calles para ampliar"],
              [_cand(1)], en_archivo=False),
        Hecho("ruta-12", "Desvío de la ruta 12", "TERMINAL",
              "Transporte Nova", "Transporte Nova", "desviará",
              "la ruta 12 de bus", 5, "durante {n} días",
              "por obras en la avenida",
              ["eliminará", "cobrará doble en"],
              [_cand(3)]),
    ]

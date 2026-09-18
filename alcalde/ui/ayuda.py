"""Sección AYUDA (tecla H o botón Ayuda)."""
import pygame

from .tema import TEMA
from .widgets import Boton, panel, parrafo, texto

SECCIONES = [
    ("Objetivo", [
        "Ciudad Nova elige alcalde y en la red social Civitas circulan publicaciones. "
        "Cada vez que alguien reenvía algo puede cambiarle un detalle: infla una cifra, quita "
        "el contexto, inventa la fuente... Así nace un ÁRBOL DE MUTACIONES: la raíz es la "
        "publicación original y cada rama es un reenvío.",
        "Tu meta: que la ciudad termine la campaña con más información verificada, confianza y "
        "convivencia, y con menos desinformación y conflictos. Descubrir DÓNDE se torció "
        "una historia vale más que adivinar si es falsa.",
    ]),
    ("Reglas", [
        "1. Cada ronda todos juegan un turno. En tu turno tienes 3 puntos de ATENCIÓN (círculos amarillos).",
        "2. Haz clic en una publicación (nodo) del árbol para seleccionarla y elige una acción. "
        "Cada acción cuesta atención.",
        "3. Al terminar la ronda llega una OLA DE PROPAGACIÓN: los reenvíos más recientes se "
        "vuelven a reenviar y algunos mutan. Las ramas contenidas (anillo verde) ya no crecen.",
        "4. Después ocurre un EVENTO ALEATORIO: noticias nuevas, rumores sobre candidatos, "
        "discusiones, campañas o una publicación VIRAL que hay que atender contra reloj.",
        "5. Un hecho solo se puede verificar si está en el ARCHIVO DE HECHOS. Si falta, un "
        "periodista puede investigarlo y registrarlo.",
    ]),
    ("Botones", [
        "COMPARTIR: reenvías la publicación. Si era verdadera y verificada ganas puntos; si era "
        "falsa, pierdes reputación y la ciudad se desinforma.",
        "VERIFICAR: compara la publicación contra el Archivo de Hechos y revela qué partes son falsas.",
        "REPORTAR: si es falsa, Civitas retira esa publicación y TODOS sus reenvíos (la rama "
        "entera). Si era verdadera, el reporte se rechaza y pierdes reputación.",
        "IGNORAR: no la alimentas. Pequeño premio si era falsa.",
        "BORRAR MI PUBLICACIÓN (solo en tus propios reenvíos): la quita, pero sus reenvíos siguen "
        "circulando: borrar no deshace lo compartido.",
        "Botón especial: depende de tu personaje. TERMINAR TURNO: pasa al siguiente jugador.",
        "Barra de RECORRIDOS: anima Preorden, Postorden, Por niveles y Camino a la raíz sobre el "
        "árbol actual. ARCHIVO AVL: muestra el archivo de hechos.",
        "Teclas: H ayuda · C alto contraste · M sonido · Tab cambiar de caso · Esc cerrar ventanas.",
    ]),
    ("Personajes", [
        "CIUDADANO — Alertar contactos: inmuniza la publicación falsa y sus reenvíos directos. "
        "Pasivo: pausa consciente (el doble de tiempo en eventos virales).",
        "PERIODISTA — Rastrear origen: sube hasta la raíz y marca el reenvío exacto donde "
        "apareció cada distorsión. Pasivo: investiga y registra hechos en el Archivo.",
        "INFLUENCER — Amplificar desmentido: publica la versión correcta en el punto de "
        "mutación y contiene toda esa rama. Pasivo: lo que comparte llega x4 (para bien o para mal).",
        "CANDIDATO — Desmentido oficial: contiene una rama falsa verificada; si el rumor era "
        "sobre su campaña gana el doble y sube su apoyo.",
    ]),
    ("Cómo ganar", [
        "Cada jugador tiene PUNTOS y REPUTACIÓN. Las acciones responsables los suben; compartir "
        "sin verificar o reportar información verdadera los baja. Hay LOGROS: Primer chequeo, "
        "Paciente cero, Poda limpia, Sangre fría.",
        "La ciudad tiene un resultado general (salud) calculado con sus indicadores.",
        "En la entrega final, al terminar la campaña se elegirá al alcalde según la confianza, "
        "la reputación y la información verificada que se logró.",
    ]),
    ("Indicadores", [
        "Información verificada: qué parte de lo que circula ya fue revisada.",
        "Confianza ciudadana: cuánto creen los ciudadanos en la información y entre ellos.",
        "Convivencia: qué tan sana es la conversación.",
        "Bienestar digital: salud del uso de la red (menos ansiedad por lo viral).",
        "Desinformación: proporción del alcance que corresponde a versiones falsas.",
        "Conflictos: peleas y ataques entre ciudadanos.",
        "Formas: círculo gris = sin verificar · cuadrado azul = verificado verdadero · "
        "triángulo naranja = verificado falso · rombo verde = desmentido · anillo verde = rama contenida · "
        "punto naranja en una arista = ahí mutó.",
    ]),
]


class Ayuda:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.sec = 0
        self.botones = []
        x = self.rect.x + 20
        for i, (nombre, _) in enumerate(SECCIONES):
            b = Boton((x, self.rect.y + 60, 132, 34), nombre, i, tam=14)
            self.botones.append(b)
            x += 140
        self.cerrar = Boton((self.rect.right - 110, self.rect.y + 14, 90, 32), "Cerrar", tam=14)

    def evento(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for b in self.botones:
                if b.clic(e.pos):
                    self.sec = b.clave
            if self.cerrar.clic(e.pos):
                return "cerrar"
        return None

    def dibujar(self, sup):
        c = TEMA.c
        capa = pygame.Surface(sup.get_size(), pygame.SRCALPHA)
        capa.fill((0, 0, 0, 170))
        sup.blit(capa, (0, 0))
        panel(sup, self.rect, c["panel"], 14)
        texto(sup, "AYUDA", (self.rect.x + 20, self.rect.y + 16), 24, c["acento"], True)
        for b in self.botones:
            b.seleccionado = b.clave == self.sec
            b.dibujar(sup)
        self.cerrar.dibujar(sup)
        y = self.rect.y + 116
        for p in SECCIONES[self.sec][1]:
            y = parrafo(sup, p, self.rect.x + 30, y, self.rect.w - 60, 17) + 12

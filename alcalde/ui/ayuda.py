import pygame

from ..modelo.partida import LOGROS
from ..modelo.roles import ORDEN_ROLES, ROLES
from . import personajes, recursos
from .tema import TEMA
from .widgets import Boton, forma_estado, parrafo, sticker, texto, titulo

LOOK_ROL = {
    "ciudadano": dict(piel=1, pelo="corto", color_pelo=1, ropa=0, extra=""),
    "periodista": dict(piel=3, pelo="largo", color_pelo=0, ropa=3, extra="gafas"),
    "influencer": dict(piel=4, pelo="afro", color_pelo=0, ropa=6, extra="aretes"),
    "candidato": dict(piel=0, pelo="ondulado", color_pelo=2, ropa=5, extra=""),
}
ICONO_ROL = {"ciudadano": "bell-ring", "periodista": "footprints", "influencer": "megaphone",
             "candidato": "badge-check"}

SECCIONES = [
    ("Objetivo", "flag", [
        ("p", "Ciudad Nova elige alcalde en pocos días y todos hablan en Civitas, su red social. Ahí "
              "circulan noticias verdaderas, opiniones y rumores. Cada vez que alguien reenvía algo puede "
              "cambiarle un detalle: infla una cifra, quita el contexto, inventa la fuente o le echa la "
              "culpa a un candidato."),
        ("p", "Tu misión es que la ciudad llegue a las urnas bien informada: con mucha información "
              "verificada, confianza y convivencia, y con poca desinformación y pocos conflictos."),
        ("item", "lightbulb", "No hay preguntas de trivia",
         "Se aprende jugando: verificas antes de compartir, descubres dónde se torció una historia y ves "
         "cómo tus decisiones cambian la ciudad y hasta el resultado de la elección."),
    ]),
    ("Cómo se juega", "list", [
        ("item", "zap", "Tu turno", "Tienes 3 puntos de atención (rayos) para actuar sobre publicaciones y "
                                   "15 minutos para moverte por el mapa."),
        ("item", "smartphone", "El celular", "A la izquierda está tu feed de Civitas. Elige una publicación y "
                                            "usa los botones de abajo, como en cualquier red social."),
        ("item", "map", "El mapa", "Haz clic en una zona cercana para caminar hasta allá. En persona puedes "
                                  "conversar con los vecinos y comprobar hechos que faltan en el Archivo."),
        ("item", "moon", "La noche", "Cuando todos juegan llega la noche: las publicaciones viajan por la red "
                                    "social (una ola), algunas mutan y ocurre un evento al azar."),
        ("item", "flame", "Publicaciones virales", "A veces algo se vuelve viral y hay que decidir contra "
                                                  "reloj. Si nadie reacciona, se dispara."),
        ("item", "vote", "La elección", "Después del último día cada zona vota. Lo que cree cada vecino "
                                       "cambia sus votos."),
    ]),
    ("Botones", "mouse-pointer-click", [
        ("item", "search", "Verificar (1)", "Compara la publicación con el Archivo de hechos y te muestra "
                                           "exactamente qué partes son falsas."),
        ("item", "share-2", "Compartir (2)", "Se la envías a tus seguidores. Si es verdadera y verificada, "
                                            "ganas; si es falsa, la ciudad se desinforma."),
        ("item", "flag", "Reportar (3)", "Si es falsa, Civitas la retira con todos sus reenvíos y avisa a "
                                        "quienes la vieron. Reportar algo cierto también hace daño."),
        ("item", "eye-off", "Ignorar (4)", "No la alimentas. Pequeño premio si era falsa."),
        ("item", "sparkles", "Especial (5)", "Depende de tu personaje (mira la sección Personajes)."),
        ("item", "trash-2", "Borrar (6)", "Solo en lo que tú publicaste. Sus reenvíos siguen circulando: "
                                         "borrar no deshace lo compartido."),
        ("item", "message-circle", "Conversar", "En el mapa: convences a los vecinos de tu zona que creen un "
                                               "rumor ya descubierto."),
        ("item", "keyboard", "Teclas", "1-6 acciones, Enter terminar turno, Tab cambiar de vista, "
                                      "H ayuda, C contraste, M sonido, Esc cerrar."),
    ]),
    ("Personajes", "users", [("roles",)]),
    ("Cómo ganar", "trophy", [
        ("item", "star", "Puntos y reputación", "Las acciones responsables suben tus puntos y tu reputación; "
                                               "compartir sin verificar o reportar lo cierto los bajan."),
        ("item", "heart-pulse", "La ciudad gana contigo", "La salud de Ciudad Nova sale de sus seis "
                                                        "indicadores. Todos juegan para que termine alta."),
        ("item", "vote", "Elección del alcalde", "Gana más apoyo quien logra confianza, buena reputación y "
                                                "verificación. Los rumores falsos le quitan votos al "
                                                "candidato atacado en cada zona donde se creen."),
        ("logros",),
    ]),
    ("Indicadores", "gauge", [
        ("item", "shield-check", "Información verificada", "Qué parte de lo que circula ya fue revisada."),
        ("item", "handshake", "Confianza ciudadana", "Cuánto creen los ciudadanos en la información y entre ellos."),
        ("item", "heart-handshake", "Convivencia", "Qué tan sana es la conversación."),
        ("item", "heart-pulse", "Bienestar digital", "Uso saludable de la red, sin ansiedad por lo viral."),
        ("item", "cloud-fog", "Desinformación", "Porcentaje de vecinos que hoy creen algo falso."),
        ("item", "zap", "Conflictos", "Peleas y ataques entre ciudadanos."),
        ("formas",),
    ]),
    ("Árboles y grafos", "network", [
        ("item", "git-fork", "Árbol de mutaciones", "La raíz es la publicación original y cada hijo es un "
                                                   "reenvío. Rastrear sube a la raíz; reportar poda una rama."),
        ("item", "archive", "Archivo de hechos (AVL)", "Árbol binario balanceado con los hechos oficiales. "
                                                       "Verificar es buscar ahí; el periodista inserta hechos nuevos."),
        ("item", "share-2", "Red social (grafo dirigido)", "Quién sigue a quién y cuánto confía. Cada noche "
                                                           "una publicación avanza un nivel de recorrido en "
                                                           "anchura (BFS) y ese recorrido es el árbol de mutaciones."),
        ("item", "map", "Mapa de la ciudad (grafo ponderado)", "Calles con minutos. Moverse usa la ruta más "
                                                               "corta (Dijkstra) y los conflictos se contagian a "
                                                               "las zonas vecinas."),
    ]),
    ("En red", "wifi", [
        ("item", "server", "Crear partida", "Un computador elige Jugar en red y Crear partida. La pantalla "
                                           "muestra su dirección (por ejemplo 192.168.1.20)."),
        ("item", "link", "Unirse", "Los demás, en la misma red wifi, eligen Unirse y escriben esa dirección. "
                                  "Cada quien arma su personaje."),
        ("item", "play", "Comenzar", "El anfitrión pulsa Comenzar. El servidor guarda la partida y le envía "
                                    "a todos cada jugada; solo puede actuar quien tiene el turno."),
    ]),
]


class Ayuda:
    def __init__(self, app=None):
        self.app = app
        self.rect = pygame.Rect(110, 50, 1060, 620)
        self.sec = 0
        self.botones = []
        y = self.rect.y + 88
        for i, (nombre, ic, _) in enumerate(SECCIONES):
            self.botones.append(Boton((self.rect.x + 20, y, 226, 50), nombre, i, icono=ic, tam=16,
                                      estilo="suave", sombra=3))
            y += 60
        self.cerrar = Boton((self.rect.right - 66, self.rect.y + 18, 46, 42), "", "cerrar", icono="x", sombra=3)

    def evento(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for b in self.botones:
                if b.clic(e.pos):
                    self.sec = b.clave
            if self.cerrar.clic(e.pos) or not self.rect.collidepoint(e.pos):
                return "cerrar"
        elif e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_h, pygame.K_F1):
                return "cerrar"
            if e.key in (pygame.K_DOWN, pygame.K_TAB):
                self.sec = (self.sec + 1) % len(SECCIONES)
            elif e.key == pygame.K_UP:
                self.sec = (self.sec - 1) % len(SECCIONES)
        return None

    def dibujar(self, sup):
        c = TEMA.c
        velo = pygame.Surface(sup.get_size(), pygame.SRCALPHA)
        velo.fill((*c["tinta"], 150))
        sup.blit(velo, (0, 0))
        sticker(sup, self.rect, c["papel"], 26, 8, 3)
        sup.blit(recursos.icono("book-open", 30, c["acento"], 2.6), (self.rect.x + 24, self.rect.y + 26))
        titulo(sup, "Ayuda", (self.rect.x + 64, self.rect.y + 22), 32, c["texto"])
        for b in self.botones:
            b.seleccionado = b.clave == self.sec
            b.dibujar(sup)
        self.cerrar.dibujar(sup)
        nombre, _, bloques = SECCIONES[self.sec]
        x, y, w = self.rect.x + 276, self.rect.y + 30, self.rect.w - 310
        titulo(sup, nombre, (x, y), 30, c["acento"])
        y += 56
        grande = TEMA.op["texto_grande"]
        tam = 17 if grande else 16
        for b in bloques:
            if b[0] == "p":
                y = parrafo(sup, b[1], x, y, w, tam, c["texto"]) + 12
            elif b[0] == "item":
                pygame.draw.circle(sup, c["acento2"], (x + 18, y + 16), 18)
                sup.blit(recursos.icono(b[1], 20, c["acento"], 2.4), (x + 8, y + 6))
                texto(sup, b[2], (x + 46, y), tam, c["texto"], peso=800)
                y = parrafo(sup, b[3], x + 46, y + tam + 5, w - 46, tam - 1, c["tinta2"]) + 10
            elif b[0] == "roles":
                self._roles(sup, x, y, w)
            elif b[0] == "formas":
                y += 4
                xx = x
                for est, nom in (("nada", "sin verificar"), ("veraz", "verdadera"), ("falso", "falsa"),
                                 ("correccion", "desmentido")):
                    forma_estado(sup, est, (xx + 10, y + 10), 9)
                    r = texto(sup, nom, (xx + 26, y + 1), 14, c["tinta2"], peso=700)
                    xx = r.right + 22
                texto(sup, "Cada estado tiene color y forma propios, para que no dependa solo del color.",
                      (x, y + 28), 14, c["tinta2"])
            elif b[0] == "logros":
                y += 2
                texto(sup, "Logros", (x, y), tam, c["texto"], peso=800)
                y += 26
                col = 0
                for nom, desc in LOGROS.items():
                    xx = x + col * (w // 2)
                    sup.blit(recursos.icono("award", 18, c["logro"], 2.4), (xx, y))
                    texto(sup, nom, (xx + 24, y), 14, c["texto"], peso=800)
                    col += 1
                    if col == 2:
                        col, y = 0, y + 24

    def _roles(self, sup, x, y, w):
        c = TEMA.c
        ancho = (w - 18) // 2
        for i, rol in enumerate(ORDEN_ROLES):
            info = ROLES[rol]
            rx, ry = x + (i % 2) * (ancho + 18), y + (i // 2) * 244
            sticker(sup, (rx, ry, ancho, 232), c["papel2"], 18, 0, 2)
            sup.blit(personajes.cuerpo(LOOK_ROL[rol], rol, "feliz", alto=150, color_extra=(58, 110, 230)),
                     (rx + 8, ry + 10))
            texto(sup, info["nombre"], (rx + 116, ry + 14), 20, c["texto"], peso=700, fam="titulo")
            sup.blit(recursos.icono(ICONO_ROL[rol], 16, c["logro"], 2.6), (rx + 116, ry + 46))
            texto(sup, info["especial"][1], (rx + 138, ry + 44), 14, c["logro"], peso=800)
            yy = parrafo(sup, info["descripcion"], rx + 116, ry + 68, ancho - 128, 13, c["tinta2"])
            parrafo(sup, info["pasivo"], rx + 14, max(yy + 6, ry + 166), ancho - 28, 13, c["texto"], peso=700)

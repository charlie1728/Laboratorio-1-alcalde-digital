import pygame

NORMAL = dict(
    fondo=(13, 17, 28), panel=(22, 29, 44), panel2=(30, 39, 58), borde=(48, 60, 86),
    texto=(232, 236, 244), tenue=(140, 152, 176), acento=(86, 180, 233),
    bueno=(0, 158, 115), malo=(213, 94, 0), aviso=(240, 228, 66), logro=(230, 159, 0),
    arista=(70, 86, 118), arista_falsa=(150, 80, 40),
    n_desconocido=(154, 163, 181), n_veraz=(86, 180, 233), n_falso=(213, 94, 0),
    n_correccion=(0, 158, 115), n_inmune=(0, 158, 115), seleccion=(255, 255, 255),
    boton=(40, 52, 78), boton_hover=(56, 72, 106), boton_off=(30, 36, 50),
    sombra=(0, 0, 0, 140),
)

ALTO_CONTRASTE = dict(
    fondo=(0, 0, 0), panel=(0, 0, 0), panel2=(20, 20, 20), borde=(255, 255, 255),
    texto=(255, 255, 255), tenue=(220, 220, 220), acento=(255, 255, 0),
    bueno=(0, 255, 180), malo=(255, 110, 50), aviso=(255, 255, 0), logro=(255, 200, 0),
    arista=(200, 200, 200), arista_falsa=(255, 140, 60),
    n_desconocido=(255, 255, 255), n_veraz=(0, 200, 255), n_falso=(255, 110, 50),
    n_correccion=(0, 255, 180), n_inmune=(0, 255, 180), seleccion=(255, 255, 0),
    boton=(0, 0, 0), boton_hover=(60, 60, 0), boton_off=(30, 30, 30),
    sombra=(0, 0, 0, 200),
)

class Tema:
    def __init__(self):
        self.alto_contraste = False
        self.c = dict(NORMAL)
        self._fuentes = {}

    def alternar_contraste(self):
        self.alto_contraste = not self.alto_contraste
        self.c = dict(ALTO_CONTRASTE if self.alto_contraste else NORMAL)

    def fuente(self, tam: int, negrita: bool = False) -> pygame.font.Font:
        clave = (tam, negrita)
        if clave not in self._fuentes:
            nombre = pygame.font.match_font("segoeui,dejavusans,arial,liberationsans", bold=negrita)
            f = pygame.font.Font(nombre, tam) if nombre else pygame.font.Font(None, tam + 6)
            if not nombre:
                f.set_bold(negrita)
            self._fuentes[clave] = f
        return self._fuentes[clave]

TEMA = Tema()

import json
from pathlib import Path

from . import recursos

# Estilo "pegatina de campaña": paneles blancos con contorno de tinta y sombra dura,
# sobre una Ciudad Nova soleada. Los estados de las publicaciones usan la paleta
# Okabe-Ito (apta para daltonismo) y además una forma propia.
NORMAL = dict(
    cielo1=(126, 209, 242), cielo2=(214, 243, 255), papel=(255, 255, 255), papel2=(241, 244, 255),
    papel3=(228, 233, 252), tinta=(35, 33, 74), texto=(35, 33, 74), tinta2=(84, 88, 130),
    tenue=(128, 132, 168), borde=(35, 33, 74), sombra=(35, 33, 74),
    acento=(108, 77, 245), acento2=(236, 231, 255), mango=(255, 194, 61), mango2=(255, 238, 196),
    pasto=(139, 211, 107), pasto2=(108, 187, 82), arena=(246, 226, 179), calle=(250, 238, 210),
    agua=(92, 200, 240),
    bueno=(0, 150, 110), malo=(213, 94, 0), aviso=(214, 140, 0), logro=(230, 159, 0),
    bueno2=(214, 245, 232), malo2=(255, 229, 212),
    arista=(150, 156, 196), arista_falsa=(213, 94, 0),
    n_desconocido=(154, 160, 186), n_veraz=(0, 114, 178), n_falso=(213, 94, 0),
    n_correccion=(0, 158, 115), n_inmune=(0, 158, 115), n_duda=(204, 170, 60),
    seleccion=(35, 33, 74), resalte=(255, 194, 61),
    boton=(255, 255, 255), boton_hover=(243, 240, 255), boton_off=(226, 229, 240),
    sobre_color=(255, 255, 255),
)

ALTO_CONTRASTE = dict(
    cielo1=(0, 0, 0), cielo2=(0, 0, 0), papel=(0, 0, 0), papel2=(18, 18, 18), papel3=(40, 40, 40),
    tinta=(255, 255, 255), texto=(255, 255, 255), tinta2=(235, 235, 235), tenue=(210, 210, 210),
    borde=(255, 255, 255), sombra=(255, 255, 0),
    acento=(255, 255, 0), acento2=(50, 50, 0), mango=(255, 255, 0), mango2=(60, 60, 0),
    pasto=(0, 60, 0), pasto2=(0, 110, 0), arena=(30, 30, 30), calle=(70, 70, 70), agua=(0, 60, 120),
    bueno=(0, 255, 180), malo=(255, 120, 60), aviso=(255, 255, 0), logro=(255, 210, 0),
    bueno2=(0, 60, 40), malo2=(80, 30, 0),
    arista=(200, 200, 200), arista_falsa=(255, 140, 60),
    n_desconocido=(255, 255, 255), n_veraz=(0, 200, 255), n_falso=(255, 120, 60),
    n_correccion=(0, 255, 180), n_inmune=(0, 255, 180), n_duda=(255, 230, 120),
    seleccion=(255, 255, 0), resalte=(255, 255, 0),
    boton=(0, 0, 0), boton_hover=(60, 60, 0), boton_off=(35, 35, 35),
    sobre_color=(0, 0, 0),
)

OPCIONES_DEFECTO = dict(alto_contraste=False, texto_grande=False, mas_tiempo=False,
                        subtitulos=True, menos_movimiento=False, sonido=True, musica=True,
                        guia=True)

_ARCHIVO = Path.home() / ".alcalde_digital.json"


class Tema:
    def __init__(self):
        self.op = dict(OPCIONES_DEFECTO)
        try:
            guardadas = json.loads(_ARCHIVO.read_text(encoding="utf-8"))
            self.op.update({k: bool(v) for k, v in guardadas.items() if k in OPCIONES_DEFECTO})
        except (OSError, ValueError, AttributeError):
            pass
        self.c = dict(ALTO_CONTRASTE if self.op["alto_contraste"] else NORMAL)

    @property
    def alto_contraste(self) -> bool:
        return self.op["alto_contraste"]

    def alternar_contraste(self):
        self.cambiar("alto_contraste", not self.op["alto_contraste"])

    def cambiar(self, clave, valor):
        self.op[clave] = valor
        self.c = dict(ALTO_CONTRASTE if self.op["alto_contraste"] else NORMAL)
        try:
            _ARCHIVO.write_text(json.dumps(self.op), encoding="utf-8")
        except OSError:
            pass

    def fuente(self, tam: int, negrita: bool = False):
        return recursos.fuente(tam, 800 if negrita else 600)

    def escala_texto(self, tam: int) -> int:
        return round(tam * 1.18) if self.op["texto_grande"] else tam


TEMA = Tema()

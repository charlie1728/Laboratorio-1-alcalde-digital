
ROLES = {
    "ciudadano": dict(
        nombre="Ciudadano", simbolo="C",
        especial=("alertar", "Alertar contactos", 1),
        pasivo="Pausa consciente: en eventos virales tiene el doble de tiempo.",
        descripcion="Frena rumores en su círculo cercano: inmuniza el nodo y sus reenvíos directos.",
        tiempo_viral=20, mult_alcance=1),
    "periodista": dict(
        nombre="Periodista", simbolo="P",
        especial=("rastrear", "Rastrear origen", 2),
        pasivo="Investiga: si el hecho no está en el Archivo, lo registra al verificar.",
        descripcion="Sube por el árbol hasta la raíz y señala el reenvío exacto donde se torció la historia.",
        tiempo_viral=10, mult_alcance=1),
    "influencer": dict(
        nombre="Influencer", simbolo="I",
        especial=("amplificar", "Amplificar desmentido", 2),
        pasivo="Megáfono: lo que comparte llega x4 y genera reenvíos inmediatos.",
        descripcion="Publica una corrección en el punto de mutación e inmuniza TODA esa rama.",
        tiempo_viral=10, mult_alcance=4),
    "candidato": dict(
        nombre="Candidato", simbolo="A",
        especial=("desmentir", "Desmentido oficial", 2),
        pasivo="Los rumores sobre él/ella le restan apoyo cada ronda.",
        descripcion="Desmiente una versión falsa verificada; si el rumor era sobre sí mismo gana apoyo extra.",
        tiempo_viral=10, mult_alcance=2),
}

ORDEN_ROLES = ["ciudadano", "periodista", "influencer", "candidato"]

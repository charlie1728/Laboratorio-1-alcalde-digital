ROLES = {
    "ciudadano": dict(
        nombre="Ciudadano", simbolo="C",
        especial=("alertar", "Alertar contactos", 1),
        pasivo="Pausa consciente: en las publicaciones virales tiene el doble de tiempo para decidir.",
        descripcion="Avisa a sus contactos de la red: quienes creían el rumor dejan de creerlo "
                    "y los demás quedan prevenidos.",
        tiempo_viral=20),
    "periodista": dict(
        nombre="Periodista", simbolo="P",
        especial=("rastrear", "Rastrear origen", 2),
        pasivo="Investiga: registra en el Archivo los hechos que faltan, esté donde esté.",
        descripcion="Sube por el árbol hasta el origen, señala dónde se torció la historia "
                    "y expone al paciente cero ante sus seguidores.",
        tiempo_viral=10),
    "influencer": dict(
        nombre="Influencer", simbolo="I",
        especial=("amplificar", "Amplificar desmentido", 2),
        pasivo="Megáfono: tiene 12 seguidores. Lo que comparte llega lejos, para bien o para mal.",
        descripcion="Publica la versión correcta donde se torció la historia, contiene esa rama "
                    "y la corrección viaja dos saltos por su red.",
        tiempo_viral=10),
    "candidato": dict(
        nombre="Candidato", simbolo="A",
        especial=("desmentir", "Desmentido oficial", 2),
        pasivo="Gira: cada zona que visita le suma apoyo. Los rumores sobre su campaña se lo restan.",
        descripcion="Desmiente una versión falsa: convence a quien confía en él o ella "
                    "por algún camino de la red.",
        tiempo_viral=10),
}

ORDEN_ROLES = ["ciudadano", "periodista", "influencer", "candidato"]

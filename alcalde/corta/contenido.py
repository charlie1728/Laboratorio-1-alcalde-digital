"""Todo lo que se puede leer en el juego: publicaciones, señales de mentira, barrios y personajes.

Atajos para decidir rápido (se enseñan en la ayuda y en el álbum):
  * Las fuentes oficiales tienen el chulito azul (✓). Lo que trae chulito azul es verdad.
  * Las mentiras traen señales: cadena, audio anónimo, cuenta bot, urgencia, cifra imposible...
  * Las más difíciles imitan a una fuente oficial pero NO tienen el chulito azul.
"""
from __future__ import annotations

# ------------------------------------------------------------------ señales de mentira
# id: (nombre, ícono, explicación para el álbum)
SENALES = {
    "cadena": ("Cadena", "link", "Viene de una cadena reenviada mil veces. Nadie sabe quién la escribió."),
    "anonimo": ("Sin autor", "eye-off", "Un audio o un 'me contaron' no tiene a nadie que responda por lo que dice."),
    "urgente": ("Te apura", "flame", "'¡Pásenlo ya!', '¡antes de que lo borren!': la prisa es para que no pienses."),
    "mayusculas": ("Grita", "megaphone", "MAYÚSCULAS y muchos signos de admiración buscan asustarte."),
    "cifra": ("Cifra imposible", "gauge", "Números exagerados: 100 colegios en una ciudad que tiene 4."),
    "bot": ("Cuenta bot", "bot", "Una cuenta con @ y números que publica sin parar. No es una persona."),
    "impostor": ("Sin chulito", "badge-check", "Se hace pasar por una fuente oficial, pero no tiene el chulito azul."),
    "ataque": ("Ataque sin pruebas", "angry", "Habla mal de alguien sin mostrar ninguna prueba."),
    "regalo": ("Demasiado bueno", "gift", "Regalos gratis y premios fáciles casi siempre son trampa."),
    "recorte": ("Recortado", "scissors", "Una foto vieja o un video recortado se puede usar para engañar."),
    "absoluto": ("Todo o nada", "circle-x", "'TODOS', 'nadie', 'para siempre': las noticias reales casi nunca son así."),
    "amenaza": ("Amenaza", "message-square-warning", "'Si no lo compartes, te pasa algo': nadie puede obligarte."),
}

# ------------------------------------------------------------------ publicaciones falsas
# (fuente, texto, nivel 1..3, señales, barrio o None)
FALSAS = [
    ("Me llegó por cadena", "¡¡URGENTE!! Mañana cierran TODOS los colegios", 1, ("cadena", "mayusculas"), "COLEGIO"),
    ("Audio anónimo", "PÁSENLO: el agua de Nova está envenenada", 1, ("anonimo", "urgente"), None),
    ("Un primo que trabaja allá", "El alcalde se robó la plata del parque", 1, ("anonimo", "ataque"), "PARQUE"),
    ("Lo vi en un grupo", "¡¡¡Van a demoler el Estadio esta noche!!!", 1, ("anonimo", "mayusculas"), "ESTADIO"),
    ("Dicen en el barrio", "Los buses ya no van a parar en El Prado", 1, ("anonimo",), "PRADO"),
    ("Pásenlo antes de que lo borren", "La elección se suspende para siempre", 1, ("urgente", "absoluto"), None),
    ("Cadena de WhatsApp", "REGALAN celulares en la Plaza, ¡CORRAN!", 1, ("cadena", "regalo"), "PLAZA"),
    ("Audio de un señor", "Cierran el Hospital Nova por un mes", 1, ("anonimo",), "HOSPITAL"),
    ("Me lo contaron", "El candidato Tomás odia a los niños", 1, ("anonimo", "ataque"), None),
    ("Grupo de mamás", "¡Mañana no hay luz en toda la ciudad!", 1, ("anonimo", "absoluto"), "NORTE"),
    ("Mensaje reenviado", "Si no compartes esto, te borran la cuenta", 1, ("cadena", "amenaza"), None),
    ("Cadena del colegio", "¡¡Mañana NO hay clases!! Pásenlo", 1, ("cadena", "urgente"), "COLEGIO"),
    ("Audio anónimo", "En la Terminal roban todos los celulares", 1, ("anonimo", "absoluto"), "TERMINAL"),
    ("Me llegó por cadena", "En la Plaza venden comida dañada a propósito", 1, ("cadena", "ataque"), "PLAZA"),
    ("Grupo del barrio", "¡¡¡Hay un león suelto en el Parque!!!", 1, ("anonimo", "mayusculas"), "PARQUE"),
    ("Cadena de WhatsApp", "Regalan boletas para el clásico, ¡ya!", 1, ("cadena", "regalo"), "ESTADIO"),
    ("Alcaldia de Nova", "El pasaje del bus subirá a 10.000 pesos", 2, ("impostor", "cifra"), "TERMINAL"),
    ("Secretaria de Educacion", "Cerrarán 100 colegios este año", 2, ("impostor", "cifra"), "COLEGIO"),
    ("Hospital Nova Oficial", "Habrá 3 años de espera para una cita", 2, ("impostor", "cifra"), "HOSPITAL"),
    ("Policía Nova", "Prohibido salir a la calle después de las 5", 2, ("impostor", "absoluto"), "NORTE"),
    ("Registraduria", "Ya no se puede votar con cédula", 2, ("impostor",), None),
    ("Alcaldía Nova Info", "El Parque Central se vende a una empresa", 2, ("impostor",), "PARQUE"),
    ("Noticiero Nova", "TODOS los candidatos están presos", 2, ("impostor", "absoluto"), None),
    ("Secretaría de Salud Nova", "Vacunarse da superpoderes", 2, ("impostor",), "HOSPITAL"),
    ("Empresa de Aguas", "Cortarán el agua 160 horas seguidas", 2, ("impostor", "cifra"), "PRADO"),
    ("Estadio Municipal", "Las boletas ahora cuestan 1 millón", 2, ("impostor", "cifra"), "ESTADIO"),
    ("Terminal Nova", "Ya no saldrán buses hacia ningún lado", 2, ("impostor", "absoluto"), "TERMINAL"),
    ("Plaza de Mercado", "Desde hoy todo cuesta el doble", 2, ("impostor", "cifra"), "PLAZA"),
    ("@NoticiasYa24", "Encuesta: Emilio gana con el 99 %", 3, ("bot", "cifra"), None),
    ("@LaVerdadOculta", "Lo que no te cuentan del Colegio San José", 3, ("bot",), "COLEGIO"),
    ("@AlertaNova", "Nueva ley: multa por sentarse en el parque", 3, ("bot",), "PARQUE"),
    ("Noticias24.co.co", "El metro de Nova ya está listo", 3, ("impostor",), "TERMINAL"),
    ("@InfoUrgente_", "Hospital Nova se quedó sin médicos", 3, ("bot",), "HOSPITAL"),
    ("Página sin nombre", "Luz Marina renunció a la campaña", 3, ("anonimo",), None),
    ("@NovaSinCensura", "Cambiaron el día de la elección", 3, ("bot",), None),
    ("Blog de chismes", "Tomás Arrieta tiene 20 casas", 3, ("ataque",), None),
    ("Video recortado", "Valentina se burla de los abuelos", 3, ("recorte", "ataque"), None),
    ("Foto vieja", "Inundación hoy en el Barrio Norte", 3, ("recorte",), "NORTE"),
    ("@NoticiasYa24", "El Estadio se cae a pedazos", 3, ("bot",), "ESTADIO"),
    ("Encuesta de internet", "Nadie va a votar este domingo", 3, ("absoluto",), None),
    ("@ElPradoLibre", "Van a tumbar las casas de El Prado", 3, ("bot",), "PRADO"),
]

# ------------------------------------------------------------------ publicaciones verdaderas
# (fuente oficial con chulito, texto, hecho para el Archivo, barrio o None)
VERDADERAS = [
    ("Alcaldía de Nova", "El Parque Central cierra 3 meses para sembrar árboles", "Parque: siembra de árboles", "PARQUE"),
    ("Secretaría de Educación", "El Colegio San José cierra 1 día para fumigar", "Colegio: fumigación", "COLEGIO"),
    ("Secretaría de Transporte", "El pasaje del bus sube 100 pesos en enero", "Bus: nueva tarifa", "TERMINAL"),
    ("Hospital Nova", "Abre jornada de vacunación el sábado", "Hospital: vacunación", "HOSPITAL"),
    ("Registraduría", "La elección es el domingo de 8 a 4", "Elección: horario", None),
    ("Policía Metropolitana", "Más patrullas de noche en el Barrio Norte", "Norte: patrullas nocturnas", "NORTE"),
    ("Empresa de Aguas", "Corte de agua de 8 horas en El Prado", "Prado: corte de agua", "PRADO"),
    ("Alcaldía de Nova", "La Plaza de Mercado amplía su horario", "Plaza: nuevo horario", "PLAZA"),
    ("Terminal de buses", "Nueva ruta de bus al Estadio", "Terminal: ruta al Estadio", "TERMINAL"),
    ("Biblioteca Pública", "Talleres gratis de lectura en vacaciones", "Biblioteca: talleres", None),
    ("Registraduría", "Consulta tu puesto de votación en línea", "Elección: puesto de votación", None),
    ("Secretaría de Salud", "Lavarse las manos previene la gripa", "Salud: lavado de manos", "HOSPITAL"),
    ("Estadio Municipal", "El clásico del sábado empieza a las 6", "Estadio: clásico", "ESTADIO"),
    ("Defensa Civil", "Simulacro de evacuación el jueves a las 10", "Simulacro de evacuación", None),
    ("Hospital Nova", "Nuevo horario de visitas: de 2 a 6", "Hospital: visitas", "HOSPITAL"),
    ("Alcaldía de Nova", "Se arreglan 12 calles del Barrio Norte", "Norte: calles arregladas", "NORTE"),
    ("Secretaría de Educación", "Inscripciones abiertas para el próximo año", "Colegio: inscripciones", "COLEGIO"),
    ("Canal Nova", "Los 4 candidatos debaten el viernes en TV", "Elección: debate", None),
    ("Empresa de Energía", "Mantenimiento de luz el martes por 2 horas", "Energía: mantenimiento", "PRADO"),
    ("Alcaldía de Nova", "Feria de emprendedores en la Plaza", "Plaza: feria", "PLAZA"),
    ("Policía Metropolitana", "Línea 123 disponible las 24 horas", "Policía: línea 123", None),
    ("Secretaría de Cultura", "Concierto gratis en el Parque el domingo", "Parque: concierto", "PARQUE"),
    ("Registraduría", "Lleva tu cédula original para votar", "Elección: cédula", None),
    ("Hospital Nova", "Jornada de donación de sangre el lunes", "Hospital: donación", "HOSPITAL"),
    ("Estadio Municipal", "Abren escuelas de fútbol para niños", "Estadio: escuelas", "ESTADIO"),
    ("Terminal de buses", "Buses cada 10 minutos en hora pico", "Terminal: frecuencia", "TERMINAL"),
    ("Junta del Barrio El Prado", "Minga de limpieza el sábado a las 8", "Prado: minga", "PRADO"),
]

# ------------------------------------------------------------------ los barrios (niveles)
# regla: id del modificador que cambia cómo se juega ese barrio
BARRIOS_JUEGO = {
    "PLAZA": dict(regla="tutorial", titulo="Primer día", icono="store",
                  texto="Aquí aprendes: las publicaciones vienen marcadas para que veas cómo es cada una."),
    "NORTE": dict(regla="cadenas", titulo="Cadenas", icono="link",
                  texto="Muchos rumores ORIGEN: si llegan arriba, se los reenvían a sus seguidores."),
    "PRADO": dict(regla="grupos", titulo="Grupo del barrio", icono="message-circle",
                  texto="Las publicaciones llegan de a tres, como en un chat de vecinos."),
    "COLEGIO": dict(regla="recreo", titulo="Recreo", icono="school",
                    texto="Todo va más rápido: los chismes del recreo corren solos."),
    "PARQUE": dict(regla="viento", titulo="Viento", icono="wind",
                   texto="El viento empuja las publicaciones de un lado a otro. ¡Mira la flecha!"),
    "TERMINAL": dict(regla="buses", titulo="Buses", icono="bus-front",
                     texto="Algunas publicaciones pasan en bus de lado a lado. ¡Córtalas antes de que salgan!"),
    "ESTADIO": dict(regla="avalancha", titulo="Avalancha", icono="users",
                    texto="Llegan muchísimas a la vez, pero los combos valen el doble."),
    "HOSPITAL": dict(regla="cero", titulo="Cero tolerancia", icono="heart-pulse",
                     texto="Rumores de salud: cada mentira que cae hace el doble de daño."),
    "ALCALDIA": dict(regla="jefe", titulo="El Bot Supremo", icono="bot",
                     texto="El jefe final lanza rumores desde arriba. Córtalos para derrotarlo."),
}

# ------------------------------------------------------------------ personajes
PODERES = {
    "periodista": dict(nombre="Lupa", icono="search", texto="Todo va lento y se ve qué es falso y qué es verdad."),
    "influencer": dict(nombre="Megáfono", icono="megaphone", texto="Corta de un solo grito todo lo falso en pantalla."),
    "ciudadano": dict(nombre="Escudo vecinal", icono="shield", texto="Las próximas 3 mentiras que caigan rebotan."),
    "candidato": dict(nombre="Discurso", icono="mic", texto="El barrio recupera 30 de confianza."),
}

# Lo que se compra en la tienda con monedas: (nombre, ícono, descripción, precios por nivel)
MEJORAS = {
    "filo": ("Filo largo", "scissors", "El tajo corta más ancho.", (40, 90, 160)),
    "calma": ("Calma", "hourglass", "Las publicaciones vuelan más despacio.", (50, 110, 190)),
    "energia": ("Recarga rápida", "zap", "Tu poder se llena más rápido.", (40, 90, 160)),
    "corazon": ("Barrio fuerte", "heart-handshake", "Cada barrio empieza con más confianza.", (60, 120, 200)),
    "iman": ("Imán de monedas", "magnet", "Ganas más monedas por nivel.", (50, 100, 170)),
}

ESPECIALES = {
    "moneda": dict(texto="+5 monedas", icono="coins"),
    "corazon": dict(texto="+15 confianza", icono="heart"),
    "reloj": dict(texto="¡Todo más lento!", icono="hourglass"),
}

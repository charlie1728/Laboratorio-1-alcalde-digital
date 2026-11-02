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
    # cosas que les llegan a los niños
    ("Cadena del recreo", "¡¡Si comes chicle en clase te expulsan!!", 1, ("cadena", "mayusculas"), "COLEGIO"),
    ("Audio de un niño", "En el Parque vive un monstruo de noche", 1, ("anonimo", "urgente"), "PARQUE"),
    ("Mensaje reenviado", "Comparte esto y te regalan un videojuego", 1, ("cadena", "regalo"), None),
    ("Grupo del salón", "La profe dijo que mañana no hay recreo", 1, ("anonimo",), "COLEGIO"),
    ("Me lo dijo un amigo", "Los perros del Parque muerden a TODOS", 1, ("anonimo", "absoluto"), "PARQUE"),
    ("Cadena de WhatsApp", "¡Gana 1.000 monedas del juego gratis!", 1, ("cadena", "regalo"), None),
    ("Audio anónimo", "Si no reenvías esto, se borra tu juego", 1, ("anonimo", "amenaza"), None),
    ("Dicen en la cancha", "Cancelaron TODOS los partidos del año", 1, ("anonimo", "absoluto"), "ESTADIO"),
    ("Grupo de la familia", "¡¡Los helados de la Plaza dan fiebre!!", 1, ("anonimo", "mayusculas"), "PLAZA"),
    ("Cadena de WhatsApp", "Los buses ahora son gratis, ¡corran!", 1, ("cadena", "urgente"), "TERMINAL"),
    ("Colegio San Jose", "Habrá clases también los domingos", 2, ("impostor",), "COLEGIO"),
    ("Hospital Nova Info", "Comer zanahoria cura todas las gripas", 2, ("impostor", "absoluto"), "HOSPITAL"),
    ("Policia Nova", "Montar bicicleta ahora está prohibido", 2, ("impostor",), "NORTE"),
    ("Parque Central Oficial", "Ya no dejarán entrar mascotas nunca", 2, ("impostor", "absoluto"), "PARQUE"),
    ("Estadio Nova", "El clásico se juega a las 3 de la mañana", 2, ("impostor",), "ESTADIO"),
    ("@JuegosGratis_99", "Descarga aquí la app que te da diamantes", 3, ("bot", "regalo"), None),
    ("@NoticiasYa24", "Encuesta: el 200 % de los niños odia leer", 3, ("bot", "cifra"), None),
    ("Video recortado", "Tomás Arrieta empuja a una señora", 3, ("recorte", "ataque"), None),
    ("Foto vieja", "Así quedó la Terminal después del choque", 3, ("recorte",), "TERMINAL"),
    ("Página sin nombre", "Luz Marina no sabe leer", 3, ("anonimo", "ataque"), None),
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
    ("Secretaría de Educación", "Vacaciones de mitad de año desde el 20 de junio", "Colegio: vacaciones", "COLEGIO"),
    ("Colegio San José", "Feria de ciencias el viernes en el patio", "Colegio: feria de ciencias", "COLEGIO"),
    ("Biblioteca Pública", "Hora del cuento para niños los sábados", "Biblioteca: hora del cuento", None),
    ("Secretaría de Salud", "Vacunación gratis para mascotas en el Parque", "Parque: vacunación de mascotas", "PARQUE"),
    ("Alcaldía de Nova", "Nueva ciclovía entre el Norte y el Parque", "Norte: ciclovía", "NORTE"),
    ("Estadio Municipal", "Entrada gratis para niños al partido del domingo", "Estadio: entrada de niños", "ESTADIO"),
    ("Terminal de buses", "Los niños menores de 5 años no pagan pasaje", "Terminal: pasaje de niños", "TERMINAL"),
    ("Hospital Nova", "Charla sobre alimentación sana el miércoles", "Hospital: alimentación sana", "HOSPITAL"),
    ("Alcaldía de Nova", "Mercado campesino los domingos en la Plaza", "Plaza: mercado campesino", "PLAZA"),
    ("Registraduría", "Los jurados de votación se escogen por sorteo", "Elección: jurados", None),
    ("Canal Nova", "Debate de candidatos con preguntas de niños", "Elección: debate infantil", None),
    ("Defensa Civil", "Curso gratis de primeros auxilios", "Defensa Civil: primeros auxilios", None),
    ("Empresa de Aguas", "Cierra la llave al cepillarte: ahorras agua", "Agua: ahorro", None),
    ("Secretaría de Cultura", "Festival de cometas en el Parque en agosto", "Parque: festival de cometas", "PARQUE"),
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
    "campana": dict(texto="¡Campaña de convivencia!", icono="hand-heart"),
}

# ------------------------------------------------------------------ misiones del día
# Un objetivo extra por nivel (da monedas y puntos). id: (texto, ícono, meta)
MISIONES = {
    "calmar": ("Calma 2 peleas entre vecinos", "hand-heart", 2),
    "combo": ("Haz un combo de 6", "flame", 6),
    "verdades": ("Deja llegar 6 noticias reales", "newspaper", 6),
    "sin_errores": ("No cortes ninguna verdad", "badge-check", 1),
    "verificar": ("Verifica antes de decidir en la alerta", "search", 1),
    "origenes": ("Corta 2 rumores ORIGEN", "git-branch", 2),
    "dorados": ("Atrapa 2 objetos dorados", "gift", 2),
    "jefe_rapido": ("Corta 15 rumores del jefe", "bot", 15),
}
# Qué misiones pueden salir según la regla del barrio
MISIONES_POR_REGLA = {
    "tutorial": ("verdades", "dorados"),
    "cadenas": ("origenes", "verificar", "calmar"),
    "jefe": ("jefe_rapido", "sin_errores", "dorados"),
}
MISIONES_COMUNES = ("calmar", "combo", "verdades", "sin_errores", "verificar", "dorados")

# ------------------------------------------------------------------ estado de Ciudad Nova
# id: (nombre, nombre corto, ícono, ¿es mejor que suba?)
INDICADORES = {
    "verificada": ("Información verificada", "Verificada", "badge-check", True),
    "confianza": ("Confianza ciudadana", "Confianza", "heart-handshake", True),
    "convivencia": ("Convivencia", "Convivencia", "users", True),
    "bienestar": ("Bienestar digital", "Bienestar", "smile", True),
    "desinformacion": ("Desinformación", "Desinformación", "cloud-lightning", False),
    "conflictos": ("Conflictos", "Conflictos", "flame", False),
}
INDICADORES_INICIO = dict(verificada=40, confianza=50, convivencia=60, bienestar=55, desinformacion=50, conflictos=35)

# ------------------------------------------------------------------ candidatos a la alcaldía
# Los tres primeros hacen campaña con propuestas; Emilio hace campaña con cadenas y bots.
# barrios: donde más lo conocen (ahí se lleva la mayoría de los votos informados).
CANDIDATOS = [
    dict(id="valentina", nombre="Valentina Ríos", lema="Parques y colegios", color=(0, 168, 120),
         barrios=("COLEGIO", "PARQUE", "PRADO")),
    dict(id="tomas", nombre="Tomás Arrieta", lema="Buses y calles", color=(40, 132, 230),
         barrios=("TERMINAL", "NORTE", "ESTADIO")),
    dict(id="luz", nombre="Luz Marina", lema="Salud para todos", color=(255, 150, 30),
         barrios=("HOSPITAL", "PLAZA", "ALCALDIA")),
    dict(id="emilio", nombre="Emilio", lema="Campaña de cadenas y bots", color=(232, 72, 72), barrios=(), bot=True),
]

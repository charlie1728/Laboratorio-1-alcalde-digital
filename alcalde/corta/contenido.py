"""Las publicaciones que salen volando.

Las falsas tienen pistas que se aprenden jugando (fuente rara, prisa, mayúsculas, cifras
imposibles). En los primeros días las pistas son muy obvias; luego se van volviendo sutiles.
Las verdaderas vienen de una fuente con nombre y dicen algo concreto y tranquilo.
"""
from __future__ import annotations

# (fuente, texto, nivel 1..3, pista que se enseña al cortarla)
FALSAS = [
    ("Me llegó por cadena", "¡¡URGENTE!! Mañana cierran TODOS los colegios", 1, "Cadena sin fuente"),
    ("Audio anónimo", "PÁSENLO: el agua de Nova está envenenada", 1, "Nadie dice quién lo dijo"),
    ("Un primo que trabaja allá", "El alcalde se robó el dinero del parque", 1, "Fuente que no se puede comprobar"),
    ("Lo vi en un grupo", "¡¡¡Van a demoler el Estadio esta noche!!!", 1, "Muchos signos de alarma"),
    ("Dicen en el barrio", "Los buses ya no van a parar en El Prado", 1, "Rumor de barrio"),
    ("Pásenlo antes de que lo borren", "La elección se suspende para siempre", 1, "Te apura para que no pienses"),
    ("Cadena de WhatsApp", "REGALAN celulares en la Plaza, ¡CORRAN!", 1, "Demasiado bueno para ser verdad"),
    ("Audio de un señor", "Cierran el Hospital Nova por un mes", 1, "Audio sin nombre"),
    ("Me lo contaron", "El candidato Tomás odia a los niños", 1, "Ataque sin pruebas"),
    ("Grupo de mamás", "¡Mañana no hay luz en toda la ciudad!", 1, "Alarma sin fuente"),
    ("Mensaje reenviado muchas veces", "Si no compartes esto, te borran la cuenta", 1, "Te amenaza para que lo compartas"),
    ("Captura de pantalla", "Valentina dijo que va a cerrar el parque", 1, "Una captura se puede inventar"),
    ("Alcaldía de Nova", "El pasaje del bus subirá a 10.000 pesos", 2, "Cifra exagerada"),
    ("Secretaría de Educación", "Cerrarán 100 colegios este año", 2, "Cifra imposible: Nova tiene 4"),
    ("Hospital Nova", "Habrá 3 años de espera para una cita", 2, "Cifra exagerada"),
    ("Policía Metropolitana", "Prohíben salir a la calle después de las 5", 2, "Cambiaron lo que dijeron"),
    ("Registraduría", "Ya no se puede votar con cédula", 2, "Cambiaron lo que dijeron"),
    ("Alcaldía de Nova", "El Parque Central se vende a una empresa", 2, "Tergiversaron el anuncio"),
    ("Noticiero Nova", "Todos los candidatos están presos", 2, "Afirmación absoluta"),
    ("Secretaría de Salud", "Vacunarse da superpoderes", 2, "Absurdo con fuente oficial falsa"),
    ("Alcaldía de Nova", "La Plaza cerrará para siempre", 2, "Le quitaron el contexto"),
    ("Empresa de Aguas", "Cortarán el agua 160 horas seguidas", 2, "Cifra exagerada"),
    ("Estadio Municipal", "Los partidos ahora cuestan 1 millón", 2, "Cifra exagerada"),
    ("Terminal de buses", "Ya no saldrán buses hacia ningún lado", 2, "Afirmación absoluta"),
    ("@NoticiasYa24", "Encuesta: Emilio gana con el 99 %", 3, "Cuenta bot y cifra rara"),
    ("@LaVerdadOculta", "Lo que no te cuentan del Colegio San José", 3, "Cuenta anónima que busca clics"),
    ("@AlertaNova", "Nueva ley: multa por usar el parque", 3, "Cuenta bot"),
    ("Noticias24.co.co", "El metro de Nova ya está listo", 3, "Página con nombre raro"),
    ("@InfoUrgente_", "Hospital Nova sin médicos desde hoy", 3, "Cuenta bot"),
    ("Página sin nombre", "Luz Marina renunció a la campaña", 3, "Sin autor ni fecha"),
    ("@NovaSinCensura", "Cambian el día de la elección", 3, "Cuenta bot"),
    ("Blog de chismes", "Tomás Arrieta tiene 20 casas", 3, "Chisme sin pruebas"),
    ("Video recortado", "Valentina se burla de los abuelos", 3, "Un video recortado engaña"),
    ("Foto vieja", "Inundación hoy en el Barrio Norte", 3, "Foto de otro año"),
    ("@NoticiasYa24", "El Estadio se cae a pedazos", 3, "Cuenta bot"),
    ("Encuesta de internet", "Nadie va a votar este domingo", 3, "Encuesta sin método"),
]

VERDADERAS = [
    ("Alcaldía de Nova", "El Parque Central cierra 3 meses para sembrar árboles"),
    ("Secretaría de Educación", "El Colegio San José cierra 1 día para fumigar"),
    ("Secretaría de Transporte", "El pasaje del bus sube 100 pesos en enero"),
    ("Hospital Nova", "Abre jornada de vacunación el sábado"),
    ("Registraduría", "La elección es el domingo de 8 a 4"),
    ("Policía Metropolitana", "Más patrullas de noche en el Barrio Norte"),
    ("Empresa de Aguas", "Corte de agua de 8 horas en El Prado"),
    ("Alcaldía de Nova", "La Plaza de Mercado amplía su horario"),
    ("Terminal de buses", "Nueva ruta de bus al Estadio"),
    ("Biblioteca Pública", "Talleres gratis de lectura en vacaciones"),
    ("Registraduría", "Puedes consultar tu puesto de votación en línea"),
    ("Secretaría de Salud", "Lavarse las manos previene la gripa"),
    ("Estadio Municipal", "El clásico del sábado empieza a las 6"),
    ("Defensa Civil", "Simulacro de evacuación el jueves a las 10"),
    ("Hospital Nova", "Nuevo horario de visitas: de 2 a 6"),
    ("Alcaldía de Nova", "Se arreglan 12 calles del Barrio Norte"),
    ("Secretaría de Educación", "Inscripciones abiertas para el próximo año"),
    ("Debate oficial", "Los 4 candidatos debaten el viernes en TV"),
    ("Empresa de Energía", "Mantenimiento de luz el martes 2 horas"),
    ("Alcaldía de Nova", "Feria de emprendedores en la Plaza"),
    ("Policía Metropolitana", "Línea 123 disponible las 24 horas"),
    ("Secretaría de Cultura", "Concierto gratis en el Parque el domingo"),
    ("Registraduría", "Lleva tu cédula original para votar"),
    ("Hospital Nova", "Donar sangre salva vidas: jornada el lunes"),
]

# Cosas especiales que también salen volando.
ESPECIALES = {
    "lupa": dict(texto="Lupa", ayuda="Todo va lento y lo falso brilla en rojo", icono="search"),
    "megafono": dict(texto="Megáfono", ayuda="¡Borra todo lo falso de la pantalla!", icono="megaphone"),
    "escudo": dict(texto="Escudo", ayuda="La ciudad está protegida un rato", icono="shield"),
    "corazon": dict(texto="Convivencia", ayuda="Sana el barrio más afectado", icono="heart-handshake"),
}

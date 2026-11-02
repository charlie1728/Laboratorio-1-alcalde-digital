# Alcalde Digital · Corta la mentira

Videojuego educativo sobre el uso responsable de las redes sociales.
Estructura de Datos II, Universidad del Norte.

Ciudad Nova va a elegir alcalde y los rumores vuelan por las redes. Las publicaciones salen disparadas desde los barrios y tú las cortas con el mouse antes de que caigan sobre la gente.

**La regla cabe en una frase: corta lo falso, deja pasar lo verdadero y cuida la ciudad.**

No hay preguntas de trivia. Se aprende jugando: las fuentes oficiales traen el **chulito azul ✓** y las mentiras traen señales (cadena, audio anónimo, cuenta bot, prisa, cifras imposibles). Al cortarlas, el juego te dice el truco que usaban y lo guarda en tu álbum. Y cuando una publicación se vuelve viral, tienes 10 segundos para decidir: **verificar, compartir, reportar o ignorar**, y luego ves por la red social a cuántas personas les llegó.

La campaña empieza con una historia animada. Cada mañana sale el **Diario Nova** con lo que pasó, y al final la portada de la elección cuenta quién ganó y qué hiciste tú. Cada barrio trae una **misión del día**, hay **18 logros** para ganar en cualquier modo y puedes **personalizar** a tu personaje.

![Alerta viral](docs/img/v3/alerta.png)

## Modos de juego

| Modo | Qué es |
|---|---|
| **¡Jugar ya!** | Un barrio de un minuto con las primeras tarjetas marcadas para aprender, y tabla de récords al final. Pensado para la feria. |
| **Campaña** | Liberas Ciudad Nova barrio por barrio en un mapa. Cada barrio es un nivel con su propia regla, y cada noche el rumor salta a los barrios vecinos. Ganas estrellas y monedas, compras mejoras, llenas el álbum y, cuando liberas 4 barrios, te enfrentas al **Bot Supremo** en la Alcaldía. Después viene la elección. El progreso se guarda solo. |
| **Fiesta (2 a 4)** | Se turnan el mouse: cada uno juega el mismo barrio y la última ronda es contra el jefe. Gana quien sume más puntos. |
| **Duelo en red** | Cada jugador en su computador, en la misma red wifi. Todos juegan el mismo barrio al mismo tiempo, ven el marcador en vivo, cada combo de 5 le manda un rumor extra a los rivales y lo que compartes en la alerta viral les llega a ellos. |

## Cómo se juega

- **Cortar:** arrastra el mouse con el botón izquierdo sobre la publicación.
- **Alerta viral:** una vez por nivel todo se congela. Pulsa **Verificar** (o 1), **Compartir** (2), **Reportar** (3) o **Ignorar** (4). Verificar muestra si es verdad y sus pistas; después decides. Al final ves tu camino en el árbol de decisiones y la publicación avanzando por la red social.
- **Peleas en la calle:** si aparece una burbuja roja sobre dos vecinos, córtala para que hagan las paces.
- **Misión del día:** cada barrio trae un objetivo extra (se ve debajo del puntaje). Cumplirlo da +50 puntos y +20 monedas.
- **Combos:** corta varias mentiras seguidas. Con 8 seguidas entras en **fiebre** (puntos dobles). Cortar dos o tres de un solo tajo da premio extra.
- **ORIGEN:** si un rumor marcado como ORIGEN llega arriba sin cortar, sus seguidores lo reenvían y aparecen copias. Si cortas el origen, caen todas las copias de una vez.
- **Poder del personaje:** se carga cortando mentiras. Se usa con **Espacio** o **clic derecho**.
  - Ana, Periodista: **Lupa**. Todo va lento y se ve qué es falso. En la alerta, verificar le da +15.
  - Beto, Influencer: **Megáfono**. Corta de un grito todo lo falso en pantalla. Tiene 12 seguidores: lo que comparte llega lejos (para bien o para mal).
  - Caro, Ciudadana: **Escudo vecinal**. Las próximas 3 mentiras que caigan rebotan. Reportar le suma convivencia.
  - Dani, Candidato: **Discurso**. El barrio recupera confianza. En la elección, Dani es uno de los candidatos.
- **Estrellas:** 1 si salvas el barrio, 2 si queda con buena confianza, 3 si además no cortaste ninguna verdad.

### Los barrios

| Barrio | Regla |
|---|---|
| Plaza de Mercado | Primer día: las publicaciones vienen marcadas para aprender |
| Barrio Norte | Cadenas: muchos rumores ORIGEN |
| Barrio El Prado | Grupo del barrio: llegan de a tres, como en un chat |
| Colegio San José | Recreo: todo va más rápido |
| Parque Central | Viento: empuja las publicaciones de lado a lado |
| Terminal de buses | Buses: algunas publicaciones cruzan la pantalla en bus |
| Estadio Municipal | Avalancha: muchísimas a la vez, combos dobles |
| Hospital Nova | Cero tolerancia: cada mentira hace el doble de daño |
| Alcaldía | Jefe final: el Bot Supremo lanza rumores desde arriba (se abre al liberar 4 barrios) |

### El estado de Ciudad Nova

Seis indicadores suben y bajan con lo que haces: **información verificada, confianza ciudadana, convivencia, bienestar digital, desinformación y conflictos** (estos dos, mejor bajos). Se ven en el mapa y al final de cada barrio, y deciden la elección: si la ciudad queda informada gana un candidato con propuestas; si no, gana Emilio, el de las cadenas y los bots.

## Las estructuras de datos (y para qué sirven en el juego)

| Estructura | Archivo | Uso en el juego |
|---|---|---|
| **Árbol de decisiones** (n-ario con puntero al padre) | `alcalde/estructuras/arbol_decision.py` | La alerta viral. Los botones son los hijos del nodo actual, el juego responde «¿es verdadera?» y cada hoja guarda la consecuencia (puntos, indicadores y si se propaga). Al final se muestra el camino de la raíz a la hoja. |
| **Grafo social** (dirigido, con confianza) | `alcalde/modelo/red_social.py` | Lo que alguien comparte les llega a sus seguidores **salto por salto (BFS)**: el juego muestra quién lo recibe, cuántos y en cuántos saltos. De ahí salen también los autores de las publicaciones y quién reenvía un ORIGEN. |
| **Grafo de la ciudad** (no dirigido, con minutos) | `alcalde/estructuras/grafo.py`, `alcalde/modelo/mapa.py` | El mapa de la campaña. Solo se juega en vecinos de un barrio liberado, el rumor se contagia por las calles cada noche (un paso de BFS desde los focos) y los barrios liberados hacen de muro. El mapa marca la ruta más corta desde la Plaza (Dijkstra). |
| **Árbol del rumor** (n-ario con puntero al padre) | `alcalde/estructuras/arbol_mutaciones.py` | El ORIGEN es la raíz y cada reenvío es un hijo. Cortar el origen **poda el subárbol**: por eso caen todas las copias. |
| **Archivo de hechos** (árbol AVL) | `alcalde/estructuras/archivo_avl.py` | Cada noticia verdadera que llega a la gente se inserta en el AVL. El álbum la muestra en orden alfabético (recorrido en inorden). Se guarda en preorden para reconstruir el árbol con la misma forma. |

Documentación: [Entrega 1, árboles](docs/ENTREGA_1.md) · [Entrega 2, grafos](docs/ENTREGA_2.md) · [**Entrega final**](docs/ENTREGA_FINAL.md) (todo lo que pide el enunciado, sección por sección, y respuestas para la sustentación).

## Lo que pide el laboratorio

| Requisito | Dónde está |
|---|---|
| Árboles y grafos con función real | Tabla de arriba |
| Compartir, verificar, ignorar o reportar con tiempo limitado | La alerta viral: 10 segundos, cuatro botones y su árbol de decisiones |
| Propagación: quién, cuántos, qué tan rápido, si es verdad y qué pasa | La red social animada después de cada alerta |
| Interfaz gráfica: ciudad, personaje, publicaciones, opciones, estado, puntaje, indicadores, resultados | Mapa de la isla, niveles con el barrio de fondo, barra de confianza, panel de indicadores y resumen de cada nivel |
| Componente aleatorio | Noticias falsas y verdaderas, virales, rumores contra candidatos, peleas entre vecinos, campañas de convivencia, vecinos que reportan, viento, buses, focos de rumor cada noche y el jefe. La misma semilla repite la partida. |
| Roles con habilidades distintas | Los 4 personajes: su poder, sus seguidores en la red y cómo vale cada decisión |
| Estado de la ciudad, puntuación individual y resultado de la ciudad | 6 indicadores, puntos, estrellas, monedas, récords y la elección final |
| Elección del alcalde | Cuatro candidatos; cada barrio vota según cómo quedó y según los indicadores |
| Multijugador cliente-servidor con sockets | `alcalde/red/sala.py`: servidor TCP con hilos y mensajes JSON por línea. Sincroniza jugadores, semilla (publicaciones y red), marcador, ataques y lo compartido |
| Inclusividad | Opciones: símbolos grandes (para quien no lee), alto contraste, modo tranquilo, menos movimiento y subtítulos de sonido. Personajes personalizables. Lo bueno y lo malo nunca se distinguen solo por color. |
| Historia | Historia animada al empezar la campaña, Diario Nova cada mañana y portada final de la elección |
| Ayuda | Botón Ayuda con 9 secciones (incluido el árbol de decisiones dibujado), también desde la pausa. La lechuza Civi da consejos y una mano animada enseña a cortar. |
| Elementos motivadores | Misiones del día, 18 logros con aviso, combos, fiebre, estrellas, tienda de mejoras, álbum, jefe final, récords de la feria, efectos, sonidos y confeti |

## Cómo ejecutar

Se necesita **Python 3.10 o superior** ([python.org](https://www.python.org/downloads/); en Windows, marcar «Add Python to PATH» al instalar).

```bash
pip install -r requirements.txt
python main.py
```

En Windows también se puede abrir con **doble clic en `jugar.bat`**. La ventana abre maximizada; `F11` pasa a pantalla completa y `M` silencia el sonido. Con `python main.py 42` la partida sale siempre igual.

### Duelo en red

1. En un computador: **Duelo en red › Crear sala**. Arriba aparece la IP (por ejemplo `192.168.1.20`).
2. En los demás: **Duelo en red**, escribir esa IP y pulsar **Unirme**.
3. El anfitrión escoge el barrio y pulsa **¡Empezar duelo!**

También hay un servidor sin ventana: `python servidor.py`.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Son 65 pruebas:
- **Estructuras:** árboles, AVL, grafo y mapa, y el árbol de decisiones (forma, recorrido, inserción y eliminación).
- **Niveles:** cada barrio del juego, el árbol del rumor y la poda.
- **Alerta viral:** congela la ciudad, la propagación solo viaja por aristas de la red y se cierra sola si se acaba el tiempo.
- **Calle:** discusiones que se calman o que suben los conflictos.
- **Campaña:** el contagio por el mapa, los indicadores, la elección, la tienda y el guardado.
- **Logros, misiones, Diario Nova, estadísticas de la campaña y personajes guardados.**
- **Récords.**
- **Red:** un duelo real con un servidor y dos clientes, y lo compartido llegando a los rivales.

## Organización del código

```
main.py                     arranque
alcalde/estructuras/        árbol de decisiones, árbol del rumor, AVL y grafo
alcalde/modelo/             mapa de la ciudad, red social y apariencia de los personajes
alcalde/corta/              el juego: nivel.py y campana.py (reglas, sin pygame) y las pantallas
alcalde/red/                duelo en red (servidor y cliente)
alcalde/ui/                 dibujo, personajes, sonido y opciones
tests/                      pruebas
```

# Alcalde Digital · Corta la mentira

Videojuego educativo sobre el uso responsable de las redes sociales.
Estructura de Datos II, Universidad del Norte.

Ciudad Nova va a elegir alcalde y los rumores vuelan por las redes. Las publicaciones salen disparadas desde los barrios y tú las cortas con el mouse antes de que caigan sobre la gente.

**La regla cabe en una frase: corta lo falso, deja pasar lo verdadero y cuida la ciudad.**

No hay preguntas de trivia. Se aprende jugando: las fuentes oficiales traen el **chulito azul ✓** y las mentiras traen señales (cadena, audio anónimo, cuenta bot, prisa, cifras imposibles). Al cortarlas, el juego te dice el truco que usaban y lo guarda en tu álbum.

## Modos de juego

| Modo | Qué es |
|---|---|
| **Campaña** | Liberas Ciudad Nova barrio por barrio en un mapa. Cada barrio es un nivel con su propia regla, y cada noche el rumor salta a los barrios vecinos. Ganas estrellas y monedas, compras mejoras, llenas el álbum y al final te enfrentas al **Bot Supremo** en la Alcaldía. Después viene la elección. El progreso se guarda solo. |
| **Fiesta (2 a 4)** | Se turnan el mouse: cada uno juega el mismo barrio y la última ronda es contra el jefe. Gana quien sume más puntos. |
| **Duelo en red** | Cada jugador en su computador, en la misma red wifi. Todos juegan el mismo barrio al mismo tiempo, ven el marcador en vivo y cada combo de 5 le manda un rumor extra a los rivales. |

## Cómo se juega

- **Cortar:** arrastra el mouse con el botón izquierdo sobre la publicación.
- **Combos:** corta varias mentiras seguidas. Con 8 seguidas entras en **fiebre** (puntos dobles). Cortar dos o tres de un solo tajo da premio extra.
- **ORIGEN:** si un rumor marcado como ORIGEN llega arriba sin cortar, sus seguidores lo reenvían y aparecen copias. Si cortas el origen, caen todas las copias de una vez.
- **Poder del personaje:** se carga cortando mentiras. Se usa con **Espacio** o **clic derecho**.
  - Ana, Periodista: **Lupa**. Todo va lento y se ve qué es falso.
  - Beto, Influencer: **Megáfono**. Corta de un grito todo lo falso en pantalla.
  - Caro, Ciudadana: **Escudo vecinal**. Las próximas 3 mentiras que caigan rebotan.
  - Dani, Candidato: **Discurso**. El barrio recupera confianza.
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
| Alcaldía | Jefe final: el Bot Supremo lanza rumores desde arriba |

## Las estructuras de datos (y para qué sirven en el juego)

| Estructura | Archivo | Uso en el juego |
|---|---|---|
| **Grafo de la ciudad** (no dirigido, con minutos) | `alcalde/estructuras/grafo.py`, `alcalde/modelo/mapa.py` | El mapa de la campaña. Solo se juega en vecinos de un barrio liberado, el rumor se contagia por las calles cada noche (un paso de BFS desde los focos) y los barrios liberados hacen de muro. El mapa marca la ruta más corta desde la Plaza (Dijkstra). |
| **Grafo social** (dirigido, con confianza) | `alcalde/modelo/red_social.py` | De ahí salen los autores de las publicaciones. Cuando un ORIGEN llega arriba, lo reenvían los seguidores del autor (sus aristas de salida, por confianza). |
| **Árbol del rumor** (n-ario con puntero al padre) | `alcalde/estructuras/arbol_mutaciones.py` | El ORIGEN es la raíz y cada reenvío es un hijo. Cortar el origen **poda el subárbol**: por eso caen todas las copias. |
| **Archivo de hechos** (árbol AVL) | `alcalde/estructuras/archivo_avl.py` | Cada noticia verdadera que dejas llegar a la gente se inserta en el AVL. El álbum la muestra en orden alfabético (recorrido en inorden). Se guarda en preorden para reconstruir el árbol con la misma forma. |

Justificaciones anteriores: [Entrega 1, árboles](docs/ENTREGA_1.md) · [Entrega 2, grafos](docs/ENTREGA_2.md).

## Lo que pide el laboratorio

| Requisito | Dónde está |
|---|---|
| Árboles y grafos con función real | Tabla de arriba |
| Interfaz gráfica: ciudad, personaje, publicaciones, opciones, estado, puntaje, indicadores, resultados | Mapa de la isla, niveles con el barrio de fondo, barra de confianza, estrellas y resumen de cada nivel |
| Componente aleatorio | Publicaciones, ORIGEN, virales, objetos especiales, viento, buses, focos nuevos de rumor cada noche y el jefe. La misma semilla repite la partida. |
| Habilidad y decisiones con tiempo limitado | Cortar a tiempo, decidir qué barrio salvar en el mapa y cuándo usar el poder |
| Roles con habilidades distintas | Los 4 personajes y sus poderes |
| Puntuación individual y resultado de la ciudad | Puntos, estrellas, monedas, confianza de cada barrio y la elección final |
| Elección del alcalde | Al vencer al jefe: cada barrio vota según cómo quedó |
| Multijugador cliente-servidor con sockets | `alcalde/red/sala.py`: servidor TCP con hilos y mensajes JSON por línea |
| Inclusividad | Opciones: modo tranquilo (todo más lento), menos movimiento, subtítulos de sonido. Las señales llevan ícono además de color. |
| Ayuda | Botón Ayuda: cómo se juega, atajos para descubrir mentiras, barrios, personajes, mapa, controles y cómo funciona por dentro. Además, la lechuza da consejos durante el juego. |
| Elementos motivadores | Combos, fiebre, estrellas, tienda de mejoras, álbum para completar, jefe final, efectos y sonidos |

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

Prueban los árboles, el AVL, el grafo y el mapa, cada barrio del juego, el árbol del rumor y la poda, el contagio por el mapa, la tienda, el guardado de la campaña y un duelo real con un servidor y dos clientes.

## Organización del código

```
main.py                     arranque
alcalde/estructuras/        árbol del rumor, AVL y grafo
alcalde/modelo/             mapa de la ciudad, red social y apariencia de los personajes
alcalde/corta/              el juego: nivel.py y campana.py (reglas, sin pygame) y las pantallas
alcalde/red/                duelo en red (servidor y cliente)
alcalde/ui/                 dibujo, personajes, sonido y opciones
tests/                      pruebas
```

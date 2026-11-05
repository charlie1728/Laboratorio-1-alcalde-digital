# Cazabulos · Alcalde Digital

Videojuego educativo sobre el uso responsable de las redes sociales.
Estructura de Datos II, Universidad del Norte.

Ciudad Nova va a elegir alcalde y por la red social Civitas corren los **Bulos**: rumores morados que se suben a la cabeza de los vecinos y saltan de amigo en amigo. Tú caminas por el barrio, los atrapas, revisas las noticias antes de compartirlas y apagas la antena del Bot que los fabrica.

**En una frase: salva a la mayor cantidad de vecinos.**

![La plaza: una cadena de Bulos con corona](docs/img/cazabulos/plaza.png)

## Cómo se juega

| Tecla | Qué hace |
|---|---|
| **Flechas** (o WASD) | Caminar por el barrio |
| **Espacio** | Lanzar tu herramienta a los Bulos (o a la cabeza de un vecino para curarlo, o a la antena). Junto a un vecino con una estrella: entregársela. Junto a dos vecinos peleando: calmarlos |
| **X** | El poder de tu personaje, cuando el círculo se llena |
| **Esc** | Pausa · **M** silencia la música · **F11** pantalla completa |

- **Bulos:** vuelan hacia los vecinos con más amigos. Si llegan, se le suben a la cabeza y el vecino se pone gris.
- **Hilos:** las amistades se ven como hilos. Un vecino con Bulo se lo reenvía a un amigo por su hilo (la bolita morada que viaja). Puedes cortarla en el aire.
- **Bulo con corona:** es la raíz de una cadena. Si lo atrapas, caen todas sus copias de una vez.
- **Estrellas (noticias):** salen del kiosco del parque. Al recogerla, **quédate quieto un segundo** para mirarla: si es real, llévasela a un vecino y queda protegido. Algunas son **Bulos disfrazados** (tienen un ojito): si la miras antes, la descubres; si la compartes sin mirar, contagias al vecino.
- **Antena del Bot:** suelta Bulos sin parar. Golpéala varias veces para apagarla (después pone otra en otro lugar).
- **Eventos al azar:** peleas entre vecinos (si no las calmas se rompe la amistad), el **Bulo viral** con 10 segundos para detenerlo, rumores sobre candidatos, lluvia de noticias, campañas de convivencia y vecinos que reportan por su cuenta.

## Personajes (fuerza pareja, cada uno ayuda distinto)

![Elegir personaje](docs/img/cazabulos/seleccion.png)

| Personaje | Rol | Ventaja | Poder (X) |
|---|---|---|---|
| **Ana** (amarillo) | Periodista | Ve los Bulos disfrazados y revisa las noticias al instante | **Flash:** congela a los Bulos cercanos |
| **Beto** (rosa) | Influencer | Lo que entrega les llega también a los amigos del vecino (¡y si es falso, también!) | **En vivo:** protege a todos los vecinos cercanos |
| **Caro** (verde) | Ciudadana | Corre más rápido y protege a quienes reconcilia | **Red gigante:** atrapa todos los Bulos cercanos |
| **Dani** (azul) | Candidato | Su protección dura el doble y compite en la elección | **Discurso:** cura a los vecinos cercanos y empuja a los Bulos |

La piel y el color de pelo se pueden cambiar al elegir.

## Modos

- **Mismo computador (1 a 4):** no se comparte el teclado. Cada uno juega su turno de 60, 90 o 120 segundos y le pasa el teclado al siguiente. En cada ronda todos juegan **el mismo barrio con los mismos eventos** (misma semilla), así es justo. Hasta 3 rondas: mañana, tarde y noche.
- **En línea (2 a 4 computadores en la misma red):** uno crea la sala y los demás escriben la dirección que aparece. Todos juegan a la vez, ven a los rivales como fantasmas y el marcador en vivo.

Al final viene la **elección del alcalde**: si el barrio terminó informado gana un candidato con propuestas; si quedó lleno de Bulos gana Emilio Bot. Luego el podio con el ganador de la partida.

## Las estructuras de datos y para qué sirven

| Estructura | Archivo | Problema que resuelve en el juego |
|---|---|---|
| Grafo social (lista de adyacencia, peso = confianza) | `cazabulos/estructuras/grafo.py`, `cazabulos/ciudad.py` | Por los hilos viajan los Bulos. El viral se riega con **BFS** (quién lo recibe, cuántos y en qué orden). Las peleas **eliminan aristas** y las campañas **agregan aristas**. Los Bulos buscan al vecino de mayor **grado**. |
| Grafo de la ciudad (lugares y esquinas, peso = distancia) | `cazabulos/mapa.py`, `cazabulos/ciudad.py` | **Dijkstra** da la ruta más corta: la flecha que guía al jugador y el camino de los vecinos entre zonas sin atravesar edificios. |
| Árbol n-ario de mutaciones | `cazabulos/estructuras/arbol_mutaciones.py` | Cada Bulo que salta es hijo del anterior. Atrapar uno **elimina su subárbol** (preorden): cortar la raíz tumba toda la cadena. |
| Árbol de decisiones | `cazabulos/estructuras/arbol_decision.py` | El camino de cada noticia (mirarla, compartirla sin mirar, dejarla) y sus consecuencias en puntos e indicadores. Se dibuja al final del turno con las veces que pasaste por cada rama. |
| AVL | `cazabulos/estructuras/avl.py`, `cazabulos/guardado.py` | La tabla de récords ordenada (insertar, eliminar el menor, recorrido en orden). |

Más detalle en [docs/ENTREGA_FINAL.md](docs/ENTREGA_FINAL.md).

## Instalar y ejecutar

```bash
pip install -r requirements.txt
python main.py
```

En Windows también funciona con doble clic en `jugar.bat`. Servidor sin ventana para el modo en línea: `python servidor.py`.

Pruebas:

```bash
python -m unittest discover tests
```

## Créditos

- Gráficos del barrio y de los vecinos: [Kenney](https://kenney.nl) (*RPG Urban Pack* y *Roguelike Modern City*, licencia CC0). Las licencias están en `cazabulos/assets/kenney/`.
- Protagonistas, Bulos, estrellas y antena: pixel art propio del equipo, hecho en código (`cazabulos/personajes.py`, `cazabulos/sprites.py`).
- Fuentes: Fredoka y Nunito (licencia SIL OFL).
- Sonidos y música: sintetizados en el juego con numpy (`cazabulos/sonido.py`).

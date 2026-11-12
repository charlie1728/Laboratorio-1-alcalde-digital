# Contexto para Claude: Cazabulos · Alcalde Digital

Este archivo resume todo lo trabajado con el usuario hasta el 12-nov-2026, para seguir en otro chat
(por ejemplo, desde el teléfono, en una sesión en la nube). Léelo completo antes de hacer cualquier cosa.

## Cómo trabajar con el usuario (muy importante)

- **Responde SIEMPRE en español.** Se ha molestado mucho cuando se le respondió en inglés. Esto incluye
  los mensajes de commit, los comentarios del código, los textos del juego y los resúmenes.
- Es estudiante de Estructura de Datos II (Universidad del Norte). No le interesa el detalle técnico:
  quiere resultados claros. Respuestas cortas, sin jerga; si algo es técnico, explícalo en una frase.
- **Cuando dice "lo más que puedas", es de verdad lo máximo**: ir a fondo y revisar con cuidado.
- Antes de cambiar algo que él ya aprobó, pregunta. No deshagas lo que le gustó.
- **Commits:** al final de cada tarea, con mensaje en español y al final la línea
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Se trabaja en `main`.
  Si no puedes subir a `main`, crea una rama y un pull request y díselo en una frase.
- **Carpeta raíz solo con lo esencial**: `README.md`, `main.py`, `jugar.bat`, `requirements.txt`,
  `cazabulos/`, `docs/`. No dejes archivos sueltos en la raíz (scripts de prueba, capturas, etc.).
- **Nunca captures la pantalla del computador.** Para ver el juego, guarda la imagen que dibuja el propio
  juego (ver "Cómo probar"). En la nube no hay pantalla: usa `SDL_VIDEODRIVER=dummy`.
- Como te escribe desde el teléfono y no puede abrir el juego, cuando cambies algo visual **guarda una
  imagen del juego y envíasela** para que la vea.
- Los cambios de dificultad o de números del juego se miden antes con partidas simuladas (ver
  "Equilibrio"). Él pide todo **"moderado"**: que el juego no se vuelva imposible.

## El laboratorio (lo que pide el enunciado)

Videojuego educativo sobre el uso responsable de las redes sociales, en Python (pygame). Ciudad Nova
elige alcalde; en la red social Civitas circulan rumores. Pide:

- 2 a 4 jugadores con roles distintos: Ciudadano, Periodista, Influencer y Candidato.
- **Árboles y grafos que resuelvan problemas reales del juego**:
  - el árbol de decisiones de cada publicación (compartir, verificar, ignorar, reportar);
  - el grafo de la ciudad y el grafo social;
  - la propagación de publicaciones por el grafo: quién la recibe, cuántos, qué tan rápido, si es
    verdadera y qué consecuencias tiene.
- Eventos aleatorios, decisiones con tiempo límite (viral de 10 s) e indicadores de la ciudad
  (información, confianza, convivencia, bienestar, desinformación, conflictos).
- Puntuación individual, elección del alcalde según el comportamiento, multijugador cliente-servidor con
  sockets, interfaz gráfica, al menos un componente inclusivo, sección de AYUDA y elementos motivadores.
- **No usar preguntas explícitas de conocimiento**: se aprende con mecánicas y consecuencias.
- Entrega final: 16 al 20 de noviembre de 2026. **VI Feria Gamer: 26 de noviembre de 2026** (lo juegan
  niños: tiene que ser fácil, vistoso y con poquísimo texto en pantalla).

`docs/ENTREGA_FINAL.md` explica cómo el juego cumple cada punto (y las respuestas para la sustentación).

## El juego: Cazabulos

**La idea:**
- Los Bulos (rumores morados) vuelan desde la antena del Bot hacia los vecinos. Al vecino que alcanzan
  se le suben a la cabeza y lo vuelven morado.
- Un morado, si nadie lo cura, le pasa el Bulo a un amigo por la red social.
- El jugador camina por el barrio y lanza su herramienta para atrapar Bulos y curar morados.
- Las estrellas son noticias verdaderas: al tocarlas, la verdad viaja por el grafo (BFS) y protege.
- **Gana quien salve a más vecinos.**

**Los personajes** (fuerza pareja, poderes que se ven distintos):

| Personaje | Rol | Ventaja | Poder |
|---|---|---|---|
| Ana | Periodista | Ve todos los Bulos y su periódico atraviesa varios | Congela con escarcha |
| Beto | Influencer | Su cura llega también a los amigos | Protege a los vecinos con corazones y burbujas |
| Caro | Ciudadana | Corre más rápido | Red gigante |
| Dani | Candidato | A quien cura no le vuelven a entrar Bulos por un rato | Discurso con ondas de megáfono |

**Misiones contra la desinformación** (una a la vez; hay que ir al círculo y quedarse hasta llenar las
barritas):
- **Verificar un rumor** del enunciado («¿Cierran el colegio?», «¿El alcalde roba?»…): revisar la fuente
  en ese lugar y publicar el desmentido en el Kiosco. El desmentido viaja por BFS de 2 niveles. Si se
  vence, el rumor se riega (sale un Bulo).
- **Reportar la cuenta del Bot** en la Alcaldía: las antenas se callan 20 s.
- **Taller en el Colegio:** protege a los vecinos de mayor grado del grafo.
- **Charla en la Plaza:** agrega amistades (aristas) y calma las peleas.

**Datos verificados (munición):**
- 15; cada lanzamiento gasta uno.
- Cualquier misión los recarga todos, las estrellas dan 2 y vuelve solo uno cada 5 s.
- Con 3 o menos, la línea guía (Dijkstra) lleva a la misión.

**Controles:**
- Flechas o WASD para moverse, Espacio para lanzar y X para el poder.
- Tab muestra u oculta el "Estado del barrio" (empieza oculto) y Esc pausa.
- Control USB: A lanza, B o X usan el poder, Y abre el estado y Start pausa.

**Modos:**
- "¡Jugar ya!": 90 s.
- Mismo PC: 1 a 4 jugadores por turnos, mismo barrio y misma semilla, hasta 3 rondas (mañana, tarde, noche).
- En línea: servidor TCP.
- Al final, la elección del alcalde y el podio.

**Modo feria:**
- Abre en una ventana grande; F11 pasa a pantalla completa.
- Vuelve solo al inicio tras 90 s sin tocar nada.
- "Salir" pregunta antes de cerrar.
- Si algo falla, se rescata y se anota en `cazabulos_error.log`.

## Dónde está cada cosa (`cazabulos/`)

| Archivo | Qué hace |
|---|---|
| `config.py` | Constantes (tamaño 1280x720, `ESC=3`, `TILE=16`, velocidad del jugador 100) |
| `mundo.py` | Toda la simulación: vecinos, Bulos, contagio, estrellas, antenas, viral, peleas, misiones (`MISIONES`, `Encargo`, `_encargos`), munición (`MUNICION_MAX`, `RECARGA_SOLA`), poderes (`_poder`), indicadores |
| `estructuras/` | `grafo.py` (BFS, DFS, Dijkstra, grado), `arbol_mutaciones.py` (cadena de Bulos: atrapar la raíz tumba la cadena), `arbol_decision.py` (árbol de cada publicación, con las ramas de las misiones), `avl.py` (récords) |
| `mapa.py`, `ciudad.py`, `trafico.py` | El barrio (64x46 tiles de Kenney), el grafo de la ciudad y las rutas, los carros y los semáforos |
| `texturas.py` | Texturas generadas con numpy al cargar el mapa: pasto, bordes orgánicos, laguna, sombras suaves, relieve de los edificios |
| `ambiente.py`, `hierba.py` | La vida del barrio: agua, patos, palomas, fuente, flores, nubes, luciérnagas; y la hierba alta tipo Pokémon. Usan su propio azar: **no cambian el juego** (hay una prueba de eso) |
| `render.py` | Dibuja el mundo: bordes, árboles que se mecen, efectos de los poderes, noche con luces, bloom (se apaga solo si el PC va lento), estación de la misión |
| `hud.py` | Tarjeta del jugador con los datos en barritas, reloj, minimapa, estado del barrio (Tab), columna izquierda con la misión, los avisos y la pista |
| `pantallas/` | Menú, selección, juego, resultados, elección, podio, ayuda (8 páginas), historia, en línea |
| `red/` | Servidor y cliente TCP (mensajes JSON) |
| `app.py`, `mando.py`, `guardado.py`, `sonido.py` | Ventana y bucle, control USB, opciones, récords y logros, sonidos sintetizados |
| `pruebas/` | 79 pruebas |

`docs/DISENO_CAZABULOS.md` tiene el historial de lo que pidió el usuario en cada ronda y los tiles útiles.

## Gustos del usuario

**Le encanta:**
- El parque de día como está ahora: pasto con texturas, caminos de bordes orgánicos, laguna con espuma,
  patos con su reflejo, flores y sombras suaves.
- Que todo tenga borde oscuro.
- Los poderes distintos.

**Rechaza:**
- Textos encima del juego y mensajes en el centro de la pantalla.
- Paneles que tapan el mapa.
- Luces que "queman" (dijo de la noche: "super extremista… vas bien pero que no te pases").
- Franjas negras a los lados de la ventana.
- Mucha información a la vez para los niños.

**Hierba alta:** primero se hizo con hojitas verticales y le encantó. Después otra herramienta (Gemini)
la cambió por matas más tupidas con borde verde. Se le preguntó cuál dejar y no respondió: quedó la de
Gemini (`hierba.py`). No la cambies sin preguntarle.

## Estado al 12-nov-2026

- `main` en GitHub tiene el juego completo (se unió la rama `cazabulos`, que también sigue existiendo).
- Pasan las 79 pruebas y los recorridos completos de 2 jugadores, 4 jugadores y en línea.
- En ventana real va a 60 fps.
- Equilibrio medido con jugadores automáticos (20 partidas de 2 minutos por personaje, 3 estilos):
  - los cuatro personajes quedan a menos de 10 % entre sí;
  - se salvan unos 10 a 15 vecinos de 18.
- Último trabajo:
  - misiones ligadas al laboratorio y munición limitada;
  - "Estado del barrio" oculto con Tab;
  - avisos a la izquierda;
  - velocidad 100.
- No hay nada pendiente pedido por el usuario. Espera sus instrucciones.

## Cómo probar

```bash
python -m pip install -r requirements.txt      # pygame y numpy
python -m unittest discover -s cazabulos/pruebas -t .
```

**Ver el juego sin pantalla.** Guarda la imagen del propio juego; nunca captures la pantalla:

```python
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init(); pant = pygame.display.set_mode((1280, 720))
from cazabulos.mundo import Mundo
from cazabulos.render import Render
from cazabulos.hud import Hud
m = Mundo(5, "ana", duracion=120, ronda=1)        # ronda=3 es de noche
r = Render(m, None, {}); h = Hud(m, r, None, 1, 1, {})
for _ in range(180):
    m.actualizar(1 / 60, {}); r.actualizar(1 / 60); h.actualizar(1 / 60)
r.dibujar(pant); h.dibujar(pant)
pygame.image.save(pant, "/tmp/juego.png")       # guárdala fuera del repositorio y envíasela
```

- Para mover al jugador, pasa en la entrada `{"der": True, "accion": True, "poder": True}` (también
  `"izq"`, `"arriba"`, `"abajo"`).
- Para las pantallas completas, usa `App` de `cazabulos/app.py` con su bucle real `app._cuadro(dt, 1.0)`.
  Así se prueban los fundidos y los cambios de escena; ya se escapó un error por no hacerlo.

**Equilibrio.**
- Haz un jugador automático que camine con `ciudad.ruta` (Dijkstra) hacia lo más cercano y lance cuando
  esté a menos de 110 px. Que vaya a la misión cuando le queden 3 datos o menos.
- Juega 20 semillas por personaje con 3 estilos:
  - experto;
  - niño (lanza con probabilidad 0,15 por cuadro y se distrae el 30 % del tiempo);
  - deja ESPACIO presionado.
- Compara los puntos y los vecinos salvados (`Mundo.resumen()`).

**Rendimiento:** dibujar un cuadro tarda unos 6 a 8 ms. Si agregas efectos, mide que no pase de unos 11 ms.

# Cazabulos: diseño

Rama `cazabulos`. El juego vive en `cazabulos/`. El código viejo (`alcalde/`, "Corta la mentira") se quitó de la carpeta y queda en el historial de git; las entregas anteriores están en `docs/historial/`.

## La idea en 4 frases

Los **Bulos** (rumores morados) se suben a la cabeza de los vecinos y los vuelven morados; un vecino morado, si nadie lo cura, se lo pasa a un amigo por la red social. Tú caminas con las flechas y con **Espacio** lanzas tu herramienta: atrapas los Bulos y curas a los morados. Las **estrellas** son noticias verdaderas: con solo tocarlas, la verdad les llega al vecino más cercano y a sus amigos. Cada jugador juega su turno en el mismo barrio y gana quien salve a más gente.

## Estado

El juego está completo y jugable (ver README y `docs/ENTREGA_FINAL.md`): mundo, render, HUD, todas las pantallas, ayuda, opciones, récords, elección, podio, modo en línea, control USB y modo feria, con 79 pruebas.

## Lo que pidió el usuario al probarlo

**Primera ronda (render):**

1. Personajes que se distingan: hecho (silueta, color y objeto propios, más altos que los vecinos).
2. Hitbox y carros: los carros de lado ocupan **3x2 tiles** (antes se usaba solo la fila de abajo y se veían cortados y montados en el andén). Cada carril mide 2 tiles y el carro va centrado en su carril. Los carros frenan ante peatones y en el semáforo; nunca salen del carril.
3. Mapa que no sea un cubículo: mapa de 64x46 tiles (unas 2,5 x 3 pantallas) con cámara que sigue al jugador. Tiene 4 zonas de tamaños distintos, avenidas, cebras, un parque con laguna y caminos que serpentean.

**Segunda ronda (después de jugarlo):**

4. Pantalla completa al abrir: hecho (y F11 para cambiar).
5. Que abra con el símbolo del juego y no con el de Python: ícono propio (Bulo con corona), identificador de Windows para la barra de tareas y acceso directo con pythonw (sin consola).
6. Demasiados mensajes y demasiadas cosas a la vez:
   - Se quitaron los globos de diálogo, los nombres y los banners.
   - Quedan avisos de una o dos palabras y flechas con dibujos.
   - Solo se dibujan los hilos que importan en ese momento.
   - La cuenta regresiva explica el juego en tres dibujos.
7. Juego más simple: los Bulos infectan (vuelven morada a la gente) y uno los atrapa y cura. Se quitó mirar las noticias quieto y las estrellas falsas, y todo se arregla lanzando.
8. Más tiempo: turnos de 2 minutos (90 segundos en "¡Jugar ya!").

**Tercera ronda (gráficos):**

9. Personaje un poco más rápido: 92 pixeles por segundo (antes 78); después, 100.
10. "Que todo tenga bordes": `recursos.borde()` le pone un borde oscuro de 1 pixel a cada imagen (se calcula una vez y se guarda). En el mapa, los edificios y los objetos planos llevan borde y sombra; el pasto tiene textura y un borde donde se encuentra con andenes y caminos.
11. "Que el mapa tenga animaciones": `cazabulos/ambiente.py` (la vida del barrio, con su propio azar para no cambiar el juego): agua con brillos y ondas, fuente que salpica, pata y patitos, nenúfares, palomas que huyen del jugador, mariposas, hojas, flores que se mecen, banderas, sombras de nubes, polvo al correr, estela de los Bulos, destellos de las estrellas y humo de los carros. En `render.py` los árboles se mecen (la punta más que el medio), los semáforos brillan y de noche se prenden las ventanas, los faroles y los faros; luciérnagas en el parque. Una viñeta suave oscurece las orillas de la pantalla.
12. Árboles y arbustos verde oscuro de Kenney (tiles 403/406/440/443/514/517) tenían el mismo verde del pasto: se repintan de verde pino (`mapa.tile_cosa`).

**Cuarta ronda (aspecto profesional):**

13. `cazabulos/texturas.py` (numpy, una sola vez al cargar el mapa, menos de 1 segundo):
    - pasto con paleta de 5 verdes, tramado y matitas;
    - bordes del pasto redondeados con desenfoque + ruido + umbral (solo hacia caminos y arena; hacia andenes y plaza va un bordillo);
    - texturas de caminos, losas, asfalto y arena;
    - laguna con forma orgánica, piedras, profundidad y espuma;
    - sombras suaves y oclusión de edificios y objetos;
    - relieve de los edificios.
    Sin numpy el mapa se dibuja como antes.
14. `cazabulos/hierba.py`: hierba alta por tiles (mancha de ruido), cuadros de viento, abierta cuando alguien está adentro, hojitas al entrar y la parte de adelante encima de los pies.
15. `render.py`:
    - sombras de los árboles en vivo (se mueven con la copa);
    - sombras suaves de la gente (de noche, alargadas lejos del farol más cercano);
    - bloom (achicar, umbral, difuminar y sumar; unos 3 ms) que se apaga solo si más de la mitad de los cuadros pasan de 12 ms durante un rato.
16. El usuario aprobó el aspecto del día ("esto sí me encanta") y pidió bajar las luces de noche: los faroles ahora aclaran la noche sin borrarla (`sprites.luz(radio, fuerza)`).
17. "El poder de Beto se ve igual al de Ana": `Render._nuevo_poder` y `Render._poderes` dibujan cada uno distinto.
    - Ana: onda de escarcha con picos y copos en los Bulos congelados.
    - Beto: arcos de transmisión y corazones que vuelan a cada vecino con escudo, y una burbuja dorada al llegar.
    - Caro: red con círculos, radios y nudos que se abre y se cierra.
    - Dani: anillos entrecortados de megáfono y estelas en los Bulos aturdidos.

**Quinta ronda (siempre hay algo que hacer):**

18. Un análisis de Gemini agregó "encargos" genéricos. Se rehicieron con el contexto del laboratorio como **misiones contra la desinformación** (`mundo.MISIONES`, `Mundo._encargos`):
    - verificar un rumor (fuente → Kiosco, desmentido por BFS; si se vence, el rumor se riega);
    - reportar la cuenta del Bot (antenas calladas 20 s);
    - taller (protege a los de mayor grado);
    - charla (aristas nuevas y peleas calmadas).
    En el árbol de decisiones hay dos ramas nuevas: `falsa → verificar → desmentida` y `falsa → denunciar → denunciada`.
19. **Datos verificados:** munición de 15 (`MUNICION_MAX`). Toda misión la recarga completa, las estrellas dan 2 y vuelve sola uno cada 5 s. Con 3 o menos, la guía apunta a la misión. Ana lanza cada 0,26 s (antes 0,22: con datos limitados era la que más gastaba). La antena reaparece a los 12 s (Gemini la había bajado a 10) y un rumor vencido suelta 1 Bulo.
    - Equilibrio elegido después de medir 5 configuraciones con jugadores automáticos (20 partidas por personaje, 3 estilos): a menos de 10 % entre personajes y 1 o 2 vecinos menos que con munición infinita.
20. HUD:
    - "Estado del barrio" oculto por defecto (`Hud.ver_estado`, Tab / Y);
    - avisos, pista y misión en una columna a la izquierda;
    - barritas de la misión en la estación (encima de todo) y en su tarjeta;
    - datos en barritas en la tarjeta del jugador.
21. Velocidad del jugador 100.

## Mapa (en tiles)

- Avenida horizontal: calzada en las filas 20-23 (arriba va hacia la izquierda, abajo hacia la derecha), andenes en 18-19 y 24-25.
- Carrera vertical: calzada en las columnas 44-47 (izquierda baja, derecha sube), andenes en 42-43 y 48-49. Cruce con semáforo.
- Noroeste: Colegio con patio de arena, Alcaldía, plaza con fuente y casas.
- Noreste: Mercado con puestos de toldo a rayas.
- Suroeste: Parque Central con laguna, kiosco de noticias (de ahí salen las estrellas) y picnic.
- Sureste: Terminal de buses y casas.

## Tiles útiles (hoja ciudad)

- Techos (9 partes, bloque de 4x4): rojo desde 0, gris desde 8, gris claro desde 16, beige desde 24. Fila 0 = borde de arriba, filas 37 y 74 = centro, fila 111 = borde de abajo; columna 0 izquierda, 1-2 centro, 3 derecha.
- Fachadas debajo del techo (3 filas, columnas 0..3 = izq, centro, centro, der): rojo 148/185/407, gris 152/189/411, beige 156/193/415, vitrina moderna 160/197/419.
- Ventanas 617/654/691/728, puerta 800 (arriba) + 837 (abajo), toldo 467-470, vitrina 908-910, poste de luz 597/634/671.
- Suelo: pasto 888/889, andén 704/741, plaza 710/711, camino beige 707/744, arena 895, grava 896, asfalto 714, cebra 826.
- Parque: borde de piedra 32-34/69-71/106-108; agua con borde (9 partes) 174-176/211-213/248-250; fuente con estatua 177-178/214-215/251-252; árboles de 2 tiles 401-406 (+37); arbustos 512-517; banca 572/573; matera 179-181; sombrilla 553/590; hidrante 533; caneca 496.
- Toldos de mercado a rayas 357-363, 394-400, 431-437; cajas de fruta 675-679.
- Carros de lado (3x2): verde 623-625/660-662 (mira a la izquierda) y 626-628/663-665 (mira a la derecha); gris 771-776/808-813; naranja 919-924/956-961.
- Carros de arriba (2x2): verde 697-698/734-735 (sube) y 699-700/736-737 (baja); gris 845-848/882-885; naranja 993-996/1030-1033. Bus rojo de frente en la hoja urbana 447/448/474/475.
- Vecinos (hoja urbana): 6 tipos, columna 23 = izquierda, 24 = frente, 25 = espalda, 26 = derecha; filas 3k, 3k+1, 3k+2 = quieto y dos pasos.

## Estructuras de datos y para qué sirven

| Estructura | Problema que resuelve en el juego |
|---|---|
| Grafo social (lista de adyacencia con peso = confianza) | Hilos entre vecinos. Un vecino morado se lo pasa al amigo en quien más confía (mayor peso). La verdad de las estrellas y el viral se riegan con BFS (quién lo recibe, cuántos y en qué orden). Las peleas borran hilos y las campañas de convivencia crean hilos nuevos. Los Bulos buscan al vecino con más amigos (grado). DFS para ver las comunidades al final. |
| Grafo de la ciudad (zonas y esquinas, peso = distancia) | Dijkstra para la flecha que guía al jugador hacia lo más urgente y para que los vecinos caminen entre zonas sin atravesar edificios. |
| Árbol n-ario de mutaciones | Cada Bulo que salta a otro vecino es hijo del anterior. Si atrapas la raíz (el Bulo con corona) caen todos sus hijos (eliminar subárbol, recorrido en preorden para la cadena). |
| Árbol de decisiones de cada publicación | Publicación falsa (Bulo): la atrapas (reportar) o alguien se la cree; si se la cree, lo curas (verificar) o se la pasa a un amigo. Publicación verdadera (estrella): la compartes o la ignoras. Cada hoja guarda puntos y cambios en los indicadores. Al final se dibuja el árbol con cuántas veces se pasó por cada rama. |
| AVL | Tabla de récords ordenada (recorrido en orden para el top 10). |


# Cazabulos: diseño

Rama `cazabulos`. El juego vive en `cazabulos/`. El código viejo (`alcalde/`, "Corta la mentira") se quitó de la carpeta y queda en el historial de git; las entregas anteriores están en `docs/historial/`.

## La idea en 4 frases

Los **Bulos** (rumores morados) se suben a la cabeza de los vecinos y los vuelven morados; un vecino morado, si nadie lo cura, se lo pasa a un amigo por la red social. Tú caminas con las flechas y con **Espacio** lanzas tu herramienta: atrapas los Bulos y curas a los morados. Las **estrellas** son noticias verdaderas: con solo tocarlas, la verdad les llega al vecino más cercano y a sus amigos. Cada jugador juega su turno en el mismo barrio y gana quien salve a más gente.

## Estado

El juego está completo y jugable (ver README y `docs/ENTREGA_FINAL.md`): mundo, render, HUD, todas las pantallas, ayuda, opciones, récords, elección, podio, modo en línea, control USB y modo feria, con 68 pruebas.

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

9. Personaje un poco más rápido: 92 pixeles por segundo (antes 78).
10. "Que todo tenga bordes": `recursos.borde()` le pone un borde oscuro de 1 pixel a cada imagen (se calcula una vez y se guarda). En el mapa, los edificios y los objetos planos llevan borde y sombra; el pasto tiene textura y un borde donde se encuentra con andenes y caminos.
11. "Que el mapa tenga animaciones": `cazabulos/ambiente.py` (la vida del barrio, con su propio azar para no cambiar el juego): agua con brillos y ondas, fuente que salpica, pata y patitos, nenúfares, palomas que huyen del jugador, mariposas, hojas, flores que se mecen, banderas, sombras de nubes, polvo al correr, estela de los Bulos, destellos de las estrellas y humo de los carros. En `render.py` los árboles se mecen (la punta más que el medio), los semáforos brillan y de noche se prenden las ventanas, los faroles y los faros; luciérnagas en el parque. Una viñeta suave oscurece las orillas de la pantalla.
12. Árboles y arbustos verde oscuro de Kenney (tiles 403/406/440/443/514/517) tenían el mismo verde del pasto: se repintan de verde pino (`mapa.tile_cosa`).

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


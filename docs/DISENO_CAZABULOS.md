# Cazabulos: diseño y estado de la reconstrucción

Rama `cazabulos`. El juego nuevo vive en `cazabulos/`. El código viejo (`alcalde/`, "Corta la mentira") sigue en el historial de git y se quitará cuando el juego nuevo funcione.

## La idea en 4 frases

Caminas con las flechas por el barrio cazando **Bulos** (rumores morados que vuelan) y les lanzas tu herramienta con **Espacio** antes de que se suban a la cabeza de los vecinos. Recoges **estrellas** (noticias) y se las llevas a la gente; si te quedas quieto un momento con la estrella, ves si es real o un Bulo disfrazado. La **antena del Bot** suelta Bulos y se apaga a golpes. Cada jugador juega su turno en el mismo barrio y gana quien salve a más gente.

## Lo que ya está hecho

- `cazabulos/config.py`: pantalla 1280x720, tiles de 16 px dibujados a x3.
- `cazabulos/recursos.py`: hojas de Kenney (CC0), tiles, bloques, escalado sin borrosidad, fuentes Fredoka/Nunito, silueta y contorno.
- `cazabulos/personajes.py`: los 4 protagonistas en pixel art propio de 16x24 (los vecinos de Kenney miden 16x16, así que los jugadores siempre se ven más grandes). Frente, espalda y lado con pasos de caminar.
  - **Ana, Periodista** (amarillo): boina roja, melena negra, gabardina, cámara al pecho.
  - **Beto, Influencer** (rosa): copete fucsia alto, gafas de sol, buzo con capucha, celular.
  - **Caro, Ciudadana** (verde): gorra al revés, pelo naranja con cola, pecas, overol, morral.
  - **Dani, Candidato** (azul): peinado con raya, traje, corbata roja, escarapela dorada.
  - Piel y color de pelo se pueden cambiar (personalización = componente inclusivo).
- `cazabulos/assets/`: hojas `ciudad.png` (Roguelike Modern City, 37 columnas) y `urbano.png` (RPG Urban Pack, 27 columnas) con sus licencias CC0, y las fuentes con su licencia OFL.

## Correcciones que pidió el usuario sobre el render

1. Personajes que se distingan: hecho (silueta, color y objeto propios, más altos que los vecinos).
2. Hitbox y carros: los carros de lado ocupan **3x2 tiles** (antes se usaba solo la fila de abajo y se veían cortados y montados en el andén). Cada carril mide 2 tiles y el carro va centrado en su carril. Los carros frenan ante peatones y en el semáforo; nunca salen del carril.
3. Mapa que no sea un cubículo: mapa de 64x46 tiles (unas 2,5 x 3 pantallas) con cámara que sigue al jugador. Tiene 4 zonas de tamaños distintos, avenidas, cebras, un parque con laguna y caminos que serpentean.

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
| Grafo social (lista de adyacencia con peso = confianza) | Hilos entre vecinos. Un vecino con Bulo se lo pasa a sus amigos por los hilos (BFS: quién lo recibe, cuántos y en qué orden). Las peleas borran hilos y las campañas de convivencia crean hilos nuevos. Los Bulos buscan al vecino con más amigos (grado). DFS para ver las comunidades al final. |
| Grafo de la ciudad (zonas y esquinas, peso = distancia) | Dijkstra para la flecha que guía al jugador hacia lo más urgente y para que los vecinos caminen entre zonas sin atravesar edificios. |
| Árbol n-ario de mutaciones | Cada Bulo que salta a otro vecino es hijo del anterior. Si atrapas la raíz (el Bulo con corona) caen todos sus hijos (eliminar subárbol, recorrido en preorden para la cadena). |
| Árbol de decisiones de la noticia | Encuentras una estrella: la miras (verificar), la entregas sin mirar (compartir) o la dejas (ignorar); si la miras: ¿es real? sí, la entregas / no, se reporta sola. Cada hoja guarda puntos y cambios en los indicadores. Al final se dibuja el árbol con cuántas veces pasaste por cada rama. |
| AVL | Tabla de récords ordenada (recorrido en orden para el top 10). |

## Estado del mapa (`cazabulos/mapa.py`, primera versión)

Ya dibuja el barrio completo con colisiones (`Mapa.libre(rect)`): edificios con techo y fachada, avenida y carrera con línea amarilla, bordillos, 5 cebras, plaza con fuente, bancas y postes, mercado con 6 puestos, parque con laguna, caminos y kiosco de noticias, terminal y casas. Vista previa: script `prev_mapa.py` del scratchpad.

Falta pulir: llenar más el parque (arbustos, flores, picnic, matera), buses estacionados en la terminal, cerca del patio del colegio y canchas pintadas, la fuente de la plaza más grande, más árboles en los bordes, semáforos dibujados con su luz, y carteles con mejor letra.

## Mecánicas pendientes de programar

- Ronda de 90 s por jugador, cuenta 3-2-1, aviso a los 10 s.
- Espacio = lanzar (con un poco de auto-apuntado) o, junto a un vecino, entregar estrella o calmar una pelea. X = poder del rol (se carga cazando).
- Poderes equilibrados: Ana ve los Bulos disfrazados y su Flash congela a los Bulos; Beto entrega la noticia también a los amigos del vecino (y si es falsa, la riega más) y su Transmisión protege a los de la pantalla; Caro es un poco más rápida, calma peleas al instante y su Red atrapa todo en un radio; Dani hace que la protección dure el doble y su Discurso empuja y cura en un radio.
- Eventos al azar (misma semilla para todos los jugadores de la ronda): noticia falsa, Bulo viral con 10 s para atraparlo (si no, contagia por BFS), rumor sobre un candidato, discusión entre vecinos, lluvia de noticias reales, campaña de convivencia, un vecino que reporta solo.
- 6 indicadores en vivo: información verificada, confianza, convivencia, bienestar digital, desinformación, conflictos.
- Mismo PC: 1 a 4 jugadores por turnos y rondas, pantalla de relevo con el personaje de cuerpo entero. En línea: servidor con sockets, todos juegan a la vez, marcador en vivo y fantasmas de los rivales.
- Elección final según lo que pasó en el barrio, podio, logros, récords, ayuda, opciones (subtítulos de sonidos, alto contraste, modo daltonismo, velocidad tranquila para niños).

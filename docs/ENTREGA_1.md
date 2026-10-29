# Primera entrega: árboles

> Esta página es la de la entrega 1. Desde la entrega 2 la interfaz cambió (personajes ilustrados, mapa y red social) y la propagación usa el grafo social: ver [ENTREGA_2.md](ENTREGA_2.md) y [ENTREGA_FINAL.md](ENTREGA_FINAL.md). Las estructuras de árbol y sus operaciones siguen siendo las mismas.

**Alcalde Digital: el árbol de mutaciones.** Criterios evaluados: árboles, pertinencia de la estructura, operaciones y recorridos, interfaz gráfica preliminar y relación del árbol con la lógica del juego.

El juego usa **dos árboles distintos**, cada uno para un problema diferente:

| | Árbol de Mutaciones | Archivo de Hechos |
|---|---|---|
| Variante | Árbol general (n-ario) con raíz y puntero al padre | Árbol AVL (BST auto-balanceado) |
| Archivo | `alcalde/estructuras/arbol_mutaciones.py` | `alcalde/estructuras/archivo_avl.py` |
| Qué guarda | La genealogía de un rumor: quién reenvió qué a partir de quién | Los hechos oficiales de Ciudad Nova, con su texto como clave |
| Para qué lo usa el jugador | Rastrear el origen, podar ramas y contener desmentidos | Verificar publicaciones |

---

## 1. Árbol de Mutaciones

### 1.1 ¿Qué problema resuelve?

Una publicación de Civitas no viaja intacta. Cada reenvío puede introducir **una** distorsión:

| Distorsión | Ejemplo |
|---|---|
| Cifra inflada | "3 días" pasa a ser "30 días" |
| Contexto eliminado | se borra "para fumigar contra el dengue" |
| Fuente inventada | "Alcaldía de Ciudad Nova" pasa a ser "Me llegó por cadena" |
| Hecho tergiversado | "cerrará" pasa a ser "venderá a una constructora" |
| Atribución falsa | "La Alcaldía" pasa a ser "El candidato Tomás Arrieta" |

El juego necesita responder preguntas que dependen de **quién reenvió a partir de quién**:

- ¿De dónde salió esta versión? ¿En qué reenvío exacto apareció cada mentira?
- Si reporto esta publicación, ¿qué otras publicaciones caen con ella?
- ¿Cuánta gente vio versiones falsas? ¿Qué tan lejos llegó el rumor?

Una lista o una tabla pierde esa relación. El árbol la guarda de forma natural: cada reenvío tiene **exactamente un padre**, que es la publicación de la que salió, y ninguna publicación es su propio ancestro. Eso es justo la definición de árbol.

```
                 [Alcaldía] "cerrará el Parque 3 días para fumigar"     <- raíz (veraz)
                /           \
           [Ana]              [Beto]  "... 30 días ..."    <- MUTÓ AQUÍ: cifra inflada
           /    \                  \
      [Caro]   [Dani]             [Eva] "... 30 días."    <- MUTÓ AQUÍ: contexto eliminado
```

### 1.2 ¿Por qué esa estructura?

- **Cada nodo tiene un solo padre y cualquier cantidad de hijos.** Una publicación se puede reenviar muchas veces, pero cada reenvío sale de un solo lugar. Por eso es un árbol n-ario y no uno binario: forzarlo a binario sería artificial.
- **La profundidad tiene significado en el juego.** Profundidad *d* equivale a la *d*-ésima ola de propagación. La altura mide qué tan lejos viajó el rumor.
- **Los subárboles tienen significado en el juego.** Todos los reenvíos que dependen de una publicación están en su subárbol, así que **reportar = podar el subárbol**.
- **Las distorsiones se heredan hacia abajo.** Un hijo contiene las distorsiones de su padre más, a lo sumo, una nueva. Así, el primer nodo del camino a la raíz que tiene una distorsión es el lugar exacto donde apareció.

¿Por qué no un grafo? En la entrega 2 el grafo social dirá **quién puede** reenviarle a quién. El árbol guarda **lo que realmente pasó** con un rumor concreto. Es, en la práctica, el árbol de propagación que dejará un recorrido sobre ese grafo.

### 1.3 ¿Qué variante se usa?

Un **árbol general (n-ario) enraizado** con:

- `hijos: list` en cada nodo (el orden de los hermanos es el orden de llegada),
- `padre` en cada nodo, para subir hasta la raíz en O(profundidad),
- un **índice hash `id -> nodo`** en el árbol, para encontrar en O(1) el nodo que el jugador seleccionó con el mouse.

### 1.4 ¿Cómo se insertan y eliminan elementos?

| Operación | Método | En el juego | Costo |
|---|---|---|---|
| Insertar hoja | `insertar(padre_id, nodo)` | **Compartir**, cada ola de propagación, **desmentidos** | O(1) |
| Eliminar subárbol | `podar(id)` | **Reportar** una publicación falsa: cae con todos sus reenvíos | O(tamaño del subárbol) |
| Eliminar un solo nodo | `eliminar_nodo(id)` | Borrar mi publicación: sus hijos **se re-enganchan al abuelo** (borrar no deshace lo que ya se compartió) | O(k), con k = número de hijos |

- **`podar`** recorre el subárbol en **postorden** para sacar cada nodo del índice (primero los hijos y luego el padre, así no quedan huérfanos). Después lo desconecta de su padre. Si se poda la raíz, el caso queda cerrado.
- **`eliminar_nodo`** reemplaza el nodo, en la lista de hijos del padre, por sus propios hijos, y conserva el orden. Si se elimina la raíz, su primer hijo pasa a ser la nueva raíz y adopta a sus hermanos.

### 1.5 ¿Cómo se recorre?

| Recorrido | Método | Para qué lo usa el juego |
|---|---|---|
| **Preorden** (raíz y luego hijos) | `preorden()` | Leer el hilo en orden cronológico. **Contener un desmentido** (`inmunizar`): se marca el padre antes que sus reenvíos. |
| **Postorden** (hijos y luego raíz) | `postorden()`, `agregar()` | **Sumar de abajo hacia arriba** el alcance total y el alcance de versiones falsas, que alimentan el indicador de Desinformación. **Podar** sin dejar huérfanos. **Dibujar el árbol**: cada padre se centra sobre sus hijos ya ubicados. |
| **Por niveles** (BFS con cola) | `por_niveles()` | Cada nivel es una **ola de propagación**. La ola del final de cada ronda procesa el árbol por niveles, y los niveles más recientes son los que más se reenvían. |
| **Camino a la raíz** | `camino_a_raiz(id)` | **Rastrear origen** (habilidad del periodista). |
| **Punto de mutación** | `punto_de_mutacion(id)` | Sube por el camino y devuelve, para cada distorsión, el nodo más alto donde aparece. Se muestra en pantalla como "MUTÓ AQUÍ". |
| **Ancestro común (LCA)** | `ancestro_comun(a, b)` | ¿Desde qué publicación se separaron dos versiones? |

En la interfaz, la barra **Preorden / Postorden / Por niveles / Camino a raíz** anima cada recorrido sobre el árbol del caso actual: numera los nodos en el orden de visita y escribe la secuencia en el registro.

---

## 2. Archivo de Hechos (AVL)

### 2.1 ¿Qué problema resuelve?

**Verificar** es comparar una publicación contra el hecho oficial. Los hechos se buscan por una clave de texto, por ejemplo `parque-fumigacion`, y el archivo **cambia durante la partida**:

- **Insertar**: el periodista investiga un hecho que no estaba registrado. Sin ese hecho, nadie puede verificar esa historia y la verificación sale *inconclusa*.
- **Eliminar**: un hecho **vence** (evento aleatorio) y sale del archivo.
- **Buscar**: en cada verificación.

### 2.2 ¿Por qué esa estructura?

- Se necesitan **búsqueda, inserción y eliminación dinámicas** y además **listar en orden alfabético** (el panel del Archivo). Un árbol binario de búsqueda da las cuatro cosas. Un diccionario hash no da el orden.
- Un BST simple puede **degenerar en una lista**: si los hechos llegan en orden alfabético, la altura sería n. El AVL garantiza **altura O(log n)**.
- **En el juego el balance se nota:** el mensaje de cada verificación muestra el **número de comparaciones** hechas en el Archivo, y la vista del AVL resalta la ruta de búsqueda.

### 2.3 Variante

**AVL**: cada nodo guarda su altura y el factor de balance es `altura(izq) - altura(der)`, que siempre queda en {-1, 0, 1}. La vista del Archivo muestra `h` y `fb` de cada nodo, y la **bitácora de rotaciones**.

### 2.4 Inserción y eliminación

- **Insertar**: se inserta como en un BST (recursivo). Al volver de la recursión se actualizan las alturas y se rebalancea con los 4 casos: **LL** (rotación derecha), **RR** (rotación izquierda), **LR** (izquierda sobre el hijo y luego derecha) y **RL** (derecha sobre el hijo y luego izquierda).
- **Eliminar**: con 0 o 1 hijo se reemplaza por ese hijo. Con 2 hijos se copia el **sucesor en inorden** (el mínimo del subárbol derecho) y se elimina el sucesor. Luego se rebalancea en el camino de regreso.
- `es_avl_valido()` comprueba el orden BST, el balance y las alturas. Las pruebas lo llaman después de cada eliminación.

### 2.5 Recorridos

- **Inorden** (iterativo, con pila): lista los hechos de la A a la Z en el panel del Archivo.
- **Preorden**: sirve para serializar el árbol y reconstruirlo con la misma forma. Se usará para sincronizar con el servidor en la entrega final.
- **Búsqueda**: devuelve `(valor, comparaciones, ruta)`. La ruta se resalta en la vista.

---

## 3. Relación de los árboles con la lógica del juego

| Decisión del jugador | Qué pasa en la estructura | Consecuencia en el juego |
|---|---|---|
| Compartir | `insertar` una hoja (el influencer inserta 3) | Si era falsa: más desinformación y conflictos, y el jugador pierde reputación |
| Verificar | `buscar` en el AVL y comparar campo por campo | Revela qué distorsiones tiene. Muestra el costo en comparaciones |
| Verificar con el periodista (hecho ausente) | `insertar` en el AVL (con posibles rotaciones) | Desde ese momento todos pueden verificar esa historia |
| Reportar | `podar` el subárbol (postorden) | Cae toda la rama. Si era verdadera, el reporte se rechaza (reportar lo cierto también hace daño) |
| Rastrear origen (periodista) | `camino_a_raiz` + `punto_de_mutacion` | Señala el reenvío exacto donde apareció cada mentira |
| Amplificar desmentido (influencer) | `punto_de_mutacion`, luego `inmunizar` (preorden) desde el nodo más alto, más `insertar` un nodo de corrección | Contiene toda la rama falsa desde su origen |
| Desmentido oficial (candidato) | `inmunizar` + `insertar` | Si el rumor era sobre su campaña, gana apoyo extra |
| Alertar contactos (ciudadano) | Marca el nodo y sus hijos directos | Contención local y barata |
| Fin de ronda | `por_niveles`, e `insertar` con mutación aleatoria | El rumor crece y muta sobre todo en la última ola |
| Indicadores | `agregar` en postorden (alcance total y falso) | Desinformación = proporción del alcance que es falsa |

**Comportamiento que se busca fomentar:** verificar antes de compartir, entender que una noticia puede ser cierta en su origen y deformarse en el camino, que reportar lo verdadero también hace daño y que borrar no deshace lo que ya se compartió.

---

## 4. Otros requisitos ya adelantados

- **Interfaz gráfica** (Pygame): ciudad e indicadores, personaje del jugador, publicaciones, acciones con su costo, estado de la partida, puntuación y registro de resultados.
- **Componente aleatorio**: 8 tipos de evento. Noticia falsa, rumor sobre un candidato, noticia verdadera, publicación viral, discusión entre ciudadanos, campaña de convivencia, reporte de un ciudadano y vencimiento de un hecho.
- **Habilidad y tiempo**: evento viral con cuenta regresiva de 10 s (20 s para el ciudadano por su pasivo *pausa consciente*).
- **Inclusividad**: los estados no dependen solo del color. Cada estado tiene una **forma** propia (círculo, cuadrado, triángulo, rombo, anillo punteado), los indicadores negativos llevan rayas y la paleta es Okabe-Ito, apta para daltonismo. Hay un **modo de alto contraste** (tecla C) y **avisos visuales para cada sonido**. Dificultades que atiende: daltonismo, baja visión e hipoacusia.
- **Ayuda** con 6 secciones (tecla H), **logros**, **sonidos** sintetizados y **animaciones** (crecimiento, poda, pulso viral, recorridos).

## 5. Pruebas

`tests/test_arboles.py` tiene 14 pruebas: recorridos, altura, camino, punto de mutación, LCA, agregación, poda, eliminación con re-enganche, eliminación de la raíz, balance del AVL con 100 inserciones ordenadas, rotaciones LR y RL, eliminación con verificación de invariantes y partidas completas simuladas con varias semillas.

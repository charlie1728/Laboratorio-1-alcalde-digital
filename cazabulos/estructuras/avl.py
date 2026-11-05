"""Árbol AVL para la tabla de récords.

Problema: guardar muchas partidas y mostrar siempre las mejores en orden, rápido.
Variante: árbol binario de búsqueda balanceado (AVL). La clave es (puntos, desempate).
Insertar y eliminar en O(log n) con rotaciones; el recorrido en orden (al revés) da el top.
"""


class _Nodo:
    __slots__ = ("clave", "valor", "izq", "der", "alto")

    def __init__(self, clave, valor):
        self.clave = clave
        self.valor = valor
        self.izq = self.der = None
        self.alto = 1


def _alto(n):
    return n.alto if n else 0


def _act(n):
    n.alto = 1 + max(_alto(n.izq), _alto(n.der))


def _rot_der(y):
    x = y.izq
    y.izq = x.der
    x.der = y
    _act(y)
    _act(x)
    return x


def _rot_izq(x):
    y = x.der
    x.der = y.izq
    y.izq = x
    _act(x)
    _act(y)
    return y


def _balancear(n):
    _act(n)
    b = _alto(n.izq) - _alto(n.der)
    if b > 1:
        if _alto(n.izq.izq) < _alto(n.izq.der):
            n.izq = _rot_izq(n.izq)
        return _rot_der(n)
    if b < -1:
        if _alto(n.der.der) < _alto(n.der.izq):
            n.der = _rot_der(n.der)
        return _rot_izq(n)
    return n


class AVL:
    def __init__(self):
        self.raiz = None
        self.n = 0

    def __len__(self):
        return self.n

    def insertar(self, clave, valor=None):
        def ins(nodo):
            if nodo is None:
                self.n += 1
                return _Nodo(clave, valor)
            if clave < nodo.clave:
                nodo.izq = ins(nodo.izq)
            elif clave > nodo.clave:
                nodo.der = ins(nodo.der)
            else:
                nodo.valor = valor
                return nodo
            return _balancear(nodo)
        self.raiz = ins(self.raiz)

    def eliminar(self, clave):
        def minimo(nodo):
            while nodo.izq:
                nodo = nodo.izq
            return nodo

        def eli(nodo, clave):
            if nodo is None:
                return None
            if clave < nodo.clave:
                nodo.izq = eli(nodo.izq, clave)
            elif clave > nodo.clave:
                nodo.der = eli(nodo.der, clave)
            else:
                if nodo.izq is None or nodo.der is None:
                    self.n -= 1
                    return nodo.izq or nodo.der
                suc = minimo(nodo.der)
                nodo.clave, nodo.valor = suc.clave, suc.valor
                nodo.der = eli(nodo.der, suc.clave)
            return _balancear(nodo)
        self.raiz = eli(self.raiz, clave)

    def en_orden(self):
        res, pila, n = [], [], self.raiz
        while pila or n:
            while n:
                pila.append(n)
                n = n.izq
            n = pila.pop()
            res.append((n.clave, n.valor))
            n = n.der
        return res

    def mejores(self, k=10):
        return self.en_orden()[::-1][:k]

    def menor(self):
        n = self.raiz
        while n and n.izq:
            n = n.izq
        return n.clave if n else None

    def altura(self):
        return _alto(self.raiz)

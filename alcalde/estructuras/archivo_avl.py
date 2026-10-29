from __future__ import annotations

from typing import Any, Iterator, Optional

class NodoAVL:
    __slots__ = ("clave", "valor", "izq", "der", "altura")

    def __init__(self, clave: str, valor: Any):
        self.clave = clave
        self.valor = valor
        self.izq: Optional[NodoAVL] = None
        self.der: Optional[NodoAVL] = None
        self.altura = 1                      

def _h(n: Optional[NodoAVL]) -> int:
    return n.altura if n else 0

def _actualizar(n: NodoAVL) -> None:
    n.altura = 1 + max(_h(n.izq), _h(n.der))

def _balance(n: Optional[NodoAVL]) -> int:
    return _h(n.izq) - _h(n.der) if n else 0

class ArchivoHechosAVL:
    def __init__(self):
        self.raiz: Optional[NodoAVL] = None
        self._n = 0
        self.bitacora: list[str] = []                                          

    def __len__(self) -> int:
        return self._n

    def __contains__(self, clave: str) -> bool:
        return self.buscar(clave)[0] is not None

    @property
    def altura(self) -> int:
        return _h(self.raiz)

    def _rot_der(self, y: NodoAVL) -> NodoAVL:
        x = y.izq
        y.izq = x.der
        x.der = y
        _actualizar(y)
        _actualizar(x)
        self.bitacora.append(f"Rotación derecha en '{y.clave}'")
        return x

    def _rot_izq(self, x: NodoAVL) -> NodoAVL:
        y = x.der
        x.der = y.izq
        y.izq = x
        _actualizar(x)
        _actualizar(y)
        self.bitacora.append(f"Rotación izquierda en '{x.clave}'")
        return y

    def _rebalancear(self, n: NodoAVL) -> NodoAVL:
        _actualizar(n)
        b = _balance(n)
        if b > 1:                                                          
            if _balance(n.izq) < 0:                         
                n.izq = self._rot_izq(n.izq)
            return self._rot_der(n)                         
        if b < -1:                                                       
            if _balance(n.der) > 0:                         
                n.der = self._rot_der(n.der)
            return self._rot_izq(n)                         
        return n

    def insertar(self, clave: str, valor: Any) -> bool:
        nuevo = [False]

        def _ins(n: Optional[NodoAVL]) -> NodoAVL:
            if n is None:
                nuevo[0] = True
                return NodoAVL(clave, valor)
            if clave < n.clave:
                n.izq = _ins(n.izq)
            elif clave > n.clave:
                n.der = _ins(n.der)
            else:
                n.valor = valor
                return n
            return self._rebalancear(n)

        self.raiz = _ins(self.raiz)
        if nuevo[0]:
            self._n += 1
        return nuevo[0]

    def eliminar(self, clave: str) -> bool:
        borrado = [False]

        def _min(n: NodoAVL) -> NodoAVL:
            while n.izq:
                n = n.izq
            return n

        def _del(n: Optional[NodoAVL], k: str) -> Optional[NodoAVL]:
            if n is None:
                return None
            if k < n.clave:
                n.izq = _del(n.izq, k)
            elif k > n.clave:
                n.der = _del(n.der, k)
            else:
                borrado[0] = True
                if n.izq is None:
                    return n.der
                if n.der is None:
                    return n.izq
                suc = _min(n.der)
                n.clave, n.valor = suc.clave, suc.valor
                n.der = _del(n.der, suc.clave)
            return self._rebalancear(n)

        self.raiz = _del(self.raiz, clave)
        if borrado[0]:
            self._n -= 1
        return borrado[0]

    def buscar(self, clave: str) -> tuple[Any, int, list[str]]:
        n, comps, ruta = self.raiz, 0, []
        while n is not None:
            comps += 1
            ruta.append(n.clave)
            if clave == n.clave:
                return n.valor, comps, ruta
            n = n.izq if clave < n.clave else n.der
        return None, comps, ruta

    def inorden(self) -> Iterator[tuple[str, Any]]:
        pila, n = [], self.raiz
        while pila or n:
            while n:
                pila.append(n)
                n = n.izq
            n = pila.pop()
            yield n.clave, n.valor
            n = n.der

    def preorden(self) -> Iterator[str]:
        pila = [self.raiz] if self.raiz else []
        while pila:
            n = pila.pop()
            yield n.clave
            if n.der:
                pila.append(n.der)
            if n.izq:
                pila.append(n.izq)

    def es_avl_valido(self) -> bool:
        def _ok(n, lo, hi):
            if n is None:
                return True, 0
            if (lo is not None and n.clave <= lo) or (hi is not None and n.clave >= hi):
                return False, 0
            oi, hi_ = _ok(n.izq, lo, n.clave)
            od, hd = _ok(n.der, n.clave, hi)
            h = 1 + max(hi_, hd)
            return oi and od and abs(hi_ - hd) <= 1 and h == n.altura, h
        return _ok(self.raiz, None, None)[0]

    @classmethod
    def desde_preorden(cls, claves: list[str], valor_de) -> "ArchivoHechosAVL":
        """Reconstruye el árbol con la MISMA forma a partir de su preorden, sin rotar.

        Reinsertar las claves en preorden en un AVL dispararía rotaciones (el subárbol
        izquierdo completo llega antes que el derecho), así que se construye directo:
        cada clave es raíz de su rango (lo, hi) como en un BST. Lo usa el cliente para
        reconstruir el Archivo que le envía el servidor.
        """
        avl = cls()
        i = [0]

        def _construir(lo, hi):
            if i[0] >= len(claves):
                return None
            k = claves[i[0]]
            if (lo is not None and k <= lo) or (hi is not None and k >= hi):
                return None
            i[0] += 1
            n = NodoAVL(k, valor_de(k))
            n.izq = _construir(lo, k)
            n.der = _construir(k, hi)
            _actualizar(n)
            return n

        avl.raiz = _construir(None, None)
        avl._n = i[0]
        return avl

# Deteccion de interbloqueos y las cuatro condiciones de Coffman.

import bitacora


class Detector:
    def __init__(self):
        self.detectados = 0

    def construir_grafo(self, poseedores, esperas, info_recursos):
        grafo = {}

        def agregar(origen, destino):
            grafo.setdefault(origen, [])
            grafo.setdefault(destino, [])
            if destino not in grafo[origen]:
                grafo[origen].append(destino)

        for id_recurso, duenos in poseedores.items():
            for pid in duenos:
                agregar(id_recurso, pid)

        for pid, id_recurso in esperas.items():
            if id_recurso is None:
                continue
            info = info_recursos.get(id_recurso)
            if info and info["libres"] == 0:
                agregar(pid, id_recurso)

        return grafo

    def buscar_ciclo(self, grafo):
        visitados = set()
        en_camino = []

        def dfs(nodo):
            if nodo in en_camino:
                inicio = en_camino.index(nodo)
                return en_camino[inicio:] + [nodo]
            if nodo in visitados:
                return None
            visitados.add(nodo)
            en_camino.append(nodo)
            for vecino in grafo.get(nodo, []):
                ciclo = dfs(vecino)
                if ciclo:
                    return ciclo
            en_camino.pop()
            return None

        for nodo in list(grafo.keys()):
            ciclo = dfs(nodo)
            if ciclo:
                return ciclo
        return None

    def detectar(self, poseedores, esperas, info_recursos):
        grafo = self.construir_grafo(poseedores, esperas, info_recursos)
        ciclo = self.buscar_ciclo(grafo)
        if ciclo is None:
            bitacora.registrar("Se ejecuto la deteccion: no se encontro espera circular.", "DEADLOCK")
            return None

        procesos = [n for n in ciclo[:-1] if n not in info_recursos]
        recursos = [n for n in ciclo[:-1] if n in info_recursos]

        self.detectados += 1
        resultado = {
            "ciclo": ciclo,
            "procesos": procesos,
            "recursos": recursos,
            "grafo": grafo,
        }
        bitacora.registrar(
            f"INTERBLOQUEO DETECTADO. Ciclo: {' -> '.join(ciclo)}", "DEADLOCK")
        bitacora.registrar(
            f"Procesos involucrados: {procesos} | Recursos involucrados: {recursos}", "DEADLOCK")
        return resultado

    def analizar_condiciones(self, deteccion, poseedores, esperas, info_recursos):
        procesos = deteccion["procesos"]
        recursos = deteccion["recursos"]

        exclusivos = [r for r in recursos
                      if info_recursos[r]["libres"] == 0 and info_recursos[r]["instancias"] >= 1]
        c1 = len(exclusivos) > 0

        retienen = []
        for pid in procesos:
            tiene = any(pid in duenos for duenos in poseedores.values())
            espera = esperas.get(pid) is not None
            if tiene and espera:
                retienen.append(pid)
        c2 = len(retienen) == len(procesos) and len(procesos) > 0

        no_expropiables = [r for r in recursos if not info_recursos[r]["expropiable"]]
        c3 = len(no_expropiables) == len(recursos) and len(recursos) > 0

        c4 = True

        condiciones = {
            "Exclusion mutua": {
                "presente": c1,
                "porque": (f"Los recursos {exclusivos} no tienen instancias libres y solo "
                           f"pueden usarse por un proceso a la vez."
                           if c1 else "Ningun recurso del ciclo es de uso exclusivo.")
            },
            "Retencion y espera": {
                "presente": c2,
                "porque": (f"Los procesos {retienen} conservan recursos mientras piden otro."
                           if c2 else "No todos los procesos del ciclo retienen recursos mientras esperan.")
            },
            "No expropiacion": {
                "presente": c3,
                "porque": (f"Los recursos {no_expropiables} estan marcados como no expropiables: "
                           f"solo se liberan cuando el dueno los suelta."
                           if c3 else "Al menos un recurso del ciclo si es expropiable.")
            },
            "Espera circular": {
                "presente": c4,
                "porque": "El detector encontro el ciclo: " + " -> ".join(deteccion["ciclo"])
            },
        }

        for nombre, datos in condiciones.items():
            marca = "SI" if datos["presente"] else "NO"
            bitacora.registrar(f"Condicion '{nombre}': {marca}. {datos['porque']}", "DEADLOCK")

        return condiciones

# Administrador de dispositivos y recursos compartidos.

import bitacora


class Recurso:
    def __init__(self, id_recurso, tipo, instancias, expropiable):
        self.id = id_recurso
        self.tipo = tipo
        self.instancias = instancias
        self.expropiable = expropiable
        self.poseedores = []

    def libres(self):
        return self.instancias - len(self.poseedores)

    def ocupado(self):
        return self.libres() == 0


class GestorRecursos:
    def __init__(self, definiciones):
        self.recursos = {}
        for d in definiciones:
            self.recursos[d["id"]] = Recurso(
                d["id"],
                d.get("tipo", "generico"),
                d.get("instancias", 1),
                d.get("expropiable", False),
            )
        self.total_solicitudes = 0
        self.total_esperas = 0

    def existe(self, id_recurso):
        return id_recurso in self.recursos

    def solicitar(self, proceso, id_recurso):
        recurso = self.recursos[id_recurso]
        self.total_solicitudes += 1

        bitacora.registrar_syscall(
            proceso.pid, f"solicitar el recurso '{id_recurso}'",
            "ioctl() / open() sobre un dispositivo",
            "Aplicacion -> Shell -> Kernel (driver) -> Hardware")

        if proceso.pid in recurso.poseedores:
            bitacora.registrar(f"{proceso.pid} ya tenia '{id_recurso}', no se le asigna otra vez.", "RECURSO")
            return True

        if recurso.libres() > 0:
            recurso.poseedores.append(proceso.pid)
            proceso.recursos.append(id_recurso)
            bitacora.registrar(
                f"Se asigno el recurso '{id_recurso}' a {proceso.pid}. "
                f"Instancias libres: {recurso.libres()}/{recurso.instancias}.", "RECURSO")
            return True

        self.total_esperas += 1
        bitacora.registrar(
            f"El recurso '{id_recurso}' esta ocupado por {recurso.poseedores}. "
            f"{proceso.pid} pasa a ESPERANDO.", "RECURSO")
        return False

    def liberar(self, proceso, id_recurso):
        recurso = self.recursos[id_recurso]
        if proceso.pid not in recurso.poseedores:
            bitacora.registrar(
                f"{proceso.pid} intento liberar '{id_recurso}' pero no lo tenia.", "ERROR")
            return False

        bitacora.registrar_syscall(
            proceso.pid, f"liberar el recurso '{id_recurso}'", "close() / release()",
            "Aplicacion -> Kernel (driver) -> Hardware")

        recurso.poseedores.remove(proceso.pid)
        if id_recurso in proceso.recursos:
            proceso.recursos.remove(id_recurso)
        bitacora.registrar(
            f"{proceso.pid} libero el recurso '{id_recurso}'. "
            f"Instancias libres: {recurso.libres()}/{recurso.instancias}.", "RECURSO")
        return True

    def liberar_todo(self, proceso):
        liberados = []
        for id_recurso in list(proceso.recursos):
            if id_recurso in self.recursos:
                self.liberar(proceso, id_recurso)
                liberados.append(id_recurso)
        return liberados

    def libres(self):
        return [r.id for r in self.recursos.values() if r.libres() > 0]

    def ocupados(self):
        return [r.id for r in self.recursos.values() if len(r.poseedores) > 0]

    def tabla(self):
        lineas = []
        for r in self.recursos.values():
            duenos = ", ".join(r.poseedores) if r.poseedores else "libre"
            lineas.append(f"  {r.id:<15} tipo={r.tipo:<12} "
                          f"{len(r.poseedores)}/{r.instancias} en uso  -> {duenos}")
        return "\n".join(lineas)

# Administrador de memoria.

import bitacora


class GestorMemoria:
    def __init__(self, memoria_total):
        self.total = memoria_total
        self.usada = 0
        self.pico = 0
        self.asignada = {}

    def disponible(self):
        return self.total - self.usada

    def solicitar(self, proceso, cantidad):
        bitacora.registrar_syscall(
            proceso.pid, "solicitar memoria", "malloc() / brk()",
            "Aplicacion -> Shell -> Kernel -> Hardware (RAM)")

        if cantidad > self.total:
            bitacora.registrar(
                f"{proceso.pid} pidio {cantidad} MB pero la maquina simulada solo "
                f"tiene {self.total} MB en total: nunca podra ejecutarse.", "ERROR")
            return False

        if cantidad > self.disponible():
            bitacora.registrar(
                f"{proceso.pid} pidio {cantidad} MB y solo hay {self.disponible()} MB "
                f"libres: se queda esperando memoria.", "MEMORIA")
            return False

        self.usada += cantidad
        self.asignada[proceso.pid] = self.asignada.get(proceso.pid, 0) + cantidad
        proceso.memoria_asignada += cantidad
        if self.usada > self.pico:
            self.pico = self.usada

        bitacora.registrar(
            f"Se asignaron {cantidad} MB a {proceso.pid}. "
            f"Usada: {self.usada}/{self.total} MB, libre: {self.disponible()} MB.", "MEMORIA")
        return True

    def liberar(self, proceso):
        cantidad = self.asignada.pop(proceso.pid, 0)
        if cantidad == 0:
            return 0

        bitacora.registrar_syscall(
            proceso.pid, "liberar memoria", "free() / exit()",
            "Aplicacion -> Kernel -> Hardware (RAM)")

        self.usada -= cantidad
        proceso.memoria_asignada = 0
        bitacora.registrar(
            f"Se liberaron {cantidad} MB de {proceso.pid}. "
            f"Usada: {self.usada}/{self.total} MB, libre: {self.disponible()} MB.", "MEMORIA")
        return cantidad

    def estado(self):
        return (f"Memoria total: {self.total} MB | usada: {self.usada} MB | "
                f"disponible: {self.disponible()} MB | pico: {self.pico} MB")

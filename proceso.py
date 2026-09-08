# Proceso del simulador y sus estados.

LISTO = "listo"
ESPERANDO = "esperando"
BLOQUEADO = "bloqueado"
TERMINADO = "terminado"


class Proceso:
    def __init__(self, pid, nombre, memoria_requerida, acciones):
        self.pid = pid
        self.nombre = nombre
        self.memoria_requerida = memoria_requerida
        self.acciones = acciones
        self.indice = 0
        self.estado = LISTO
        self.memoria_asignada = 0
        self.recursos = []
        self.esperando = None
        self.pasos_trabajando = 0
        self.motivo_fin = ""

    def accion_actual(self):
        if self.indice < len(self.acciones):
            return self.acciones[self.indice]
        return None

    def avanzar(self):
        self.indice += 1

    def terminado(self):
        return self.estado == TERMINADO

    def resumen(self):
        recursos = ", ".join(self.recursos) if self.recursos else "-"
        espera = self.esperando["id"] if self.esperando else "-"
        return (f"{self.pid:<5} {self.nombre:<18} {self.estado:<10} "
                f"mem={self.memoria_asignada:<5} tiene=[{recursos}] espera={espera}")

    def __repr__(self):
        return f"<Proceso {self.pid} {self.estado}>"

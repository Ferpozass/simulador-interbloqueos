# Registro de eventos en archivo.

import os
import datetime

CARPETA_LOGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

_archivo = None
_mostrar_en_pantalla = False


def iniciar(nombre_escenario):
    global _archivo
    if not os.path.exists(CARPETA_LOGS):
        os.makedirs(CARPETA_LOGS)

    marca = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    limpio = "".join(c if c.isalnum() or c in "-_" else "_" for c in nombre_escenario)
    _archivo = os.path.join(CARPETA_LOGS, f"simulacion_{limpio}_{marca}.log")

    with open(_archivo, "w", encoding="utf-8") as f:
        f.write(f"SIMULACION: {nombre_escenario}\n")
        f.write(f"Fecha: {datetime.datetime.now():%d/%m/%Y %H:%M:%S}\n")
        f.write("=" * 70 + "\n")
    return _archivo


def registrar(mensaje, tipo="EVENTO"):
    if _archivo is None:
        return
    hora = datetime.datetime.now().strftime("%H:%M:%S")
    linea = f"[{hora}] [{tipo:<8}] {mensaje}"
    with open(_archivo, "a", encoding="utf-8") as f:
        f.write(linea + "\n")
    if _mostrar_en_pantalla:
        print("   " + linea)


def registrar_syscall(proceso, servicio, equivalente, capas):
    registrar(f"{proceso} solicita el servicio '{servicio}' "
              f"(equivale a {equivalente}) | recorrido: {capas}", tipo="SYSCALL")


def ruta_actual():
    return _archivo


def eco(activar):
    global _mostrar_en_pantalla
    _mostrar_en_pantalla = activar

# Monitoreo de la maquina real con psutil.

import psutil


def datos_reales():
    memoria = psutil.virtual_memory()
    disco = psutil.disk_usage("/")
    red = psutil.net_io_counters()

    return {
        "cpu_porcentaje": psutil.cpu_percent(interval=1),
        "cpu_nucleos": psutil.cpu_count(logical=True),
        "ram_total_gb": round(memoria.total / (1024 ** 3), 2),
        "ram_usada_gb": round(memoria.used / (1024 ** 3), 2),
        "ram_porcentaje": memoria.percent,
        "disco_total_gb": round(disco.total / (1024 ** 3), 2),
        "disco_usado_gb": round(disco.used / (1024 ** 3), 2),
        "disco_porcentaje": disco.percent,
        "red_enviado_mb": round(red.bytes_sent / (1024 ** 2), 2),
        "red_recibido_mb": round(red.bytes_recv / (1024 ** 2), 2),
    }


def mostrar(simulador=None):
    d = datos_reales()

    print()
    print("=" * 68)
    print("MONITOREO DEL SISTEMA (datos REALES obtenidos con psutil)")
    print("=" * 68)
    print("CPU en uso:        " + str(d["cpu_porcentaje"]) + " %  (" +
          str(d["cpu_nucleos"]) + " nucleos logicos)")
    print("Memoria RAM:       " + str(d["ram_usada_gb"]) + " GB usados de " +
          str(d["ram_total_gb"]) + " GB (" + str(d["ram_porcentaje"]) + " %)")
    print("Almacenamiento:    " + str(d["disco_usado_gb"]) + " GB usados de " +
          str(d["disco_total_gb"]) + " GB (" + str(d["disco_porcentaje"]) + " %)")
    print("Red:               " + str(d["red_enviado_mb"]) + " MB enviados / " +
          str(d["red_recibido_mb"]) + " MB recibidos")

    if simulador is not None:
        print()
        print("-" * 68)
        print("RECURSOS SIMULADOS (inventados por el escenario, no son reales)")
        print("-" * 68)
        print("Memoria del simulador:  " + str(simulador.memoria.usada) + " MB usados de " +
              str(simulador.memoria.total) + " MB")
        print("Recursos del escenario: " + str(list(simulador.recursos.recursos.keys())))
        print("Procesos del escenario: " + str([p.pid for p in simulador.procesos]))
        print()
        print("Los numeros de arriba son de la computadora fisica; los de abajo")
        print("existen solo dentro del programa. Son cosas distintas.")

    print("=" * 68)
    print()

# Menu CLI del simulador.

import os
import sys

import bitacora
import monitoreo
import visualizacion
from simulador import Simulador, cargar_escenario, ErrorEscenario

CARPETA_ESCENARIOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "escenarios")


def limpiar():
    os.system("cls" if os.name == "nt" else "clear")


def titulo():
    print("=" * 68)
    print("   SIMULADOR DE ADMINISTRACION DE RECURSOS E INTERBLOQUEOS")
    print("   Sistemas Operativos - UAQ")
    print("=" * 68)


def listar_escenarios():
    if not os.path.exists(CARPETA_ESCENARIOS):
        return []
    archivos = [a for a in os.listdir(CARPETA_ESCENARIOS) if a.endswith(".json")]
    archivos.sort()
    return archivos


def elegir_escenario():
    archivos = listar_escenarios()
    print()
    print("Escenarios disponibles en la carpeta 'escenarios':")
    if not archivos:
        print("  (no hay ninguno)")
    for i, a in enumerate(archivos, start=1):
        print("  " + str(i) + ") " + a)
    print("  R) Escribir la ruta de otro archivo JSON")
    print("  0) Cancelar")

    opcion = input("\nElige una opcion: ").strip()

    if opcion == "0":
        return None
    if opcion.upper() == "R":
        ruta = input("Ruta del archivo JSON: ").strip().strip('"')
        return ruta
    if opcion.isdigit() and 1 <= int(opcion) <= len(archivos):
        return os.path.join(CARPETA_ESCENARIOS, archivos[int(opcion) - 1])

    print("Opcion no valida.")
    return None


def cargar(sim_actual):
    ruta = elegir_escenario()
    if ruta is None:
        return sim_actual

    try:
        datos = cargar_escenario(ruta)
    except ErrorEscenario as e:
        print()
        print("!! No se pudo cargar el escenario.")
        print("   " + str(e))
        input("\nEnter para volver al menu...")
        return sim_actual

    sim = Simulador(datos)
    print()
    print("Escenario cargado: " + sim.nombre)
    if sim.descripcion:
        print("Descripcion: " + sim.descripcion)
    print("Procesos: " + str(len(sim.procesos)) +
          " | Memoria total: " + str(sim.memoria.total) + " MB" +
          " | Recursos: " + str(len(sim.recursos.recursos)))
    print("Bitacora de esta corrida: " + str(bitacora.ruta_actual()))
    input("\nEnter para continuar...")
    return sim


def modo_automatico(sim):
    print()
    print("MODO AUTOMATICO: se ejecuta el escenario completo.")
    print("-" * 68)
    eventos = sim.ejecutar_todo()
    for i, e in enumerate(eventos, start=1):
        print("  " + str(i).rjust(3) + ". " + e)
    print("-" * 68)
    print()
    print(sim.estado_texto())
    print()
    print(sim.metricas_texto())
    print("Bitacora: " + str(bitacora.ruta_actual()))
    input("\nEnter para volver al menu...")


def modo_paso_a_paso(sim):
    print()
    print("MODO PASO A PASO. Enter = siguiente evento | g = ver grafo | s = salir")
    print(sim.estado_texto())

    while not sim.terminada:
        tecla = input("\n> ").strip().lower()
        if tecla == "s":
            break
        if tecla == "g":
            ciclo = sim.historial_deadlocks[-1]["ciclo"] if sim.historial_deadlocks else None
            visualizacion.dibujar(sim, ciclo)
            continue

        evento = sim.paso()
        if evento is None:
            print("\nYa no quedan eventos por ejecutar.")
            break
        print("\n>> " + evento)
        print(sim.estado_texto())

    print()
    print(sim.metricas_texto())
    input("\nEnter para volver al menu...")


def analizar_interbloqueo(sim):
    print()
    print("ANALISIS DE INTERBLOQUEO (bajo demanda)")
    print("-" * 68)
    deteccion = sim.revisar_interbloqueo()

    if deteccion is None:
        print("No se encontro espera circular en este momento.")
        print("Los procesos que estan esperando lo hacen por recursos que")
        print("todavia pueden liberarse, asi que no hay interbloqueo.")
        input("\nEnter para volver al menu...")
        return

    print("SI HAY INTERBLOQUEO")
    print("Ciclo encontrado:      " + " -> ".join(deteccion["ciclo"]))
    print("Procesos involucrados: " + str(deteccion["procesos"]))
    print("Recursos involucrados: " + str(deteccion["recursos"]))
    print()
    print("Las cuatro condiciones:")
    for nombre, datos in deteccion["condiciones"].items():
        marca = "[SI]" if datos["presente"] else "[NO]"
        print("  " + marca + " " + nombre)
        print("        " + datos["porque"])

    print()
    if input("Quieres ver el grafo? (s/n): ").strip().lower() == "s":
        visualizacion.dibujar(sim, deteccion["ciclo"])

    print()
    if input("Aplicar la estrategia de recuperacion? (s/n): ").strip().lower() == "s":
        print()
        print(sim.resolver_interbloqueo(deteccion))
        print()
        print(sim.estado_texto())

    input("\nEnter para volver al menu...")


def ver_grafo(sim):
    ciclo = sim.historial_deadlocks[-1]["ciclo"] if sim.historial_deadlocks else None
    ruta = visualizacion.dibujar(sim, ciclo)
    if ruta is None:
        input("\nEnter para volver al menu...")
    else:
        input("\nEnter para volver al menu...")


def menu():
    sim = None

    while True:
        limpiar()
        titulo()
        if sim is None:
            print("Escenario cargado: (ninguno)")
        else:
            estado = "terminada" if sim.terminada else "en curso"
            print("Escenario cargado: " + sim.nombre + "  [" + estado + "]")
        print("-" * 68)
        print("  1) Cargar escenario")
        print("  2) Ejecutar en modo automatico")
        print("  3) Ejecutar en modo paso a paso")
        print("  4) Ver estado actual del sistema")
        print("  5) Analizar interbloqueo ahora")
        print("  6) Ver grafo de procesos y recursos")
        print("  7) Ver resultados y metricas")
        print("  8) Monitoreo real del equipo (psutil)")
        print("  9) Ver la bitacora de esta corrida")
        print("  0) Salir")
        print("-" * 68)

        opcion = input("Opcion: ").strip()

        if opcion == "1":
            sim = cargar(sim)
            continue

        if opcion == "8":
            monitoreo.mostrar(sim)
            input("Enter para volver al menu...")
            continue

        if opcion == "0":
            print("\nHasta luego.")
            sys.exit(0)

        if opcion in ("2", "3", "4", "5", "6", "7", "9") and sim is None:
            print("\nPrimero hay que cargar un escenario (opcion 1).")
            input("Enter para continuar...")
            continue

        if opcion == "2":
            modo_automatico(sim)
        elif opcion == "3":
            modo_paso_a_paso(sim)
        elif opcion == "4":
            print()
            print(sim.estado_texto())
            input("\nEnter para volver al menu...")
        elif opcion == "5":
            analizar_interbloqueo(sim)
        elif opcion == "6":
            ver_grafo(sim)
        elif opcion == "7":
            print()
            print(sim.metricas_texto())
            input("\nEnter para volver al menu...")
        elif opcion == "9":
            ruta = bitacora.ruta_actual()
            print()
            if ruta and os.path.exists(ruta):
                print("Archivo: " + ruta)
                print("-" * 68)
                with open(ruta, "r", encoding="utf-8") as f:
                    print(f.read())
            else:
                print("Todavia no hay bitacora.")
            input("\nEnter para volver al menu...")
        else:
            print("\nOpcion no valida.")
            input("Enter para continuar...")


if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        print("\n\nSimulacion interrumpida por el usuario.")
    except EOFError:
        print("\n\nSe acabo la entrada, se cierra el programa.")

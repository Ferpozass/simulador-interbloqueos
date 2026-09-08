# Motor del simulador: carga el escenario, lo ejecuta y aplica la estrategia.

import json
import os

import bitacora
from proceso import Proceso, LISTO, ESPERANDO, BLOQUEADO, TERMINADO
from memoria import GestorMemoria
from recursos import GestorRecursos
from archivos import GestorArchivos
from interbloqueo import Detector


class ErrorEscenario(Exception):
    pass


ACCIONES_VALIDAS = [
    "solicitar_memoria", "solicitar_recurso", "liberar_recurso", "trabajar",
    "crear_archivo", "escribir_archivo", "leer_archivo", "cerrar_archivo",
    "mover_archivo", "eliminar_archivo", "terminar",
]


def cargar_escenario(ruta):
    if not os.path.exists(ruta):
        raise ErrorEscenario("No se encontro el archivo '" + ruta + "'.")

    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except json.JSONDecodeError as e:
        raise ErrorEscenario("El archivo no es un JSON valido: " + str(e))

    for campo in ["nombre", "memoria_total", "procesos"]:
        if campo not in datos:
            raise ErrorEscenario("Al escenario le falta el campo obligatorio '" + campo + "'.")

    if not isinstance(datos["memoria_total"], int) or datos["memoria_total"] <= 0:
        raise ErrorEscenario("'memoria_total' debe ser un numero entero mayor que cero.")

    if not isinstance(datos["procesos"], list) or len(datos["procesos"]) == 0:
        raise ErrorEscenario("El escenario debe traer al menos un proceso.")

    ids_recursos = []
    for r in datos.get("recursos", []):
        if "id" not in r:
            raise ErrorEscenario("Todos los recursos necesitan un campo 'id'.")
        if r["id"] in ids_recursos:
            raise ErrorEscenario("El recurso '" + r["id"] + "' esta repetido.")
        if r.get("instancias", 1) < 1:
            raise ErrorEscenario("El recurso '" + r["id"] + "' debe tener al menos una instancia.")
        ids_recursos.append(r["id"])

    pids = []
    for p in datos["procesos"]:
        for campo in ["pid", "memoria", "acciones"]:
            if campo not in p:
                raise ErrorEscenario("Al proceso " + str(p.get("pid", "(sin pid)")) +
                                     " le falta el campo '" + campo + "'.")
        if p["pid"] in pids:
            raise ErrorEscenario("El PID '" + p["pid"] + "' esta repetido.")
        pids.append(p["pid"])

        if not isinstance(p["memoria"], int) or p["memoria"] < 0:
            raise ErrorEscenario("La memoria de " + p["pid"] +
                                 " debe ser un entero mayor o igual a cero.")
        if not isinstance(p["acciones"], list) or len(p["acciones"]) == 0:
            raise ErrorEscenario("El proceso " + p["pid"] + " no tiene acciones.")

        for a in p["acciones"]:
            tipo = a.get("tipo")
            if tipo not in ACCIONES_VALIDAS:
                raise ErrorEscenario("La accion '" + str(tipo) + "' de " + p["pid"] +
                                     " no existe. Validas: " + ", ".join(ACCIONES_VALIDAS))
            if tipo in ("solicitar_recurso", "liberar_recurso"):
                if a.get("recurso") not in ids_recursos:
                    raise ErrorEscenario(p["pid"] + " usa el recurso '" + str(a.get("recurso")) +
                                         "' que no esta definido en el escenario.")
            if tipo.endswith("_archivo") and "archivo" not in a:
                raise ErrorEscenario("La accion '" + tipo + "' de " + p["pid"] +
                                     " necesita el campo 'archivo'.")

    return datos


class Simulador:
    def __init__(self, datos):
        self.nombre = datos["nombre"]
        self.descripcion = datos.get("descripcion", "")
        self.resolver_automaticamente = datos.get("resolver_automaticamente", True)
        self.memoria = GestorMemoria(datos["memoria_total"])
        self.recursos = GestorRecursos(datos.get("recursos", []))
        self.archivos = GestorArchivos(datos.get("archivos", []))
        self.detector = Detector()

        self.procesos = []
        for p in datos["procesos"]:
            self.procesos.append(Proceso(p["pid"], p.get("nombre", p["pid"]),
                                         p["memoria"], p["acciones"]))

        self.turno = 0
        self.ultimo_evento = "(la simulacion aun no empieza)"
        self.terminada = False
        self.historial_deadlocks = []

        self.interbloqueos_detectados = 0
        self.interbloqueos_resueltos = 0
        self.recursos_en_interbloqueos = []
        self.recursos_liberados = []

        bitacora.iniciar(self.nombre)
        bitacora.registrar("Inicio de la simulacion '" + self.nombre + "'.", "INICIO")
        bitacora.registrar("Memoria total: " + str(self.memoria.total) + " MB. Procesos: " +
                           str(len(self.procesos)) + ". Recursos: " +
                           str(list(self.recursos.recursos.keys())) + ".", "INICIO")


    def activos(self):
        return [p for p in self.procesos if p.estado not in (TERMINADO, BLOQUEADO)]

    def por_estado(self, estado):
        return [p.pid for p in self.procesos if p.estado == estado]

    def paso(self):
        if self.terminada:
            return None

        if not self.activos():
            self.terminada = True
            bitacora.registrar("Fin de la simulacion: no quedan procesos por ejecutar.", "FIN")
            return None

        total = len(self.procesos)
        for i in range(total):
            indice = (self.turno + i) % total
            p = self.procesos[indice]
            if p.estado in (TERMINADO, BLOQUEADO):
                continue
            avanzo, evento = self.ejecutar_accion(p)
            if avanzo:
                self.turno = (indice + 1) % total
                self.ultimo_evento = evento
                return evento

        return self.revisar_bloqueo_general()

    def ejecutar_accion(self, p):
        accion = p.accion_actual()
        if accion is None:
            return self.terminar_proceso(p, "termino todas sus acciones")

        tipo = accion["tipo"]

        if tipo == "solicitar_memoria":
            cantidad = accion.get("cantidad", p.memoria_requerida)
            if self.memoria.solicitar(p, cantidad):
                p.estado = LISTO
                p.esperando = None
                p.avanzar()
                return True, p.pid + " obtuvo " + str(cantidad) + " MB de memoria"
            p.estado = ESPERANDO
            p.esperando = {"tipo": "memoria", "id": "memoria"}
            return False, p.pid + " espera memoria"

        if tipo == "solicitar_recurso":
            id_recurso = accion["recurso"]
            if self.recursos.solicitar(p, id_recurso):
                p.estado = LISTO
                p.esperando = None
                p.avanzar()
                return True, p.pid + " tomo el recurso '" + id_recurso + "'"
            p.estado = ESPERANDO
            p.esperando = {"tipo": "recurso", "id": id_recurso}
            return False, p.pid + " espera el recurso '" + id_recurso + "'"

        if tipo == "liberar_recurso":
            id_recurso = accion["recurso"]
            self.recursos.liberar(p, id_recurso)
            self.recursos_liberados.append(id_recurso + " (por " + p.pid + ")")
            self.despertar_esperando(id_recurso)
            p.avanzar()
            return True, p.pid + " libero el recurso '" + id_recurso + "'"

        if tipo == "trabajar":
            pasos = accion.get("pasos", 1)
            p.pasos_trabajando += 1
            bitacora.registrar(p.pid + " esta trabajando (" + str(p.pasos_trabajando) +
                               "/" + str(pasos) + ").", "CPU")
            hechos = p.pasos_trabajando
            if p.pasos_trabajando >= pasos:
                p.pasos_trabajando = 0
                p.avanzar()
            p.estado = LISTO
            return True, p.pid + " uso la CPU (" + str(hechos) + "/" + str(pasos) + ")"

        if tipo.endswith("_archivo"):
            return self.accion_de_archivo(p, accion, tipo)

        if tipo == "terminar":
            return self.terminar_proceso(p, "ejecuto la accion terminar")

        bitacora.registrar("Accion desconocida '" + tipo + "' en " + p.pid + ", se ignora.", "ERROR")
        p.avanzar()
        return True, p.pid + " tenia una accion desconocida y se salto"

    def accion_de_archivo(self, p, accion, tipo):
        nombre = accion["archivo"]
        etiqueta = "F:" + nombre

        if tipo == "crear_archivo":
            self.archivos.crear(p, nombre)
            p.avanzar()
            return True, p.pid + " creo el archivo '" + nombre + "'"

        if tipo == "cerrar_archivo":
            self.archivos.cerrar(p, nombre)
            self.recursos_liberados.append(nombre + " (por " + p.pid + ")")
            self.despertar_esperando(etiqueta)
            p.avanzar()
            return True, p.pid + " cerro el archivo '" + nombre + "'"

        if tipo == "escribir_archivo":
            ok = self.archivos.escribir(p, nombre)
        elif tipo == "leer_archivo":
            ok = self.archivos.leer(p, nombre)
        elif tipo == "mover_archivo":
            ok = self.archivos.mover(p, nombre, accion.get("destino", nombre + ".bak"))
        elif tipo == "eliminar_archivo":
            ok = self.archivos.eliminar(p, nombre)
        else:
            ok = True

        if ok:
            p.estado = LISTO
            p.esperando = None
            p.avanzar()
            return True, p.pid + " ejecuto '" + tipo + "' sobre '" + nombre + "'"

        p.estado = ESPERANDO
        p.esperando = {"tipo": "archivo", "id": etiqueta}
        return False, p.pid + " espera el archivo '" + nombre + "'"

    def terminar_proceso(self, p, motivo):
        bitacora.registrar_syscall(p.pid, "terminar el proceso", "exit()",
                                   "Aplicacion -> Shell -> Kernel")
        liberados = self.recursos.liberar_todo(p)
        cerrados = self.archivos.liberar_todo(p)
        self.memoria.liberar(p)

        for r in liberados:
            self.recursos_liberados.append(r + " (por " + p.pid + ")")
            self.despertar_esperando(r)
        for a in cerrados:
            self.recursos_liberados.append(a + " (por " + p.pid + ")")
            self.despertar_esperando("F:" + a)

        p.estado = TERMINADO
        p.esperando = None
        p.motivo_fin = motivo
        bitacora.registrar(p.pid + " TERMINO (" + motivo + ").", "PROCESO")
        return True, p.pid + " termino"

    def despertar_esperando(self, id_recurso):
        for p in self.procesos:
            if p.estado == ESPERANDO and p.esperando and p.esperando["id"] == id_recurso:
                p.estado = LISTO
                p.esperando = None
                bitacora.registrar(p.pid + " vuelve a LISTO porque se libero '" +
                                   id_recurso + "'.", "PROCESO")


    def foto_del_sistema(self):
        poseedores = {}
        info = {}

        for r in self.recursos.recursos.values():
            poseedores[r.id] = list(r.poseedores)
            info[r.id] = {"instancias": r.instancias, "libres": r.libres(),
                          "expropiable": r.expropiable, "tipo": r.tipo}

        for a in self.archivos.archivos.values():
            etiqueta = "F:" + a.nombre
            poseedores[etiqueta] = [a.en_uso_por] if a.en_uso_por else []
            info[etiqueta] = {"instancias": 1,
                              "libres": 0 if a.en_uso_por else 1,
                              "expropiable": False, "tipo": "archivo"}

        esperas = {}
        for p in self.procesos:
            if p.estado in (ESPERANDO, BLOQUEADO) and p.esperando \
                    and p.esperando["tipo"] != "memoria":
                esperas[p.pid] = p.esperando["id"]

        return poseedores, esperas, info

    def revisar_interbloqueo(self):
        poseedores, esperas, info = self.foto_del_sistema()
        deteccion = self.detector.detectar(poseedores, esperas, info)
        if deteccion is None:
            return None

        deteccion["condiciones"] = self.detector.analizar_condiciones(
            deteccion, poseedores, esperas, info)

        if self.historial_deadlocks:
            ultimo = self.historial_deadlocks[-1]
            if not ultimo["resuelto"] and set(ultimo["ciclo"]) == set(deteccion["ciclo"]):
                return ultimo

        deteccion["resuelto"] = False
        self.interbloqueos_detectados += 1
        for r in deteccion["recursos"]:
            if r not in self.recursos_en_interbloqueos:
                self.recursos_en_interbloqueos.append(r)
        self.historial_deadlocks.append(deteccion)
        return deteccion

    def resolver_interbloqueo(self, deteccion):
        candidatos = [p for p in self.procesos if p.pid in deteccion["procesos"]]
        if not candidatos:
            return "No se pudo elegir una victima."

        victima = min(candidatos, key=lambda p: (len(p.recursos), p.memoria_asignada))

        bitacora.registrar(
            "ESTRATEGIA APLICADA: terminacion de victima. Se elige a " + victima.pid +
            " porque retiene " + str(len(victima.recursos)) + " recurso(s) y " +
            str(victima.memoria_asignada) + " MB, que es lo menos entre " +
            str([p.pid for p in candidatos]) + ".", "ESTRATEGIA")

        self.terminar_proceso(victima, "fue terminado por el SO para romper el interbloqueo")

        for p in candidatos:
            if p is not victima and p.estado == ESPERANDO:
                p.estado = LISTO
                p.esperando = None

        deteccion["resuelto"] = True
        self.interbloqueos_resueltos += 1
        bitacora.registrar("Se rompio la espera circular. La simulacion continua.", "ESTRATEGIA")
        return ("Interbloqueo resuelto: se termino a " + victima.pid +
                " y se liberaron sus recursos para romper el ciclo")

    def revisar_bloqueo_general(self):
        deteccion = self.revisar_interbloqueo()
        if deteccion and self.resolver_automaticamente:
            evento = self.resolver_interbloqueo(deteccion)
            self.ultimo_evento = evento
            return evento

        if deteccion:
            bitacora.registrar(
                "El escenario pidio NO resolver automaticamente: los procesos del "
                "ciclo se quedan bloqueados para poder observar el interbloqueo.",
                "DEADLOCK")

        atorados = [p for p in self.procesos if p.estado == ESPERANDO]
        for p in atorados:
            p.estado = BLOQUEADO
            bitacora.registrar(p.pid + " pasa a BLOQUEADO: espera '" +
                               str(p.esperando["id"]) + "' y nadie lo va a liberar.", "PROCESO")
        self.terminada = True
        bitacora.registrar("Fin de la simulacion: ya nadie puede avanzar.", "FIN")
        self.ultimo_evento = ("Procesos bloqueados definitivamente: " +
                              str([p.pid for p in atorados]))
        return self.ultimo_evento

    def ejecutar_todo(self, limite=500):
        eventos = []
        while not self.terminada and len(eventos) < limite:
            evento = self.paso()
            if evento is None:
                break
            eventos.append(evento)
        if len(eventos) >= limite:
            bitacora.registrar("Se alcanzo el limite de " + str(limite) +
                               " eventos, se detiene.", "FIN")
        return eventos


    def estado_texto(self):
        lineas = []
        lineas.append("-" * 68)
        lineas.append("Ultimo evento: " + str(self.ultimo_evento))
        lineas.append("")
        lineas.append("Listos:      " + str(self.por_estado(LISTO) or "-"))
        lineas.append("Esperando:   " + str(self.por_estado(ESPERANDO) or "-"))
        lineas.append("Bloqueados:  " + str(self.por_estado(BLOQUEADO) or "-"))
        lineas.append("Terminados:  " + str(self.por_estado(TERMINADO) or "-"))
        lineas.append("")
        lineas.append(self.memoria.estado())
        lineas.append("")
        lineas.append("Recursos:")
        lineas.append(self.recursos.tabla() or "  (sin recursos)")
        lineas.append("  Libres:   " + str(self.recursos.libres() or "-"))
        lineas.append("  Ocupados: " + str(self.recursos.ocupados() or "-"))
        lineas.append("")
        lineas.append("Archivos:")
        lineas.append(self.archivos.tabla())
        en_uso = self.archivos.en_uso()
        lineas.append("  En uso: " + str(en_uso if en_uso else "-"))
        lineas.append("")
        lineas.append("Detalle de procesos:")
        for p in self.procesos:
            lineas.append("  " + p.resumen())
        lineas.append("-" * 68)
        return "\n".join(lineas)

    def metricas(self):
        terminados_ok = [p for p in self.procesos if p.estado == TERMINADO
                         and "romper el interbloqueo" not in p.motivo_fin]
        victimas = [p for p in self.procesos if "romper el interbloqueo" in p.motivo_fin]
        bloqueados = [p for p in self.procesos if p.estado == BLOQUEADO]
        return {
            "Numero total de procesos": len(self.procesos),
            "Procesos terminados correctamente": len(terminados_ok),
            "Procesos terminados por el SO (victimas)": len(victimas),
            "Procesos que quedaron bloqueados": len(bloqueados),
            "Uso maximo de memoria (MB)": self.memoria.pico,
            "Solicitudes de recursos": self.recursos.total_solicitudes,
            "Veces que un proceso tuvo que esperar": self.recursos.total_esperas,
            "Operaciones sobre archivos": self.archivos.operaciones,
            "Interbloqueos detectados": self.interbloqueos_detectados,
            "Interbloqueos resueltos o evitados": self.interbloqueos_resueltos,
            "Recursos que participaron en interbloqueos":
                self.recursos_en_interbloqueos or ["ninguno"],
            "Resumen de recursos liberados": self.recursos_liberados or ["ninguno"],
        }

    def metricas_texto(self):
        lineas = ["=" * 68, "RESULTADOS Y METRICAS DE LA SIMULACION", "=" * 68]
        for clave, valor in self.metricas().items():
            if isinstance(valor, list):
                lineas.append(clave + ":")
                for v in valor:
                    lineas.append("    - " + str(v))
            else:
                lineas.append(clave + ": " + str(valor))
        lineas.append("=" * 68)
        texto = "\n".join(lineas)
        bitacora.registrar("Metricas finales:\n" + texto, "FIN")
        return texto

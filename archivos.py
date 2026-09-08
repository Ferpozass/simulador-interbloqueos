# Administrador de archivos simulados.

import bitacora


class Archivo:
    def __init__(self, nombre, existe=True):
        self.nombre = nombre
        self.existe = existe
        self.en_uso_por = None
        self.lectores = []


class GestorArchivos:
    def __init__(self, definiciones):
        self.archivos = {}
        for d in definiciones:
            nombre = d["nombre"] if isinstance(d, dict) else d
            self.archivos[nombre] = Archivo(nombre)
        self.operaciones = 0

    def _obtener(self, nombre):
        return self.archivos.get(nombre)

    def crear(self, proceso, nombre):
        self.operaciones += 1
        bitacora.registrar_syscall(proceso.pid, f"crear el archivo '{nombre}'",
                                   "creat() / open(O_CREAT)",
                                   "Aplicacion -> Shell -> Kernel (sistema de archivos) -> Hardware (disco)")
        if nombre in self.archivos and self.archivos[nombre].existe:
            bitacora.registrar(f"{proceso.pid} quiso crear '{nombre}' pero ya existe.", "ERROR")
            return True
        self.archivos[nombre] = Archivo(nombre)
        bitacora.registrar(f"{proceso.pid} creo el archivo '{nombre}'.", "ARCHIVO")
        return True

    def escribir(self, proceso, nombre):
        self.operaciones += 1
        bitacora.registrar_syscall(proceso.pid, f"escribir en '{nombre}'", "write()",
                                   "Aplicacion -> Kernel (sistema de archivos) -> Hardware (disco)")
        archivo = self._obtener(nombre)
        if archivo is None or not archivo.existe:
            bitacora.registrar(f"{proceso.pid} intento escribir en '{nombre}' que no existe.", "ERROR")
            return True
        if archivo.en_uso_por not in (None, proceso.pid):
            bitacora.registrar(
                f"El archivo '{nombre}' lo tiene abierto {archivo.en_uso_por}. "
                f"{proceso.pid} pasa a ESPERANDO.", "ARCHIVO")
            return False

        archivo.en_uso_por = proceso.pid
        etiqueta = "F:" + nombre
        if etiqueta not in proceso.recursos:
            proceso.recursos.append(etiqueta)
        bitacora.registrar(f"{proceso.pid} escribio en '{nombre}' y lo mantiene abierto.", "ARCHIVO")
        return True

    def leer(self, proceso, nombre):
        self.operaciones += 1
        bitacora.registrar_syscall(proceso.pid, f"leer '{nombre}'", "read()",
                                   "Aplicacion -> Kernel (sistema de archivos) -> Hardware (disco)")
        archivo = self._obtener(nombre)
        if archivo is None or not archivo.existe:
            bitacora.registrar(f"{proceso.pid} intento leer '{nombre}' que no existe.", "ERROR")
            return True
        if archivo.en_uso_por not in (None, proceso.pid):
            bitacora.registrar(
                f"'{nombre}' esta abierto en escritura por {archivo.en_uso_por}. "
                f"{proceso.pid} pasa a ESPERANDO.", "ARCHIVO")
            return False
        bitacora.registrar(f"{proceso.pid} leyo el archivo '{nombre}'.", "ARCHIVO")
        return True

    def cerrar(self, proceso, nombre):
        self.operaciones += 1
        archivo = self._obtener(nombre)
        if archivo and archivo.en_uso_por == proceso.pid:
            bitacora.registrar_syscall(proceso.pid, f"cerrar '{nombre}'", "close()",
                                       "Aplicacion -> Kernel (sistema de archivos)")
            archivo.en_uso_por = None
            etiqueta = "F:" + nombre
            if etiqueta in proceso.recursos:
                proceso.recursos.remove(etiqueta)
            bitacora.registrar(f"{proceso.pid} cerro el archivo '{nombre}'.", "ARCHIVO")
        return True

    def mover(self, proceso, nombre, destino):
        self.operaciones += 1
        bitacora.registrar_syscall(proceso.pid, f"mover '{nombre}' a '{destino}'", "rename()",
                                   "Aplicacion -> Kernel (sistema de archivos) -> Hardware (disco)")
        archivo = self._obtener(nombre)
        if archivo is None or not archivo.existe:
            bitacora.registrar(f"{proceso.pid} intento mover '{nombre}' que no existe.", "ERROR")
            return True
        if archivo.en_uso_por not in (None, proceso.pid):
            bitacora.registrar(f"No se puede mover '{nombre}': lo usa {archivo.en_uso_por}. "
                               f"{proceso.pid} espera.", "ARCHIVO")
            return False
        del self.archivos[nombre]
        archivo.nombre = destino
        self.archivos[destino] = archivo
        bitacora.registrar(f"{proceso.pid} movio '{nombre}' a '{destino}'.", "ARCHIVO")
        return True

    def eliminar(self, proceso, nombre):
        self.operaciones += 1
        bitacora.registrar_syscall(proceso.pid, f"eliminar '{nombre}'", "unlink()",
                                   "Aplicacion -> Kernel (sistema de archivos) -> Hardware (disco)")
        archivo = self._obtener(nombre)
        if archivo is None or not archivo.existe:
            bitacora.registrar(f"{proceso.pid} intento eliminar '{nombre}' que no existe.", "ERROR")
            return True
        if archivo.en_uso_por not in (None, proceso.pid):
            bitacora.registrar(f"No se puede eliminar '{nombre}': lo usa {archivo.en_uso_por}. "
                               f"{proceso.pid} espera.", "ARCHIVO")
            return False
        archivo.existe = False
        archivo.en_uso_por = None
        bitacora.registrar(f"{proceso.pid} elimino el archivo '{nombre}'.", "ARCHIVO")
        return True

    def liberar_todo(self, proceso):
        cerrados = []
        for archivo in self.archivos.values():
            if archivo.en_uso_por == proceso.pid:
                archivo.en_uso_por = None
                etiqueta = "F:" + archivo.nombre
                if etiqueta in proceso.recursos:
                    proceso.recursos.remove(etiqueta)
                cerrados.append(archivo.nombre)
                bitacora.registrar(f"Se cerro '{archivo.nombre}' porque {proceso.pid} lo solto.", "ARCHIVO")
        return cerrados

    def en_uso(self):
        return {a.nombre: a.en_uso_por for a in self.archivos.values() if a.en_uso_por}

    def tabla(self):
        if not self.archivos:
            return "  (el escenario no definio archivos)"
        lineas = []
        for a in self.archivos.values():
            estado = "eliminado" if not a.existe else (f"abierto por {a.en_uso_por}" if a.en_uso_por else "disponible")
            lineas.append(f"  {a.nombre:<20} {estado}")
        return "\n".join(lineas)

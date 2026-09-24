# Simulador de Administración de Recursos e Interbloqueos

Proyecto parcial de **Sistemas Operativos** — UAQ
Docente: Guadalupe Hernández

**Equipo:**
- Pozas Gomez Fernando — expediente 333414
- Juan Pablo Bolaños Rivera — expediente 326570
- Julio Alberto Tecuapacho Velázquez — expediente 333364

---

## Qué hace

Simula cómo un sistema operativo administra memoria, archivos, dispositivos y
recursos compartidos entre varios procesos. Cuando los procesos se quedan
esperando recursos unos de otros, el programa detecta el interbloqueo por su
cuenta, revisa cuáles de las cuatro condiciones de Coffman se cumplen, lo dibuja
como grafo y aplica una estrategia de recuperación para que la simulación pueda
continuar.

## Cómo instalarloo

Se necesita Python 3.9 o más nuevo.

```
pip install -r requirements.txt
```

## Cómo ejecutarlo

Desde la carpeta del proyecto:

```
python main.py
```

Sale un menú:

```
  1) Cargar escenario
  2) Ejecutar en modo automático
  3) Ejecutar en modo paso a paso
  4) Ver estado actual del sistema
  5) Analizar interbloqueo ahora
  6) Ver grafo de procesos y recursos
  7) Ver resultados y métricas
  8) Monitoreo real del equipo (psutil)
  9) Ver la bitácora de esta corrida
  0) Salir
```

Lo primero siempre es la opción **1** para cargar un escenario. La opción 1
también permite escribir la ruta de un JSON que esté en cualquier otra carpeta,
que es como se carga un escenario externo sin tocar el código.

En el modo paso a paso: **Enter** avanza un evento, **g** dibuja el grafo y
**s** sale al menú.

## Los cinco escenarios

Están en `escenarios/` y todos los diseñó el equipo:

| Archivo | Qué demuestra |
|---|---|
| `escenario_1_normal.json` | Ejecución normal: nadie espera, los 3 procesos terminan |
| `escenario_2_espera_temporal.json` | Espera temporal: hay cola por la impresora y por memoria, pero los 4 terminan |
| `escenario_3_interbloqueo.json` | Interbloqueo de 2 procesos; el detector lo encuentra solo |
| `escenario_4_recuperacion.json` | Interbloqueo + estrategia de recuperación aplicada |
| `escenario_5_amplio.json` | 7 procesos, 5 recursos, ciclo de 3 y procesos trabajando en paralelo |

El escenario 3 trae `"resolver_automaticamente": false` para que el interbloqueo
se pueda ver tal cual, sin que el programa lo arregle de inmediato. Los demás
usan el valor por defecto (`true`).

## Formato de un escenario

```json
{
  "nombre": "Nombre del escenario",
  "descripcion": "Para qué sirve",
  "resolver_automaticamente": true,
  "memoria_total": 1024,
  "recursos": [
    { "id": "impresora_laser", "tipo": "dispositivo", "instancias": 1, "expropiable": false }
  ],
  "archivos": [ { "nombre": "reporte.pdf" } ],
  "procesos": [
    {
      "pid": "P-EJEMPLO",
      "nombre": "Descripción del proceso",
      "memoria": 200,
      "acciones": [
        { "tipo": "solicitar_memoria" },
        { "tipo": "solicitar_recurso", "recurso": "impresora_laser" },
        { "tipo": "trabajar", "pasos": 2 },
        { "tipo": "liberar_recurso", "recurso": "impresora_laser" },
        { "tipo": "terminar" }
      ]
    }
  ]
}
```

Acciones que entiende el simulador:

| Acción | Campos extra | Qué hace |
|---|---|---|
| `solicitar_memoria` | `cantidad` (opcional) | Pide memoria; si no hay, espera |
| `solicitar_recurso` | `recurso` | Pide un dispositivo o recurso; si está ocupado, espera |
| `liberar_recurso` | `recurso` | Lo suelta y despierta a quien lo esperaba |
| `trabajar` | `pasos` | Consume turnos de CPU |
| `crear_archivo` | `archivo` | Crea un archivo simulado |
| `escribir_archivo` | `archivo` | Lo abre en exclusiva y escribe |
| `leer_archivo` | `archivo` | Lo lee (varios pueden leer a la vez) |
| `cerrar_archivo` | `archivo` | Lo suelta |
| `mover_archivo` | `archivo`, `destino` | Lo renombra |
| `eliminar_archivo` | `archivo` | Lo borra |
| `terminar` | — | Termina y libera todo |

Si el JSON trae un error (falta un campo, un recurso que no existe, memoria
negativa, un PID repetido, una acción inventada), el programa lo dice con un
mensaje claro y no se cae.

## Carpetas que genera

- `logs/` — una bitácora por cada simulación, con todos los eventos y las
  llamadas al sistema marcadas como `[SYSCALL]`.
- `graficas/` — los PNG del grafo de asignación de recursos.

## Archivos del proyecto

| Archivo | Responsabilidad |
|---|---|
| `main.py` | Menú CLI |
| `proceso.py` | Clase Proceso y sus estados |
| `memoria.py` | Asignar y liberar memoria, métricas de uso |
| `archivos.py` | Archivos simulados y su bloqueo |
| `recursos.py` | Dispositivos y recursos compartidos |
| `interbloqueo.py` | Grafo, búsqueda de ciclos y las cuatro condiciones |
| `simulador.py` | Motor: carga, valida, ejecuta y aplica la estrategia |
| `monitoreo.py` | Datos reales de la máquina con psutil |
| `visualizacion.py` | Dibujo del grafo con NetworkX y Matplotlib |
| `bitacora.py` | Registro de eventos en archivo |

## Nota sobre el monitoreo

La opción 8 del menú muestra CPU, RAM, disco y red **reales** de la computadora,
leídos con psutil. Esos números no tienen nada que ver con la memoria y los
recursos del simulador, que son inventados por el escenario. La pantalla los
muestra en dos bloques separados justamente para que no se confundan.

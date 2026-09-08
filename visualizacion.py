# Grafo de asignacion de recursos con NetworkX y Matplotlib.

import os
import datetime

import matplotlib
matplotlib.use("Agg")          # para poder guardar la imagen sin abrir ventana
import matplotlib.pyplot as plt
import networkx as nx

CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graficas")


def dibujar(simulador, ciclo=None, mostrar=True):
    poseedores, esperas, info = simulador.foto_del_sistema()

    G = nx.DiGraph()
    nodos_proceso = []
    nodos_recurso = []

    for p in simulador.procesos:
        if p.estado == "terminado" and not p.recursos:
            continue
        G.add_node(p.pid)
        nodos_proceso.append(p.pid)

    for id_recurso, datos in info.items():
        usado = len(poseedores.get(id_recurso, [])) > 0
        esperado = id_recurso in esperas.values()
        if usado or esperado:
            G.add_node(id_recurso)
            nodos_recurso.append(id_recurso)

    aristas_asignacion = []
    aristas_espera = []

    for id_recurso, duenos in poseedores.items():
        for pid in duenos:
            if id_recurso in G and pid in G:
                G.add_edge(id_recurso, pid)
                aristas_asignacion.append((id_recurso, pid))

    for pid, id_recurso in esperas.items():
        if id_recurso in G and pid in G:
            G.add_edge(pid, id_recurso)
            aristas_espera.append((pid, id_recurso))

    if len(G) == 0:
        print("No hay nada que dibujar todavia: ningun proceso tiene o espera recursos.")
        return None

    aristas_ciclo = []
    if ciclo:
        for i in range(len(ciclo) - 1):
            origen, destino = ciclo[i], ciclo[i + 1]
            if origen in G and destino in G and G.has_edge(origen, destino):
                aristas_ciclo.append((origen, destino))

    posiciones = nx.spring_layout(G, seed=42, k=1.2)

    plt.figure(figsize=(9, 6))
    plt.title("Grafo de asignacion de recursos - " + simulador.nombre)

    nx.draw_networkx_nodes(G, posiciones, nodelist=nodos_proceso,
                           node_color="#8ecae6", node_shape="o", node_size=1800)
    nx.draw_networkx_nodes(G, posiciones, nodelist=nodos_recurso,
                           node_color="#ffb703", node_shape="s", node_size=2000)
    nx.draw_networkx_labels(G, posiciones, font_size=8)

    normales_asignacion = [a for a in aristas_asignacion if a not in aristas_ciclo]
    normales_espera = [a for a in aristas_espera if a not in aristas_ciclo]

    nx.draw_networkx_edges(G, posiciones, edgelist=normales_asignacion,
                           edge_color="#2a9d8f", width=2, arrowsize=22,
                           connectionstyle="arc3,rad=0.12", node_size=2000)
    nx.draw_networkx_edges(G, posiciones, edgelist=normales_espera,
                           edge_color="#6c757d", width=2, style="dashed", arrowsize=22,
                           connectionstyle="arc3,rad=0.12", node_size=2000)
    if aristas_ciclo:
        nx.draw_networkx_edges(G, posiciones, edgelist=aristas_ciclo,
                               edge_color="red", width=3, arrowsize=28,
                               connectionstyle="arc3,rad=0.12", node_size=2000)

    leyenda = ("Circulo azul = proceso   |   Cuadro amarillo = recurso\n"
               "Verde continuo: recurso asignado   |   Gris punteado: proceso esperando")
    if aristas_ciclo:
        leyenda += "\nROJO: espera circular (interbloqueo)"
    plt.figtext(0.5, 0.02, leyenda, ha="center", fontsize=8)

    plt.axis("off")
    plt.tight_layout()

    if not os.path.exists(CARPETA):
        os.makedirs(CARPETA)
    marca = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    limpio = "".join(c if c.isalnum() or c in "-_" else "_" for c in simulador.nombre)
    ruta = os.path.join(CARPETA, "grafo_" + limpio + "_" + marca + ".png")
    plt.savefig(ruta, dpi=110)
    plt.close()

    if mostrar:
        print("Grafo guardado en: " + ruta)
        try:
            os.startfile(ruta)
        except Exception:
            pass

    return ruta

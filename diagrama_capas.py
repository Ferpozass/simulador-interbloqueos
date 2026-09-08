# Genera el diagrama de las cuatro capas. Se ejecuta aparte: python diagrama_capas.py

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graficas")

CAPAS = [
    ("APLICACIONES", "#8ecae6",
     "El proceso ALU-01 del escenario ejecuta la accion\n"
     "solicitar_recurso 'impresora_laser'"),
    ("SHELL", "#95d5b2",
     "El menu CLI de main.py recibe la orden del usuario\n"
     "y se la pasa al simulador"),
    ("KERNEL", "#ffb703",
     "GestorRecursos.solicitar() decide si hay instancia libre,\n"
     "la asigna o manda el proceso a ESPERANDO, y lo anota en la bitacora"),
    ("HARDWARE", "#e07a5f",
     "La impresora fisica (aqui simulada) es el dispositivo\n"
     "que finalmente queda ocupado"),
]


def generar():
    fig, ax = plt.subplots(figsize=(10, 6.5))

    alto = 1.0
    separacion = 0.45
    y = 0

    for nombre, color, texto in reversed(CAPAS):
        caja = FancyBboxPatch((0.5, y), 9, alto,
                              boxstyle="round,pad=0.02",
                              facecolor=color, edgecolor="#333333", linewidth=1.5)
        ax.add_patch(caja)
        ax.text(1.0, y + alto * 0.62, nombre, fontsize=13, fontweight="bold", va="center")
        ax.text(1.0, y + alto * 0.26, texto, fontsize=9, va="center")
        y += alto + separacion

    alto_total = len(CAPAS) * (alto + separacion) - separacion

    ax.add_patch(FancyArrowPatch((0.28, alto_total - 0.1), (0.28, 0.15),
                                 arrowstyle="-|>", mutation_scale=22,
                                 color="#c1121f", linewidth=2))
    ax.text(0.02, alto_total / 2, "solicitud", rotation=90, fontsize=9,
            color="#c1121f", va="center", fontweight="bold")

    ax.add_patch(FancyArrowPatch((9.72, 0.15), (9.72, alto_total - 0.1),
                                 arrowstyle="-|>", mutation_scale=22,
                                 color="#2a9d8f", linewidth=2))
    ax.text(9.9, alto_total / 2, "respuesta", rotation=270, fontsize=9,
            color="#2a9d8f", va="center", fontweight="bold")

    ax.set_title("Recorrido de una solicitud por las cuatro capas\n"
                 "Ejemplo: ALU-01 pide la impresora laser", fontsize=13)
    ax.set_xlim(-0.3, 10.3)
    ax.set_ylim(-0.3, alto_total + 0.6)
    ax.axis("off")
    plt.tight_layout()

    if not os.path.exists(CARPETA):
        os.makedirs(CARPETA)
    ruta = os.path.join(CARPETA, "diagrama_capas.png")
    plt.savefig(ruta, dpi=130)
    plt.close()
    return ruta


if __name__ == "__main__":
    print("Diagrama guardado en: " + generar())

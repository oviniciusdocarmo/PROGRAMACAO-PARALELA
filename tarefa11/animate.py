import matplotlib
matplotlib.use("Agg")  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.animation import FuncAnimation  # noqa: E402
from mpl_toolkits.mplot3d import Axes3D  # noqa: E402, F401
import numpy as np  # noqa: E402

NX, NY = 64, 64
R = 0.1 * 0.1 / 1.0 ** 2  # nu*dt/dx^2 = 0.01

cx, cy = NX // 2, NY // 2
x, y = np.mgrid[0:NX, 0:NY]
u = 10.0 * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2.0 * 8 ** 2))

X, Y = np.meshgrid(range(NY), range(NX))
passo = [0]


def step(u):
    u_new = u.copy()
    u_new[1:-1, 1:-1] = u[1:-1, 1:-1] + R * (
        u[2:, 1:-1] + u[:-2, 1:-1] +
        u[1:-1, 2:] + u[1:-1, :-2] - 4 * u[1:-1, 1:-1]
    )
    return u_new


fig = plt.figure()
ax = fig.add_subplot(111, projection="3d")


def update(frame):
    global u
    for _ in range(10):
        u = step(u)
        passo[0] += 1
    ax.clear()
    ax.plot_surface(X, Y, u, cmap="viridis", vmin=0, vmax=10)
    ax.set_zlim(0, 10)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Velocidade")
    ax.set_title(f"Evolução da Difusão - Passo {passo[0]}")
    return []


ani = FuncAnimation(fig, update, frames=100, interval=50)
ani.save("tarefa11/diffusion.gif", writer="pillow", fps=24)
print("Salvo: tarefa11/diffusion.gif")

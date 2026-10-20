import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

d = pd.read_excel("dt_clients_confidence.xlsx")
v = d["New Height Comp (m)"]
groups = [("Lidar confident", "#2a78d6", d["Lidar Confident"]), ("Not lidar confident", "#eb6834", ~d["Lidar Confident"])]

print(v.describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).round(3))
print(d.groupby("Lidar Confident")["New Height Comp (m)"].describe().round(3))

plt.rcParams.update({"font.family": "Segoe UI", "axes.edgecolor": "#c3c2b7", "text.color": "#2b2b29", "xtick.color": "#6b6a63", "ytick.color": "#6b6a63"})
fig, ax = plt.subplots(figsize=(11, 5.5), facecolor="#fcfcfb")
ax.set_facecolor("#fcfcfb")
bins = np.arange(-1.175, 1.2, 0.05)
ax.hist([v[m] for _, _, m in groups], bins=bins, stacked=True, color=[c for _, c, _ in groups],
        label=[f"{n} (n={m.sum()}, median {v[m].median():+.2f} m)" for n, _, m in groups], edgecolor="#fcfcfb", linewidth=1.5)
ax.axvline(v.median(), color="#2b2b29", linewidth=1.5, linestyle="--")
ax.text(0.12, ax.get_ylim()[1] * 0.9, f"Overall median {v.median():+.2f} m\nMean {v.mean():+.2f} m  ·  IQR {v.quantile(.25):+.2f} to {v.quantile(.75):+.2f} m",
        va="top", fontsize=10, color="#2b2b29")
ax.set(xlabel="New Height Comp (m)", ylabel="Assets", xlim=(-1.2, 1.2))
ax.set_title(f"New Height Comp distribution — {len(v)} assets", loc="left", fontsize=14, fontweight="bold")
ax.grid(axis="y", color="#e8e7e1", linewidth=0.8)
ax.set_axisbelow(True)
for s in ["top", "right", "left"]:
    ax.spines[s].set_visible(False)
ax.legend(frameon=False, loc="upper left")
fig.tight_layout()
fig.savefig("height_comp_distribution.png", dpi=150)

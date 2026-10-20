import numpy as np
import pandas as pd

d = pd.read_excel("DYCE NORTH 004 Validation copy.xlsx", sheet_name="filt")
c = pd.read_csv("conf09-21.csv", usecols=["Asset Number", "Smallest Ground Plane 10"], low_memory=False)
c["Asset Number"] = pd.to_numeric(c["Asset Number"], errors="coerce")

m = d.merge(c, on="Asset Number", how="left")
m["LL vs GP10"] = (pd.to_numeric(m["Linesman Laser/RF + Height"], errors="coerce") - m["Smallest Ground Plane 10"]).round(2)

new, old = m["LL vs GP10"].abs(), m["LL vs GP"].round(2).abs()
m["GP10 vs GP"] = np.select([new < old, new > old, new == old], ["smaller", "bigger", "same"], default=None)

m.to_csv("dyce_gp10_comparison.csv", index=False)
print(m["GP10 vs GP"].value_counts(dropna=False))
print(pd.DataFrame({"LL vs GP": old, "LL vs GP10": new}).agg(["mean", "median"]).round(3))

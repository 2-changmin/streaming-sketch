import csv
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load(name):
    with open(f"results/{name}.csv") as f:
        return list(csv.DictReader(f))


# Bloom Filter: k 에 따른 FPR
rows = [r for r in load("bloom") if r["type"] == "bloom"]
plt.figure(figsize=(6.4, 4))
for i, b in enumerate([2, 4, 8, 12, 16]):
    sub = [r for r in rows if int(r["bits_per_elem"]) == b]
    ks = [int(r["k"]) for r in sub]
    plt.plot(ks, [float(r["fpr"]) for r in sub], "o-", color=f"C{i}", label=f"m/n = {b}")
    plt.plot(ks, [float(r["theory_fpr"]) for r in sub], "k--", lw=0.8)
plt.yscale("log")
plt.xlabel("number of hash functions k")
plt.ylabel("false positive rate")
plt.title("Bloom Filter (n = 500,000), dashed = theory")
plt.legend(fontsize=8)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("figures/bloom_fpr.png", dpi=200)
plt.close()

# Count-Min Sketch: width, depth 에 따른 평균 절대 오차
rows = [r for r in load("cms") if r["type"] == "cms"]
fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.8))
for d in [1, 2, 3, 4, 5, 8]:
    # 로그 축이라 오차가 0인 점은 그리지 않음
    sub = [r for r in rows if int(r["depth"]) == d and float(r["mae"]) > 0]
    ax[0].plot([int(r["width"]) for r in sub], [float(r["mae"]) for r in sub],
               "o-", label=f"d = {d}")
ax[0].set_xscale("log", base=2)
ax[0].set_yscale("log")
ax[0].set_xlabel("width w")
ax[0].set_ylabel("mean absolute error")
ax[0].set_title("CMS error vs width")
ax[0].legend(fontsize=8)
ax[0].grid(alpha=0.3)

# 카운터 총 개수를 8192개(32KB)로 고정했을 때
fixed = [r for r in rows if int(r["width"]) * int(r["depth"]) == 8192]
fixed.sort(key=lambda r: int(r["depth"]))
labels = [f'{r["width"]}x{r["depth"]}' for r in fixed]
ax[1].bar(labels, [float(r["mae"]) for r in fixed], color="C1")
ax[1].set_xlabel("w x d  (8,192 counters = 32 KB)")
ax[1].set_ylabel("mean absolute error")
ax[1].set_title("same memory, different shape")
ax[1].grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("figures/cms_error.png", dpi=200)
plt.close()

# HyperLogLog: p 에 따른 상대 오차
rows = [r for r in load("hll") if r["type"] == "hll" and r["target"] == "pair"]
by_p = defaultdict(list)
for r in rows:
    by_p[int(r["p"])].append(float(r["rel_err"]) * 100)
ps = sorted(by_p)
plt.figure(figsize=(6.4, 4))
for p in ps:
    plt.plot([p] * len(by_p[p]), by_p[p], "x", color="gray")
plt.plot(ps, [sum(by_p[p]) / len(by_p[p]) for p in ps], "o-", label="mean of 5 seeds")
plt.plot(ps, [104 / (2 ** p) ** 0.5 for p in ps], "k--", label="1.04 / sqrt(m)")
plt.yscale("log")
plt.xlabel("p  (m = 2^p registers)")
plt.ylabel("relative error (%)")
plt.title("HyperLogLog, distinct (user, movie) pairs")
plt.legend(fontsize=8)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("figures/hll_error.png", dpi=200)
plt.close()
print("figures saved")

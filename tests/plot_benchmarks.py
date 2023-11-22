# -*- coding: utf-8 -*-
import argparse
import json
import os
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.style as mstyle

mstyle.use("seaborn")


def main(fn):
    with open(os.path.join("benchmarks", fn), "r") as f:
        try:
            benchmarks = json.load(f)
        except json.decoder.JSONDecodeError:
            print("no benchmarks found (or JSONDecodeError)")
            return
    benchmarks = benchmarks["benchmarks"]
    res = defaultdict(list)
    for benchmark in benchmarks:
        name = benchmark["name"]
        if not name.startswith("test_neighbors_real_world_speed"):
            continue
        bits = benchmark["params"]["bits"]

        res[bits].append(
            {
                "name": benchmark["params"]["real_world_area"][0],
                "population": benchmark["extra_info"]["population_count"],
                "time_ms": benchmark["stats"]["mean"] * 1000,
            }
        )

    {k: v for k, v in sorted(res.items(), key=lambda x: x[0])}

    min_bits = min(res.keys())
    max_bits = max(res.keys())

    zorder = 10
    fig, ax = plt.subplots()
    for bits, values in res.items():
        values = sorted(values, key=lambda v: v["population"])
        names = [v["name"] for v in values]
        x = [v["population"] for v in values]
        y = [v["time_ms"] for v in values]
        ax.plot(x, y, label=f"{bits} bits", zorder=zorder)
        ax.scatter(x, y, marker="o", zorder=zorder)

        offset = 1.3
        halfway = len(names) // 2
        if bits == max_bits:
            for i in range(halfway):
                ax.annotate(
                    names[i],
                    (x[i], y[i] * offset),
                    rotation="vertical",
                    fontsize=8,
                    fontstyle="italic",
                    ha="center",
                )
        if bits == min_bits:
            for i in range(halfway, len(names)):
                ax.annotate(
                    names[i],
                    (x[i], y[i] * (1 / offset)),
                    rotation="vertical",
                    fontsize=8,
                    fontstyle="italic",
                    ha="center",
                    va="top",
                )
        zorder += 1

    ax.set_yscale("log")
    ax.set_xscale("log")

    ax.legend()
    ax.set_xlabel("population", fontsize=9)
    ax.set_ylabel("time (ms)", fontsize=9)

    ax.set_title(
        f"select {benchmark['extra_info']['n_neighbors']} agents within {benchmark['extra_info']['radius']} m for every 1000th agent",
        fontsize=10,
    )

    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, required=False)
    args = parser.parse_args()

    if args.file:
        main(args.file)
    else:
        from datetime import datetime

        folder = "benchmarks"
        files = os.listdir(folder)
        dates = [datetime.strptime(fn, "benchmark_%Y%m%d-%H%M%S.json") for fn in files]
        latest_fn = files[dates.index(max(dates))]
        main(latest_fn)

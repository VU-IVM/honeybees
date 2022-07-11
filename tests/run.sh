cd "$(dirname "$(realpath "$0")")";
mkdir -p benchmarks
pytest -s --plots plots --benchmark-json=benchmarks/benchmark.json --benchmark-warmup=on --benchmark-max-time=1000000000 --extended


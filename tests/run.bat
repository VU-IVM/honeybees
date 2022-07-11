echo off
cd /D "%~dp0"
if not exist "benchmarks" mkdir benchmarks

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /format:list') do set datetime=%%I
set datetime=%datetime:~0,8%-%datetime:~8,6%

@REM pytest -s -k test_neighbors_real_world_speed --plots plots --benchmark-json=benchmarks/benchmark_%datetime%.json --benchmark-warmup=on --benchmark-max-time=3600 --extended
pytest -s -k test_coords_to_pixels --plots plots --benchmark-json=benchmarks/benchmark_%datetime%.json --benchmark-warmup=on --benchmark-max-time=3600 --extended
@REM python plot_benchmarks.py --file benchmark_%datetime%.json
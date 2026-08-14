import argparse
from stackwise.reproduce import reproduce_smoke

parser = argparse.ArgumentParser()
parser.add_argument("--smoke", action="store_true", required=True)
parser.add_argument("--output", default="results/smoke")
args = parser.parse_args()
for name, path in reproduce_smoke(args.output).items():
    print(f"{name}: {path}")

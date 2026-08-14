import argparse
from stackwise.harmonize import harmonize_dataset

parser = argparse.ArgumentParser()
parser.add_argument("dataset_id")
parser.add_argument("--strict", action="store_true")
args = parser.parse_args()
path, warnings = harmonize_dataset(args.dataset_id, strict=args.strict)
print(path)
for warning in warnings:
    print("WARNING:", warning)

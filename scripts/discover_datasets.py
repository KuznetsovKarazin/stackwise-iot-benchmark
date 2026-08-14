import argparse

from stackwise.discovery import search_kaggle, search_zenodo, write_candidates

parser = argparse.ArgumentParser()
parser.add_argument("query")
parser.add_argument("--provider", choices=["zenodo", "kaggle", "both"], default="both")
parser.add_argument("--output", default="results/discovery/candidates.csv")
parser.add_argument("--size", type=int, default=25)
args = parser.parse_args()

candidates = []
if args.provider in {"zenodo", "both"}:
    candidates.extend(search_zenodo(args.query, size=args.size))
if args.provider in {"kaggle", "both"}:
    candidates.extend(search_kaggle(args.query))
print(write_candidates(candidates, args.output))

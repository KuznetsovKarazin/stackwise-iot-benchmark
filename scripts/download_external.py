import argparse
from stackwise.download import download_dataset
from stackwise.registry import DatasetRegistry

parser = argparse.ArgumentParser()
parser.add_argument("dataset_id")
parser.add_argument("--accept-license", action="store_true")
parser.add_argument("--accept-unverified-license", action="store_true")
args = parser.parse_args()
record = DatasetRegistry().get(args.dataset_id)
files = download_dataset(
    record,
    accept_license=args.accept_license,
    accept_unverified_license=args.accept_unverified_license,
)
print(f"Downloaded {len(files)} files")

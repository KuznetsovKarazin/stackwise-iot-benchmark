import argparse
from stackwise.io import read_table
from stackwise.models import fit_energy_model, save_energy_model

parser = argparse.ArgumentParser()
parser.add_argument("observations")
parser.add_argument("--output", default="results/models/energy")
args = parser.parse_args()
model = fit_energy_model(read_table(args.observations))
print(save_energy_model(model, args.output))

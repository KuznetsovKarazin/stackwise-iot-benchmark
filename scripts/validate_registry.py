from stackwise.registry import DatasetRegistry

registry = DatasetRegistry()
registry.validate()
print(f"Registry valid: {len(registry.records)} datasets")

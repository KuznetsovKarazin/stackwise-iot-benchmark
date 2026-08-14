from stackwise.audit import write_audit

for name, path in write_audit().items():
    print(f"{name}: {path}")

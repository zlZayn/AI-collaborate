def phase(tag, msg):
    print(f"  [{tag}] {msg}")


def task_done(name):
    print(f"  {name}  done")


def task_error(name, err):
    print(f"  {name}  ERROR: {err}")

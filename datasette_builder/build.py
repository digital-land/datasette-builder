import re
import subprocess


def run(command):
    proc = subprocess.run(command, capture_output=True, text=True)
    try:
        proc.check_returncode()  # raise exception on nonz-ero return code
    except subprocess.CalledProcessError as e:
        print(f"\n---- STDERR ----\n{proc.stderr}")
        print(f"\n---- STDIN ----\n{proc.stdout}")
        raise e

    return proc


parse_container_id = re.compile(r"^#[0-9]+ writing image ([^ ]*) done$", re.MULTILINE)
parse_name = re.compile(r"^#[0-9]+ naming to ([^ ]*) done", re.MULTILINE)


def package_datasets(datasets, tag=None):
    command = ["datasette", "package"]
    if tag:
        command.extend(["--tag", tag])
    command.extend(datasets)
    proc = run(command)
    container_id_match = parse_container_id.search(proc.stderr)
    name_match = parse_name.search(proc.stderr)
    return (container_id_match.group(1), name_match.group(1) if name_match else None)

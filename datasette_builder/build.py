import re
import subprocess


def run(command):
    proc = subprocess.run(command, capture_output=True, text=True)
    try:
        proc.check_returncode()  # raise exception on nonz-ero return code
    except subprocess.CalledProcessError as e:
        print(f"\n---- STDERR ----\n{proc.stderr}")
        print(f"\n---- STDOUT ----\n{proc.stdout}")
        raise e

    return proc


parse_container_id = re.compile(r"^#[0-9]+ writing image ([^ ]*) done$", re.MULTILINE)
parse_container_id_alternate = re.compile(r"^Successfully built ([^ ]*)$", re.MULTILINE)
parse_name = re.compile(r"^#[0-9]+ naming to ([^ ]*) done", re.MULTILINE)
parse_name_alternate = re.compile(r"Successfully tagged ([^ ]*)", re.MULTILINE)


def package_datasets(datasets, tag=None):
    command = ["datasette", "package"]
    if tag:
        command.extend(["--tag", tag])
    command.extend(datasets)
    print(f"executing command: {command}")
    proc = run(command)
    container_id_match = parse_container_id.search(proc.stderr)

    if container_id_match:
        name_match = parse_name.search(proc.stderr)
    else:
        container_id_match = parse_container_id_alternate.search(proc.stdout)
        name_match = parse_name_alternate.search(proc.stdout)

    if not container_id_match:
        print("----- STDOUT -----")
        print(proc.stdout)
        print("----- STDERR -----")
        print(proc.stderr)
        raise Exception("container_id not matched")

    return (container_id_match.group(1), name_match.group(1) if name_match else None)

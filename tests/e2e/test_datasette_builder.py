import os
import csv
import json

# import re

import sqlite3
import subprocess
import time
import uuid
from pathlib import Path


import pytest
import requests


@pytest.fixture
def sqlite3_db(tmp_path):
    "provides a test sqlite3 db"
    db_dir = tmp_path / "test_dir/"
    os.mkdir(db_dir)
    db_path =  db_dir / "test.sqlite3"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("CREATE TABLE e2e_test (id integer PRIMARY KEY, name TEXT)")
    c.execute("INSERT INTO e2e_test (name) VALUES ('entry-1')")
    conn.commit()
    conn.close()
    return db_path


 
def test_datasette_builder(sqlite3_db):
    uid = str(uuid.uuid4())[:8]
    base_tag = f"e2e-test-image-{uid}"
    docker_tag = f"{base_tag}_digital_land"
    proc_package = run(
        [
            "datasette_builder",
            "package",
            "--tag",
            base_tag,
            "--data-dir",
            str(sqlite3_db.parent)
        ]
    )

    assert proc_package.stderr == ""
    # assert re.match(r"^1 dataset successfully packaged", proc_package.stdout)

    proc_inspect = run(["docker", "inspect", docker_tag])
    image = json.loads(proc_inspect.stdout)
    assert image, f"docker image with tag {docker_tag} not found"

    run_name = f"e2e-test-{uid}"
    run(["docker", "run", "-d", "-p", "8081:5000", "--name", run_name, docker_tag])
    time.sleep(5)  # wait for docker to get going

    r = requests.get("http://0.0.0.0:8081/test.json?sql=select+*+from+e2e_test")
    assert r.json()["rows"] == [[1, "entry-1"]]

    run(["docker", "kill", run_name])
    time.sleep(2)

    run(["docker", "rm", run_name])
    time.sleep(2)

    run(["docker", "rmi", docker_tag])


def run(command, ignore_errors=False):
    proc = subprocess.run(command, capture_output=True, text=True)
    try:
        proc.check_returncode()  # raise exception on nonz-ero return code
    except subprocess.CalledProcessError as e:
        if not ignore_errors:
            print(f"\n---- STDERR ----\n{proc.stderr}")
            print(f"\n---- STDOUT ----\n{proc.stdout}")
            raise e
    return proc

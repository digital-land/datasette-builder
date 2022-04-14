#! /usr/bin/env python
import json
import os
import glob
import sys


def merge_inspect_files(data_dir):
    os.chdir(data_dir)
    files = glob.glob("*.json")
    lines = []
    for file in files:
        with open(file, "r") as f:
            lines.append(json.load(f))

    with open("inspect-data-all.json", "w") as out:
        data = {}
        for line in lines:
            for key, val in line.items():
                data[key] = val
        json.dump(data, out, indent=4)

    print("generated inspect-data-all.json in dir", path)

    for file in files:
        if os.path.isfile(file):
            os.remove(file)


if __name__ == '__main__':
    path = sys.argv[1]
    merge_inspect_files(path)

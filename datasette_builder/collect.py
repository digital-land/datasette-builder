from pathlib import Path

import requests


def collect_datasets(datasets, data_dir="./data"):
    for dataset in datasets:
        name = dataset["dataset"]
        path = Path(f"{data_dir}/{name}.sqlite3")
        if path.exists():
            print(f"skipping {name} as file already found at {path}")
            continue

        url = (
            dataset["url"]
            if dataset["url"]
            else f"https://github.com/digital-land/{name}-collection/raw/main/dataset/{name}.sqlite3"
        )

        r = requests.get(url, allow_redirects=True)
        path.open(mode="wb").write(r.content)
        print(f"{path} written successfully")

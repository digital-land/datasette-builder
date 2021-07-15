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
            else f"https://collection-dataset.s3.eu-west-2.amazonaws.com/{name}-collection/dataset/{name}.sqlite3"
        )

        r = requests.get(url, allow_redirects=True)
        path.open(mode="wb").write(r.content)
        print(f"{path} written successfully")

import csv
import sys
from pathlib import Path

import click

from .build import package_datasets
from .collect import collect_datasets


@click.group()
def cli():
    pass


@click.command()
@click.argument("config_path", type=click.Path(exists=True))
def collect(config_path):
    datasets = datasets_from_config(config_path)
    collect_datasets(datasets)


@click.command()
@click.argument("config_path", type=click.Path(exists=True))
@click.option("--tag", "-t", default="data")
@click.option("--data-dir", default="./data")
def package(config_path, tag, data_dir):
    datasets = [
        f"{data_dir}/{d['dataset']}.sqlite3" for d in datasets_from_config(config_path)
    ]
    for dataset in datasets:
        if not Path(dataset).exists():
            print(f"{dataset} not found")
            sys.exit(1)

    container_id, name = package_datasets(datasets, tag)
    click.echo("%s dataset successfully packaged" % len(datasets))
    click.echo(f"container_id: {container_id}")
    if name:
        click.echo(f"name: {name}")


def datasets_from_config(config_path):
    reader = csv.DictReader(open(config_path))
    return list(reader)


cli.add_command(package)
cli.add_command(collect)

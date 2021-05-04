import csv
import os
import sys
from pathlib import Path
import click

from .build import package_datasets
from .csv_dataset import sqlite_to_csv
from .collect import collect_datasets
from .github_api import GithubApi


@click.group()
def cli():
    pass


@click.command()
@click.argument("config_path", type=click.Path(exists=True))
def collect(config_path):
    datasets = datasets_from_config(config_path)
    collect_datasets(datasets)


@click.command()
@click.option("--tag", "-t", default="data")
@click.option("--data-dir", default="./data")
def package(tag, data_dir):
    datasets = [f"{d}" for d in Path(data_dir).glob("*.sqlite3")]
    for dataset in datasets:
        if not Path(dataset).exists():
            print(f"{dataset} not found")
            sys.exit(1)

    container_id, name = package_datasets(datasets, tag)
    click.echo("%s dataset successfully packaged" % len(datasets))
    click.echo(f"container_id: {container_id}")
    if name:
        click.echo(f"name: {name}")


@click.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.argument("output_path", type=click.Path())
def build_csv(input_path, output_path):
    sqlite_to_csv(input_path, output_path)
    click.echo("complete")


@click.command()
def scrape():
    github_token = os.environ.get("GITHUB_TOKEN", None)
    g = GithubApi(github_token, "digital-land")
    for dataset in g.find_datasets():
        click.echo(",".join([dataset["name"], dataset["url"]]))


def datasets_from_config(config_path):
    reader = csv.DictReader(open(config_path))
    return list(reader)


cli.add_command(collect)
cli.add_command(package)
cli.add_command(build_csv)
cli.add_command(scrape)

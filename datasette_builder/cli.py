import csv
import os
import sys
from pathlib import Path
import click
from collections import defaultdict
from datasette_builder.canned_query import generate_model_canned_queries
import json

from .build import package_datasets
from .csv_dataset import sqlite_to_csv
from .collect import collect_datasets
from .github_api import GithubApi
from .tiles import build_tiles_for_datasets


@click.group()
def cli():
    pass


@click.command()
@click.argument("config_path", type=click.Path(exists=True))
def collect(config_path):
    datasets = datasets_from_config(config_path)
    collect_datasets(datasets)


@click.command()
@click.argument(
    "metadata_path", type=click.Path(exists=True), default="./"
)
def build_view_queries(metadata_path):
    with open(Path(metadata_path) / "metadata.json", "r") as json_file:
        metadata = defaultdict(None, json.load(json_file))

    canned_queries = generate_model_canned_queries()
    metadata["databases"]["view_model"]["queries"].update(canned_queries)

    with open(Path(metadata_path) / "metadata_generated.json", "w") as json_file:
        json.dump(metadata, json_file, indent=4)


@click.command()
@click.option("--tag", "-t", default="data")
@click.option("--data-dir", default="./var/cache")
@click.option("--ext", default="sqlite3")
@click.option("--options", default=None)
def package(tag, data_dir, ext, options):
    datasets = [f"{d}" for d in Path(data_dir).rglob(f"*.{ext}")]
    for dataset in datasets:
        if not Path(dataset).exists():
            print(f"{dataset} not found")
            sys.exit(1)

    container_id, name = package_datasets(datasets, tag, options)
    click.echo("%s dataset successfully packaged" % len(datasets))
    click.echo(f"container_id: {container_id}")
    if name:
        click.echo(f"name: {name}")


@click.command()
@click.argument("view_model_path", type=click.Path(exists=True))
@click.argument("output_path", type=click.Path())
@click.argument("config_path", type=click.Path(exists=True), default="./datasets.csv")
def build_tiles(view_model_path, output_path, config_path):
    build_tiles_for_datasets(view_model_path, output_path)


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
cli.add_command(build_view_queries)
cli.add_command(build_tiles)

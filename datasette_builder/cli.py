import csv

import click

from .build import package_datasets


@click.group()
def cli():
    pass


@click.command()
@click.argument("config_path", type=click.Path(exists=True))
@click.option("--tag")
def package(config_path, tag):
    reader = csv.DictReader(open(config_path))
    datasets = [row["path"] for row in reader]
    container_id, name = package_datasets(datasets, tag)
    click.echo("%s dataset successfully packaged" % len(datasets))
    click.echo(f"container_id: {container_id}")
    if name:
        click.echo(f"name: {name}")


cli.add_command(package)

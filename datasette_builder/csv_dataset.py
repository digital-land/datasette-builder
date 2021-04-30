import csv

from digital_land.repository.entry_repository import EntryRepository
from digital_land.model.entity import Entity


def sqlite_to_csv(input_path, output_path):
    repo = EntryRepository(input_path)
    entities = repo.list_entities()
    output = csv.DictWriter(
        open(output_path, "w"),
        fieldnames=repo.list_attributes() | {"entry-date", "slug"},
    )
    output.writeheader()
    for entity in entities:
        output.writerow(Entity(repo.find_by_entity(entity), None).snapshot())

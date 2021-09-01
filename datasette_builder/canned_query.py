from view_builder.model.table import Base
from sqlalchemy.inspection import inspect

excluded_relationships = ["organisation", "metric"]


def generate_model_canned_queries(pagination=True):
    canned_queries = {}
    schema_models = (
        c
        for c in Base.__subclasses__()
        if hasattr(c, "dl_type") and c.dl_type == "schema"
    )
    for model in schema_models:
        canned_queries[f"get_{model.__tablename__}_id"] = generate_get_id_query(model)
        relationships = inspect(model).relationships
        related_classes = (rel.mapper.class_ for rel in relationships)
        join_query = "SELECT * FROM ("
        for related_class in related_classes:
            if any(
                True
                for rel in excluded_relationships
                if rel in related_class.__tablename__
            ):
                continue
            query = generate_join_query(model, related_class)
            if query:
                join_query += query + " UNION ALL "
        if join_query.endswith(" UNION ALL "):
            # Strip the last UNION ALL
            join_query = join_query[:-11]
            join_query += ")"
            if pagination:
                join_query += " WHERE gid > :gid ORDER BY gid"
            canned_queries[f"get_{model.__tablename__}_references"] = {
                "sql": join_query,
                "title": f"Get all references for {model.__tablename__}",
            }

    return canned_queries


def generate_get_id_query(model):
    sql_query = f"SELECT id{', type' if hasattr(model, 'type') else ''} FROM {model.__tablename__} WHERE {model.__tablename__}=:{model.__tablename__}"
    return {"sql": sql_query, "title": f"Get {model.__tablename__} id by reference"}


def generate_join_query(original_model, related_model):
    sql_query = ""
    # Two types of relationships - direct FK, or via an association table.
    if related_model.dl_type == "schema":
        # TODO
        pass
    if related_model.dl_type == "join":
        relationships = inspect(related_model).relationships
        related_schemas = [
            rel.mapper.class_
            for rel in relationships
            if rel.mapper.class_ is not original_model
        ]
        if len(related_schemas) != 1:
            raise Exception(
                "Expected join class {} to provide relationship for exactly two tables".format(
                    related_model
                )
            )
        related_table = related_schemas[0].__tablename__
        join_table = related_model.__tablename__
        original_table = original_model.__tablename__
        sql_query = (
            f"SELECT "
            f"{related_table}.id AS id, "
            f"{related_table}.{related_table} as reference, "
            f"{related_table}.name as name, "
            f"{related_table}.entity as entity, "
            f"'{related_table}' as type "
            f"FROM {related_table} "
            f"INNER JOIN {join_table} ON ({join_table}.{related_table}_id = {related_table}.id "
            f"AND {join_table}.{original_table}_id = :{original_table}) "
        )
    return sql_query

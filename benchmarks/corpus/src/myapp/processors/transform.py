"""EDS target: complex data transformation without documentation."""


def transform_dataset(records, schema, options):
    output = []
    for record in records:
        row = {}
        for field_name, field_def in schema.items():
            value = record.get(field_def.get("source", field_name))
            if value is None:
                if field_def.get("required"):
                    if options.get("strict"):
                        raise ValueError(f"Missing required: {field_name}")
                    else:
                        value = field_def.get("default", "")
                else:
                    value = field_def.get("default", None)
            if field_def.get("type") == "int":
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    if options.get("coerce"):
                        value = 0
                    else:
                        value = None
            elif field_def.get("type") == "float":
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    if options.get("coerce"):
                        value = 0.0
                    else:
                        value = None
            elif field_def.get("type") == "bool":
                if isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes")
                else:
                    value = bool(value)
            if field_def.get("transform") == "upper":
                if isinstance(value, str):
                    value = value.upper()
            elif field_def.get("transform") == "strip":
                if isinstance(value, str):
                    value = value.strip()
            if field_def.get("validate"):
                validator = field_def["validate"]
                if validator == "positive" and isinstance(value, (int, float)):
                    if value < 0:
                        value = abs(value)
                elif validator == "non_empty" and isinstance(value, str):
                    if not value:
                        value = field_def.get("default", "N/A")
            row[field_name] = value
        if options.get("filter_fn"):
            if not options["filter_fn"](row):
                continue
        output.append(row)
    if options.get("sort_by"):
        key = options["sort_by"]
        output.sort(key=lambda r: r.get(key, ""))
    if options.get("limit"):
        output = output[: options["limit"]]
    return output

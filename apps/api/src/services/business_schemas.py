"""Convert server-owned output schemas to the supported graph type subset."""

from copy import deepcopy


def obj(**properties):
    return {"type": "object", "properties": properties, "required": list(properties)}


STRING = {"type": "string"}
SOURCE = obj(title=STRING, raw_text=STRING, notes=STRING)
REPORT = obj(final_output=STRING)


def reference(node=None, path=()):
    return {
        "op": "ref",
        "ref": {
            "source": "node" if node else "input",
            **({"node_id": node} if node else {}),
            "path": list(path),
        },
    }


def graph_schema(schema, definitions=None):
    definitions = definitions or schema.get("$defs", {})
    if "$ref" in schema:
        return graph_schema(definitions[schema["$ref"].split("/")[-1]], definitions)
    if "anyOf" in schema:
        return {"type": [item["type"] for item in schema["anyOf"]]}
    # The graph type system is deliberately smaller than provider JSON Schema.
    # Registered semantic validators enforce constraints beyond this type subset.
    result = {
        key: deepcopy(value)
        for key, value in schema.items()
        if key in {"type", "required", "additionalProperties"}
    }
    if "properties" in schema:
        result["properties"] = {
            key: graph_schema(value, definitions) for key, value in schema["properties"].items()
        }
        # Provider strict schemas require every field, including nullable sources.
        # Existing business response schemas already follow this convention.
        result["required"] = list(result["properties"])
    if "items" in schema:
        result["items"] = graph_schema(schema["items"], definitions)
    return result

import os
import json
from jsonschema import validate

_PATH_TO_SCHEMA = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                               "../mm_pal/schema/response_schema.json")


def test_response_format():
    example_data = [{'result': "Success", "cmd": "foo(bar=42)", "data": 4},
                    {'result': "Error", "cmd": "foo(bar=42)", "data": 4},
                    {'result': "Timeout", "cmd": "foo(bar=42)"},
                    {'result': "Success", "cmd": ["foo(bar=42)",
                                                "anotherthing"], "data": 4},
                    {'result': "Success", "cmd": "foo(bar=42)", "data": 4,
                    "msg": "this is a debug message"},
                    {'result': "Success", "cmd": "foo(bar=42)", "data": 4,
                    "version": "0.0.0"}]

    with open(_PATH_TO_SCHEMA) as schema_f:
        schema = json.load(schema_f)
    for example_result in example_data:
        validate(example_result, schema)

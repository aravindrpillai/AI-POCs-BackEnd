import json
from ai import constants
from openai import OpenAI
from cv.llm.base import CVExtractor
from cv.schema import CVExtractResult
from cv.prompts.helper import PromptHelper

client = OpenAI(api_key=constants.OPENAI_API_KEY)


class OpenAIExtractor(CVExtractor):

    def extract(self, cv_text: str) -> dict:
        return self.extract_cv_json(cv_text)

        
    def make_schema_strict(self, schema):
        
        if isinstance(schema, list):
            return [self.make_schema_strict(x) for x in schema]

        if not isinstance(schema, dict):
            return schema

        # First, recurse into known composite keys
        for key in ("anyOf", "allOf", "oneOf"):
            if key in schema and isinstance(schema[key], list):
                schema[key] = [self.make_schema_strict(x) for x in schema[key]]

        # Recurse into definitions
        if "$defs" in schema and isinstance(schema["$defs"], dict):
            schema["$defs"] = {k: self.make_schema_strict(v) for k, v in schema["$defs"].items()}

        # Recurse into properties
        if "properties" in schema and isinstance(schema["properties"], dict):
            schema["properties"] = {k: self.make_schema_strict(v) for k, v in schema["properties"].items()}

        # Recurse into array items
        if "items" in schema:
            schema["items"] = self.make_schema_strict(schema["items"])

        # Handle object strictness
        if schema.get("type") == "object":
            schema["additionalProperties"] = False

            props = schema.get("properties", {})
            # OpenAI wants required explicitly (even if some fields are optional in your model)
            # In strict mode, "required" just means keys must be present (values can be null).
            if isinstance(props, dict):
                schema["required"] = list(props.keys())

        return schema


    def get_output_text(self, resp) -> str:
        ot = getattr(resp, "output_text", None)
        if isinstance(ot, str):
            return ot
        if callable(ot):
            return ot()

        out = ""
        for item in getattr(resp, "output", []) or []:
            if getattr(item, "type", None) == "message":
                for c in getattr(item, "content", []) or []:
                    if getattr(c, "type", None) in ("output_text", "text"):
                        out += getattr(c, "text", "") or ""
        return out


    def extract_cv_json(self, cv_text: str) -> dict:
        base_schema = CVExtractResult.model_json_schema()
        strict_schema = self.make_schema_strict(base_schema)

        resp = client.responses.create(
            model=constants.OPENAI_MODEL,
            instructions=PromptHelper.get("cv_summary.prompt", force_reload=True),
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": f"THIS IS A CV. Extract the requested fields.\n\nCV TEXT:\n{cv_text}"}
                    ],
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "cv_extract_result",
                    "schema": strict_schema,
                    "strict": True,
                }
            },
        )

        raw = self.get_output_text(resp)
        data = json.loads(raw)
        print("OPENAI---OP-START----")
        print(raw)
        print("OPENAI---OP-END-----")

        CVExtractResult(**data)
        return data

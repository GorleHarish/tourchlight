import re
import json

def _clean_and_parse_json(raw_str: str) -> dict:
    raw = (raw_str or "").strip()
    if not raw:
        return {}
        
    def _extract_dict(data):
        if isinstance(data, dict):
            return data
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            return data[0]
        return None
    
    try:
        data = json.loads(raw)
        extracted = _extract_dict(data)
        if extracted is not None:
            return extracted
    except Exception:
        pass

    try:
        fixed = re.sub(
            r'("(?:content|code|text|raw)")\s*:\s*"(.*?)"(?=\s*[,}\]])',
            lambda m: m.group(1) + ': ' + json.dumps(m.group(2)),
            raw,
            flags=re.DOTALL
        )
        data = json.loads(fixed)
        extracted = _extract_dict(data)
        if extracted is not None:
            return extracted
    except Exception:
        pass

    return {"error": "fallback"}

test_str1 = """[
  {
    "tool_name": "WRITE_FILE",
    "args": {
      "path": "test.txt",
      "content": "def foo():\n    pass\n"
    }
  }
]"""

res = _clean_and_parse_json(test_str1)
print(res)

test_str2 = """```json
[
  {
    "name": "READ_FILE",
    "arguments": {
      "path": "main.py"
    }
  }
]
```"""

json_array_match = re.search(r'(?:```(?:json)?\s*)?(\[\s*\{\s*["\'](?:tool_name|name|action|tool)["\'].*?\}\s*\])(?:\s*```)?', test_str2, re.DOTALL | re.IGNORECASE)
if json_array_match:
    print("Matched 2:", _clean_and_parse_json(json_array_match.group(1)))

test_str3 = """[{"name":"READ_FILE", "path":"main.py"}]"""
json_array_match = re.search(r'(?:```(?:json)?\s*)?(\[\s*\{\s*["\'](?:tool_name|name|action|tool)["\'].*?\}\s*\])(?:\s*```)?', test_str3, re.DOTALL | re.IGNORECASE)
if json_array_match:
    print("Matched 3:", _clean_and_parse_json(json_array_match.group(1)))


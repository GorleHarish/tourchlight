import urllib.request
import json
def trigger_load():
    req = urllib.request.Request(
        "http://127.0.0.1:1234/v1/chat/completions",
        data=json.dumps({
            "model": "any",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        response = urllib.request.urlopen(req, timeout=5)
        print("Success:", response.read().decode("utf-8"))
    except Exception as e:
        print("Error:", e)
trigger_load()

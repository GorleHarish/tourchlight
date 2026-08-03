import re

response = """
I will now generate the complete Snake game code as requested.

```javascript
/*
 * Classic Snake Game Implementation (Single File)
 * Requirements: Canvas API, Dark Theme, Keyboard Controls, Scoreboard, localStorage High Score.
 */
```
"""

bare_code_match = re.search(r"```(?:\w+)?\n(.*?)```", response, re.DOTALL | re.IGNORECASE)
if bare_code_match:
    content = bare_code_match.group(1).strip()
    print("Content matched")
    file_match = re.search(r"^(?:#|//|/\*|<!--)\s*(?:file|filename|filepath|path|class)\s*[:=]?\s*([^\n\r]+)", content, re.IGNORECASE)
    if file_match:
        print("File match inside block:", file_match.group(1))
    else:
        # Check immediately before the block
        pre_text = response[:bare_code_match.start()].strip()
        print("Pre-text:", pre_text)
        file_match_pre = re.search(r"(?:for|file|filename|filepath|path)\s*[:=]?\s*`?([\w\.\-/]+\.\w+)`?", pre_text, re.IGNORECASE)
        if file_match_pre:
            print("File match outside block:", file_match_pre.group(1))
        else:
            print("No file match found.")


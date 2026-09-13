
import re
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
html = re.sub(r'\s*<div class=\"major-logo-box\">.*?<div class=\"major-content\">', '\n\n            <div class=\"major-content\">', html, flags=re.DOTALL)
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)


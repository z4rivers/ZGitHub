#!/usr/bin/env python3
import re
from pathlib import Path
p = Path('hvac_cost_comparison.html')
s = p.read_text(encoding='utf-8', errors='ignore')
results = []
start = 0
while True:
    i = s.find('<script>', start)
    if i == -1: break
    j = s.find('</script>', i)
    if j == -1: break
    js = s[i+8:j]
    # strip strings and comments
    js2 = re.sub(r"/\*.*?\*/", '', js, flags=re.S)
    js2 = re.sub(r"//.*", '', js2)
    js2 = re.sub(r"'(?:\\.|[^'\\])*'", '""', js2)
    js2 = re.sub(r'"(?:\\.|[^"\\])*"', '""', js2)
    js2 = re.sub(r'`(?:\\.|[^`\\])*`', '""', js2)
    stack = []
    extra = None
    for k, ch in enumerate(js2):
        if ch in '{[(':
            stack.append((ch, k))
        elif ch in '}])':
            if not stack:
                extra = k
                break
            stack.pop()
    results.append({
        'block_start': i,
        'block_end': j,
        'unclosed': len(stack),
        'extra_closing_at': extra,
        'last_opener_at': stack[-1][1] if stack else None,
    })
    start = j + 9

for r in results:
    print(r)

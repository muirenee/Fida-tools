from pathlib import Path
p = Path('.fida-build/apply_0913.py')
s = p.read_text(encoding='utf-8')
old = "new, n = re.subn(pattern, replacement, text, count=1, flags=re.S)"
new = "new, n = re.subn(pattern, lambda m: replacement, text, count=1, flags=re.S)"
if old not in s:
    raise SystemExit('0.9.13 regex helper anchor not found')
p.write_text(s.replace(old, new, 1), encoding='utf-8')
print('0.9.13 regex replacement escaping fixed')

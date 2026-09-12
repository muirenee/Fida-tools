from pathlib import Path
import re

MAIN = Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
GRADLE = Path('fida-field/app/build.gradle')


def replace_once(path: Path, old: str, new: str):
    text = path.read_text()
    if old not in text:
        raise SystemExit(f'Expected source fragment not found in {path}: {old!r}')
    path.write_text(text.replace(old, new, 1))


# Version bump.
replace_once(GRADLE, "versionCode 39\n        versionName '0.9.36-test'", "versionCode 40\n        versionName '0.9.37-test'")

# Prevent accidental dismissal when the user taps outside an interactive AlertDialog.
# Back still works normally and explicit Cancel/Close/Save actions are unchanged.
text = MAIN.read_text()
pattern = re.compile(r'(AlertDialog\s+([A-Za-z_][A-Za-z0-9_]*)\s*=.*?\.create\(\);)', re.S)

parts = []
last = 0
patched = 0
for match in pattern.finditer(text):
    block = match.group(1)
    var = match.group(2)
    # Avoid double-patching if a future source already applies the behavior.
    tail = text[match.end():match.end()+120]
    if f'{var}.setCanceledOnTouchOutside(false);' in tail:
        continue
    parts.append(text[last:match.end()])
    parts.append(f'{var}.setCanceledOnTouchOutside(false);')
    last = match.end()
    patched += 1

if patched == 0:
    raise SystemExit('No AlertDialog create() forms/dialogs were found to protect')
parts.append(text[last:])
text = ''.join(parts)

# Keep About text aligned with the test release when the previous string is present.
text = text.replace(
    'Fida Field 0.9.36 Test\\nPause/resume multi-session service timing, shared sites, team controls and professional field reporting by Fidalix.',
    'Fida Field 0.9.37 Test\\nSticky forms, pause/resume multi-session service timing and professional field reporting by Fidalix.'
)

MAIN.write_text(text)
print(f'Fida Field 0.9.37 sticky forms patch applied to {patched} AlertDialog instances')

from pathlib import Path

GRADLE=Path('fida-field/app/build.gradle')
MAIN=Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')


def replace_once(path:Path, old:str, new:str):
    text=path.read_text()
    if old not in text:
        raise SystemExit(f'Expected source fragment not found in {path}: {old[:260]!r}')
    path.write_text(text.replace(old,new,1))

replace_once(
    GRADLE,
    "versionCode 53\n        versionName '1.0.0'",
    "versionCode 54\n        versionName '1.0.1'"
)

# Replace the complete legacy About block by anchoring on the next method instead
# of depending on how the historical embedded newline was encoded.
text=MAIN.read_text()
start=text.find('        b.addView(section("About"));')
anchor='\n    }\n\n    private void showReports()'
end=text.find(anchor,start)
if start < 0 or end < 0:
    raise SystemExit('Could not locate legacy About block in MainActivity.java')
replacement='        b.addView(section("About"));String edition=BuildConfig.OPEN_EDITION?"Open Edition":"Google Play Edition";b.addView(paragraph("Fida Field "+BuildConfig.VERSION_NAME+"\\n"+edition+"\\nField service & maintenance management by Fidalix."));'
MAIN.write_text(text[:start]+replacement+text[end:])

print('Fida Field 1.0.1 About/version hotfix applied')

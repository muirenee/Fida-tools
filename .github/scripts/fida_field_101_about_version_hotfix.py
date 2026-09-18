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

replace_once(
    MAIN,
    '''        b.addView(section("About"));b.addView(paragraph("Fida Field 0.9.33 Test\\
Shared customer sites, customer-filtered job sites and Owner-only operational cloud reset."));\n''',
    '''        b.addView(section("About"));String edition=BuildConfig.OPEN_EDITION?"Open Edition":"Google Play Edition";b.addView(paragraph("Fida Field "+BuildConfig.VERSION_NAME+"\\n"+edition+"\\nField service & maintenance management by Fidalix."));\n'''
)

print('Fida Field 1.0.1 About/version hotfix applied')

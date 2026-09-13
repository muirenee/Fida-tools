from pathlib import Path

GRADLE = Path('fida-field/app/build.gradle')
CLOUD = Path('fida-field/app/src/main/java/com/fidalix/fidafield/CloudSyncFoundation.java')


def replace_once(path: Path, old: str, new: str):
    text = path.read_text()
    if old not in text:
        raise SystemExit(f'Expected source fragment not found in {path}: {old!r}')
    path.write_text(text.replace(old, new, 1))


replace_once(
    GRADLE,
    "versionCode 44\n        versionName '0.9.41-test'",
    "versionCode 45\n        versionName '0.9.42-test'",
)

# Technicians must receive workspace reference/master data used by the job form.
# Their push permissions stay restricted to jobs; customers/sites/assets/technicians remain read-only.
replace_once(
    CLOUD,
    'String[] pullOrder=canManage?new String[]{"customer","site","asset","technician","job"}:new String[]{"technician","job"};',
    'String[] pullOrder=new String[]{"customer","site","asset","technician","job"};',
)

print('Fida Field 0.9.42 workspace reference sync patch applied')

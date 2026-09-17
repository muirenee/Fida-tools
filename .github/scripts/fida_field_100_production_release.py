from pathlib import Path

GRADLE=Path('fida-field/app/build.gradle')
MAIN=Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
RELEASE=Path('fida-field/RELEASE-1.0.0.md')


def replace_once(path:Path,old:str,new:str):
    text=path.read_text()
    if old not in text:
        raise SystemExit(f'Expected source fragment not found in {path}: {old[:260]!r}')
    path.write_text(text.replace(old,new,1))

# Promote the fully QA'd 0.9.49 build to the first production semantic version.
replace_once(GRADLE,"versionCode 52\n        versionName '0.9.49-test'","versionCode 53\n        versionName '1.0.0'")

# Keep the useful diagnostics screen, but remove pre-release/QA wording from the production UI.
replace_once(
    MAIN,
    '        b.addView(menuCard("Release readiness QA","Role permissions, device identity & multi-device sync checks",v->showReleaseReadiness()));\n',
    '        b.addView(menuCard("System diagnostics","Role permissions, device identity & multi-device sync health",v->showReleaseReadiness()));\n'
)
replace_once(
    MAIN,
    '        setHeader("Release readiness QA","Role & multi-device checks");mainTabScreen=false;clear();LinearLayout b=body(page());',
    '        setHeader("System diagnostics","Role, device & multi-device sync health");mainTabScreen=false;clear();LinearLayout b=body(page());'
)
replace_once(
    MAIN,
    '        b.addView(heroCard("Device QA snapshot","Use this screen on each test phone to confirm that account role, field permissions and workspace synchronization match the expected behavior before 1.0."));\n',
    '        b.addView(heroCard("Device & workspace health","Confirm account role, field permissions, device identity and workspace synchronization on this device."));\n'
)
replace_once(MAIN,'        b.addView(section("Two-device test"));','        b.addView(section("Two-device sync test"));')
replace_once(MAIN,'        b.addView(section("Role test"));','        b.addView(section("Role reference"));')

RELEASE.write_text('''# Fida Field 1.0.0 release baseline\n\n- Package: `com.fidalix.fidafield`\n- Version code: `53`\n- Version name: `1.0.0`\n- Minimum Android SDK: 26\n- Target / compile SDK: 36\n- Open Edition: internal APK build with `FIDA_OPEN_EDITION=true`\n- Google Play Edition: release AAB with `FIDA_OPEN_EDITION=false`\n- Password recovery deep link: `fidafield://password-reset`\n- Workspace invitation deep link: `fidafield://workspace-invite`\n- Cloud backend: Fida Field Supabase project configured through BuildConfig and publishable-key secret\n- Existing signing certificate is preserved for upgrade/signature continuity\n\n## Release validation\n\nCI for 1.0.0 performs source/branding checks, Android lint, unit-test task, APK build, release AAB build, AAB signature verification, SHA-256 generation, and a production validation report.\n\n## Play Console checks before rollout\n\nConfirm the final store listing, privacy-policy URL, Data safety answers, app access/sign-in instructions, content rating, target audience, countries/regions, pricing/subscription products, and the intended testing/production track before rollout.\n''')

print('Fida Field 1.0.0 production release patch applied')

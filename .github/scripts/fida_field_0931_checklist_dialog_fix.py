from pathlib import Path

main_path=Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
gradle_path=Path('fida-field/app/build.gradle')

s=main_path.read_text()
old='new MaterialAlertDialogBuilder(this).setTitle("Service checklist").setMessage("Choose a checklist. Only tick actions you actually performed; selected items are added to Work performed and remain editable.").setItems(types,(d,which)->{'
new='new MaterialAlertDialogBuilder(this).setTitle("Choose service checklist").setItems(types,(d,which)->{'
if old not in s:
    raise SystemExit('0.9.31 patch failed: checklist type dialog pattern not found')
s=s.replace(old,new,1)
main_path.write_text(s)

g=gradle_path.read_text()
if '        versionCode 33\n' not in g or "        versionName '0.9.30-test'\n" not in g:
    raise SystemExit('0.9.31 patch failed: expected 0.9.30 version not found')
g=g.replace('        versionCode 33\n','        versionCode 34\n',1)
g=g.replace("        versionName '0.9.30-test'\n","        versionName '0.9.31-test'\n",1)
gradle_path.write_text(g)

print('Fida Field 0.9.31 checklist dialog fix applied')

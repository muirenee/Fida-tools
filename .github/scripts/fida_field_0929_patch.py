from pathlib import Path
p=Path('fida-field/app/build.gradle')
s=p.read_text()
s=s.replace('        versionCode 31\n','        versionCode 32\n',1)
s=s.replace("        versionName '0.9.28-test'\n","        versionName '0.9.29-test'\n",1)
p.write_text(s)
print('Fida Field 0.9.29 applied')

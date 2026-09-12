from pathlib import Path

main_path = Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
gradle_path = Path('fida-field/app/build.gradle')


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f'0.9.30 patch failed: {label} pattern not found')
    return text.replace(old, new, 1)

s = main_path.read_text()
old = 'form.addView(parts);MaterialButton aiAssist=outlineButton("AI assist report");aiAssist.setOnClickListener(v->showAiReportAssistant(jobTitle,problem,diagnosis,work,parts));form.addView(aiAssist);form.addView(label("Technician"));'
new = 'form.addView(parts);MaterialButton checklist=outlineButton("Service checklist");checklist.setOnClickListener(v->showServiceChecklist(work));form.addView(checklist);MaterialButton aiAssist=outlineButton("AI assist report");aiAssist.setOnClickListener(v->showAiReportAssistant(jobTitle,problem,diagnosis,work,parts));form.addView(aiAssist);form.addView(label("Technician"));'
s = replace_once(s, old, new, 'job form checklist button')

anchor = '    private void showAiReportAssistant(EditText jobTitle,EditText problem,EditText diagnosis,EditText work,EditText parts){\n'
methods = '''    private void showServiceChecklist(EditText work){\n        String[] types={"Preventive maintenance","Corrective maintenance","Installation / commissioning","Inspection / site survey"};\n        new MaterialAlertDialogBuilder(this).setTitle("Service checklist").setMessage("Choose a checklist. Only tick actions you actually performed; selected items are added to Work performed and remain editable.").setItems(types,(d,which)->{\n            if(which==0)showServiceChecklistItems("Preventive maintenance",new String[]{"Visual condition inspected","Connections and cabling checked","Equipment cleaned or housekeeping completed","Operational test completed","Alarms and indicators checked","Maintenance findings recorded"},work);\n            else if(which==1)showServiceChecklistItems("Corrective maintenance",new String[]{"Fault symptoms verified","Fault source isolated","Repair or replacement completed","Connections restored and secured","Operational test completed","Final operating condition verified"},work);\n            else if(which==2)showServiceChecklistItems("Installation / commissioning",new String[]{"Equipment installed or mounted","Power and cabling connected","Configuration completed","Network or service connectivity tested","Functional test completed","Labelling or handover completed"},work);\n            else showServiceChecklistItems("Inspection / site survey",new String[]{"Physical condition inspected","Power and environment checked","Cabling and connections inspected","Configuration or status reviewed","Findings documented","Recommendations recorded"},work);\n        }).setNegativeButton("Cancel",null).show();\n    }\n\n    private void showServiceChecklistItems(String type,String[] items,EditText work){\n        boolean[] checked=new boolean[items.length];\n        AlertDialog dialog=new MaterialAlertDialogBuilder(this).setTitle(type).setMultiChoiceItems(items,checked,(d,which,isChecked)->checked[which]=isChecked).setNegativeButton("Cancel",null).setPositiveButton("Add selected",null).create();\n        dialog.setOnShowListener(x->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{\n            ArrayList<String> selected=new ArrayList<>();for(int i=0;i<items.length;i++)if(checked[i])selected.add(items[i]);\n            if(selected.isEmpty()){toast("Select at least one completed action");return;}\n            String current=val(work);StringBuilder add=new StringBuilder();for(String item:selected){String line="✓ "+item;if(!current.contains(line))add.append(line).append("\\n");}\n            if(add.length()==0){toast("Selected actions are already listed");dialog.dismiss();return;}\n            String block="Checklist confirmed · "+type+"\\n"+add.toString().trim();work.setText(current.isEmpty()?block:current+"\\n\\n"+block);work.setSelection(work.getText().length());dialog.dismiss();toast(selected.size()+" checklist item"+(selected.size()==1?"":"s")+" added");\n        }));dialog.show();\n    }\n\n'''
s = replace_once(s, anchor, methods + anchor, 'guided checklist methods')
main_path.write_text(s)

g = gradle_path.read_text()
g = replace_once(g, '        versionCode 32\n', '        versionCode 33\n', 'version code')
g = replace_once(g, "        versionName '0.9.29-test'\n", "        versionName '0.9.30-test'\n", 'version name')
gradle_path.write_text(g)

print('Fida Field 0.9.30 guided service checklists applied')

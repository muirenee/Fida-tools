from pathlib import Path

main=Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
s=main.read_text()

def rep(old,new,label):
    global s
    if old not in s:
        raise SystemExit(f'0.9.33 site UI patch failed: {label}')
    s=s.replace(old,new,1)

rep('long sites=db.count("sites","customer_id=?",new String[]{String.valueOf(r.id())});','long sites=db.siteCountForCustomer(r.id());','customer list site count')
rep('stats.addView(stat("Sites",db.count("sites","customer_id=?",new String[]{String.valueOf(id)})),','stats.addView(stat("Sites",db.siteCountForCustomer(id)),','customer detail site count')

old='AppDatabase.Row s=db.getSite(id);if(s.id()==0){toast("Site not found");return;}AppDatabase.Row c=db.getCustomer(parse(s.s("customer_id")));setHeader(s.s("name"),"Site service history");clear();LinearLayout b=body(page());LinearLayout top=new LinearLayout(this);top.setOrientation(LinearLayout.HORIZONTAL);MaterialButton back=outlineButton("← Customers");back.setOnClickListener(v->showCustomers());top.addView(back,new LinearLayout.LayoutParams(0,dp(48),1));if(canManageWorkspaceSettings()){top.addView(spacerH());MaterialButton edit=button("Edit");edit.setOnClickListener(v->showSiteDialog(id,parse(s.s("customer_id"))));top.addView(edit,new LinearLayout.LayoutParams(0,dp(48),1));}b.addView(top);'
new='AppDatabase.Row s=db.getSite(id);if(s.id()==0){toast("Site not found");return;}long primaryCustomer=db.firstCustomerIdForSite(id);String siteCustomers=db.customerNamesForSite(id);setHeader(s.s("name"),"Site service history");clear();LinearLayout b=body(page());LinearLayout top=new LinearLayout(this);top.setOrientation(LinearLayout.HORIZONTAL);MaterialButton back=outlineButton("← Customers");back.setOnClickListener(v->showCustomers());top.addView(back,new LinearLayout.LayoutParams(0,dp(48),1));if(canManageWorkspaceSettings()){top.addView(spacerH());MaterialButton edit=button("Edit");edit.setOnClickListener(v->showSiteDialog(id,primaryCustomer));top.addView(edit,new LinearLayout.LayoutParams(0,dp(48),1));}b.addView(top);'
rep(old,new,'site detail header')
rep('b.addView(section("Site profile"));b.addView(info("Customer",c.s("name")));','b.addView(section("Site profile"));b.addView(info("Customers",siteCustomers));','site detail customers')

old='''    private void showSiteDialog(long id,long preferredCustomer){
        if(!requireWorkspaceManager("Site master data"))return;
        AppDatabase.Row r=id>0?db.getSite(id):new AppDatabase.Row();List<Choice> customers=customerChoices(true);LinearLayout form=form();Spinner customer=choiceSpinner(customers);long cid=id>0?parse(r.s("customer_id")):preferredCustomer;setChoice(customer,cid);EditText name=input("Site name *",r.s("name"));EditText address=input("Address",r.s("address"));EditText contact=input("Site contact",r.s("contact"));EditText phone=input("Phone",r.s("phone"));EditText notes=multi("Notes",r.s("notes"));form.addView(label("Customer *"));form.addView(customer);form.addView(name);form.addView(address);form.addView(contact);form.addView(phone);form.addView(notes);
        AlertDialog dialog=new MaterialAlertDialogBuilder(this).setTitle(id>0?"Edit site":"New site").setView(scrollForm(form)).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();dialog.setOnShowListener(x->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{Choice ch=(Choice)customer.getSelectedItem();if(ch==null||ch.id==0){toast("Add/select a customer first");return;}if(val(name).isEmpty()){name.setError("Required");return;}db.saveSite(id,AppDatabase.map("customer_id",String.valueOf(ch.id),"name",val(name),"address",val(address),"contact",val(contact),"phone",val(phone),"notes",val(notes)));dialog.dismiss();toast("Site saved");refreshCurrent();}));dialog.show();
    }
'''
new='''    private void showSiteDialog(long id,long preferredCustomer){
        if(!requireWorkspaceManager("Site master data"))return;
        AppDatabase.Row r=id>0?db.getSite(id):new AppDatabase.Row();ArrayList<Long> selectedCustomers=new ArrayList<>();if(id>0)selectedCustomers.addAll(db.customerIdsForSite(id));else if(preferredCustomer>0)selectedCustomers.add(preferredCustomer);LinearLayout form=form();
        Spinner existing=null;if(id==0){ArrayList<Choice> existingChoices=new ArrayList<>();existingChoices.add(new Choice(0,"— Create a new site —"));for(AppDatabase.Row sr:db.sites(0)){String customers=sr.s("customer_name");existingChoices.add(new Choice(sr.id(),sr.s("name")+(customers.isEmpty()?"":" · "+customers)));}existing=choiceSpinner(existingChoices);form.addView(label("Reuse an existing site (optional)"));form.addView(existing);}
        final Spinner existingSite=existing;MaterialButton customerPicker=outlineButton(customerPickerLabel(selectedCustomers));form.addView(label("Customers *"));form.addView(customerPicker);EditText name=input("Site name *",r.s("name"));EditText address=input("Address",r.s("address"));EditText contact=input("Site contact",r.s("contact"));EditText phone=input("Phone",r.s("phone"));EditText notes=multi("Notes",r.s("notes"));form.addView(name);form.addView(address);form.addView(contact);form.addView(phone);form.addView(notes);
        customerPicker.setOnClickListener(v->{List<AppDatabase.Row> rows=db.customers();if(rows.isEmpty()){toast("Create a customer first");return;}String[] labels=new String[rows.size()];boolean[] checked=new boolean[rows.size()];for(int i=0;i<rows.size();i++){labels[i]=rows.get(i).s("name");checked[i]=selectedCustomers.contains(rows.get(i).id());}new MaterialAlertDialogBuilder(this).setTitle("Customers using this site").setMultiChoiceItems(labels,checked,(d,which,on)->checked[which]=on).setNegativeButton("Cancel",null).setPositiveButton("Apply",(d,w)->{selectedCustomers.clear();for(int i=0;i<rows.size();i++)if(checked[i])selectedCustomers.add(rows.get(i).id());customerPicker.setText(customerPickerLabel(selectedCustomers));}).show();});
        if(existingSite!=null)existingSite.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){public void onItemSelected(AdapterView<?>p,View v,int pos,long rowId){Choice ch=(Choice)existingSite.getSelectedItem();boolean reuse=ch!=null&&ch.id>0;if(reuse){AppDatabase.Row sr=db.getSite(ch.id);name.setText(sr.s("name"));address.setText(sr.s("address"));contact.setText(sr.s("contact"));phone.setText(sr.s("phone"));notes.setText(sr.s("notes"));}name.setEnabled(!reuse);address.setEnabled(!reuse);contact.setEnabled(!reuse);phone.setEnabled(!reuse);notes.setEnabled(!reuse);}public void onNothingSelected(AdapterView<?>p){}});
        AlertDialog dialog=new MaterialAlertDialogBuilder(this).setTitle(id>0?"Edit site":"Add / share site").setView(scrollForm(form)).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();dialog.setOnShowListener(x->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{if(selectedCustomers.isEmpty()){toast("Select at least one customer");return;}Choice reuse=existingSite==null?null:(Choice)existingSite.getSelectedItem();if(reuse!=null&&reuse.id>0){db.addSiteCustomers(reuse.id,selectedCustomers);dialog.dismiss();toast("Existing site linked to selected customer(s)");refreshCurrent();return;}if(val(name).isEmpty()){name.setError("Required");return;}long first=selectedCustomers.get(0);long saved=db.saveSite(id,AppDatabase.map("customer_id",String.valueOf(first),"name",val(name),"address",val(address),"contact",val(contact),"phone",val(phone),"notes",val(notes)));db.setSiteCustomers(saved,selectedCustomers);dialog.dismiss();toast(id>0?"Site updated":"Site created and linked");refreshCurrent();}));dialog.show();
    }
'''
rep(old,new,'shared site dialog')

old='Spinner customer=choiceSpinner(customerChoices(true));setChoice(customer,parse(r.s("customer_id")));Spinner site=choiceSpinner(siteChoices(true));setChoice(site,parse(r.s("site_id")));'
new='Spinner customer=choiceSpinner(customerChoices(true));long assetCustomerId=parse(r.s("customer_id"));setChoice(customer,assetCustomerId);Spinner site=choiceSpinner(siteChoices(true,assetCustomerId));setChoice(site,parse(r.s("site_id")));customer.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){public void onItemSelected(AdapterView<?>p,View v,int pos,long rowId){long keep=selectedChoiceId(site);Choice c=(Choice)customer.getSelectedItem();replaceChoices(site,siteChoices(true,c==null?0:c.id),keep);}public void onNothingSelected(AdapterView<?>p){}});'
rep(old,new,'asset site filter')
rep('Choice c=(Choice)customer.getSelectedItem(),s=(Choice)site.getSelectedItem();try{db.saveAsset','Choice c=(Choice)customer.getSelectedItem(),s=(Choice)site.getSelectedItem();if(c!=null&&c.id>0&&s!=null&&s.id>0&&!db.siteBelongsToCustomer(s.id,c.id)){toast("Select a site linked to the selected customer");return;}try{db.saveAsset','asset site validation')

old='Spinner customer=choiceSpinner(customerChoices(true));long customerId=id>0?parse(r.s("customer_id")):parse(ar.s("customer_id"));setChoice(customer,customerId);Spinner site=choiceSpinner(siteChoices(true));long siteId=id>0?parse(r.s("site_id")):parse(ar.s("site_id"));setChoice(site,siteId);Spinner asset=choiceSpinner(assetChoices(true));'
new='Spinner customer=choiceSpinner(customerChoices(true));long customerId=id>0?parse(r.s("customer_id")):parse(ar.s("customer_id"));setChoice(customer,customerId);Spinner site=choiceSpinner(siteChoices(true,customerId));long siteId=id>0?parse(r.s("site_id")):parse(ar.s("site_id"));setChoice(site,siteId);customer.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){public void onItemSelected(AdapterView<?>p,View v,int pos,long rowId){long keep=selectedChoiceId(site);Choice c=(Choice)customer.getSelectedItem();replaceChoices(site,siteChoices(true,c==null?0:c.id),keep);}public void onNothingSelected(AdapterView<?>p){}});Spinner asset=choiceSpinner(assetChoices(true));'
rep(old,new,'job site filter')
rep('Choice c=(Choice)customer.getSelectedItem(),s=(Choice)site.getSelectedItem(),a=(Choice)asset.getSelectedItem();Map<String,String> m=','Choice c=(Choice)customer.getSelectedItem(),s=(Choice)site.getSelectedItem(),a=(Choice)asset.getSelectedItem();if(c!=null&&c.id>0&&s!=null&&s.id>0&&!db.siteBelongsToCustomer(s.id,c.id)){toast("Select a site linked to the selected customer");return;}Map<String,String> m=','job site validation')

old='''    private List<Choice> siteChoices(boolean empty){ArrayList<Choice> out=new ArrayList<>();if(empty)out.add(new Choice(0,"— None —"));for(AppDatabase.Row r:db.sites(0))out.add(new Choice(r.id(),r.s("customer_name")+" / "+r.s("name")));return out;}
'''
new='''    private List<Choice> siteChoices(boolean empty){return siteChoices(empty,0);}
    private List<Choice> siteChoices(boolean empty,long customerId){ArrayList<Choice> out=new ArrayList<>();if(empty)out.add(new Choice(0,"— None —"));for(AppDatabase.Row r:db.sites(customerId)){String customers=r.s("customer_name");out.add(new Choice(r.id(),customerId>0?r.s("name"):(customers.isEmpty()?r.s("name"):customers+" / "+r.s("name"))));}return out;}
    private long selectedChoiceId(Spinner s){Object o=s.getSelectedItem();return o instanceof Choice?((Choice)o).id:0;}
    private void replaceChoices(Spinner s,List<Choice> list,long selected){ArrayAdapter<Choice>a=new ArrayAdapter<>(this,android.R.layout.simple_spinner_item,list);a.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);s.setAdapter(a);setChoice(s,selected);}
    private String customerPickerLabel(List<Long> ids){int n=ids==null?0:ids.size();return n==0?"Select customers *":n+" customer"+(n==1?"":"s")+" selected";}
'''
rep(old,new,'site choice helpers')

main.write_text(s)
print('Fida Field 0.9.33 shared site UI patch applied')

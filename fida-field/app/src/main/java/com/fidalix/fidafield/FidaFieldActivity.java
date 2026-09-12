package com.fidalix.fidafield;

import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageButton;
import android.widget.LinearLayout;

public class FidaFieldActivity extends MainActivity {
    @Override protected void onCreate(Bundle state){
        super.onCreate(state);
        getWindow().getDecorView().post(this::installTimeAction);
    }

    private void installTimeAction(){
        ViewGroup content=findViewById(android.R.id.content);if(content==null||content.getChildCount()==0)return;View root=content.getChildAt(0);if(!(root instanceof LinearLayout))return;LinearLayout shell=(LinearLayout)root;if(shell.getChildCount()==0)return;View first=shell.getChildAt(0);if(!(first instanceof LinearLayout))return;LinearLayout bar=(LinearLayout)first;
        ImageButton time=new ImageButton(this);time.setImageResource(android.R.drawable.ic_menu_recent_history);time.setColorFilter(Color.WHITE);time.setBackgroundColor(Color.TRANSPARENT);time.setContentDescription("Time & productivity");time.setTooltipText("Time & productivity");time.setPadding(dpLocal(9),dpLocal(9),dpLocal(9),dpLocal(9));time.setOnClickListener(v->startActivity(new Intent(this,TimeProductivityActivity.class)));
        LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(dpLocal(42),dpLocal(42));p.setMargins(dpLocal(4),0,dpLocal(4),0);int index=Math.max(0,bar.getChildCount()-1);bar.addView(time,index,p);
    }

    private int dpLocal(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
}

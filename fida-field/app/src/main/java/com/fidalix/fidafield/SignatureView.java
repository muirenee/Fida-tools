package com.fidalix.fidafield;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.util.AttributeSet;
import android.view.MotionEvent;
import android.view.View;

public class SignatureView extends View {
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path path = new Path();
    private boolean empty = true;

    public SignatureView(Context context) { super(context); init(); }
    public SignatureView(Context context, AttributeSet attrs) { super(context, attrs); init(); }

    private void init() {
        paint.setColor(Color.rgb(25, 35, 33));
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(5f);
        paint.setStrokeCap(Paint.Cap.ROUND);
        paint.setStrokeJoin(Paint.Join.ROUND);
        setBackgroundColor(Color.WHITE);
        setMinimumHeight(420);
    }

    @Override protected void onDraw(Canvas canvas) { super.onDraw(canvas); canvas.drawPath(path, paint); }

    @Override public boolean onTouchEvent(MotionEvent event) {
        float x = event.getX(), y = event.getY();
        switch (event.getAction()) {
            case MotionEvent.ACTION_DOWN: path.moveTo(x, y); empty = false; invalidate(); return true;
            case MotionEvent.ACTION_MOVE: path.lineTo(x, y); invalidate(); return true;
            case MotionEvent.ACTION_UP: path.lineTo(x, y); invalidate(); return true;
            default: return false;
        }
    }

    public void clear() { path.reset(); empty = true; invalidate(); }
    public boolean isEmpty() { return empty; }

    public Bitmap bitmap() {
        int w = Math.max(getWidth(), 800), h = Math.max(getHeight(), 420);
        Bitmap b = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(b);
        c.drawColor(Color.WHITE);
        draw(c);
        return b;
    }
}

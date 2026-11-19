package uz.navbot.tv;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.view.WindowManager;
import android.webkit.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.concurrent.*;

/** Dedicated TV viewer. No credentials, JavaScript bridge or local server. */
public final class MainActivity extends Activity {
    private static final String ORIGIN = "http://172.20.30.31";
    private static final String TV = ORIGIN + "/tv";
    private WebView web;
    private final Handler main = new Handler(Looper.getMainLooper());
    private ScheduledExecutorService updates;
    private String revision;
    private boolean active, failed;
    private final Runnable retry = () -> { if(active) web.loadUrl(TV); };
    private void fullscreen() {
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN
            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
    }
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        web = new WebView(this); setContentView(web);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true); s.setDomStorageEnabled(true);
        s.setCacheMode(WebSettings.LOAD_NO_CACHE); s.setAllowFileAccess(false);
        s.setAllowContentAccess(false); s.setMediaPlaybackRequiresUserGesture(false);
        s.setSupportMultipleWindows(false); s.setTextZoom(100);
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return !TV.equals(url); // Only the fixed public TV page may navigate.
            }
            @Override public void onPageStarted(WebView view, String url, android.graphics.Bitmap icon) {
                failed=false;
            }
            @Override public void onPageFinished(WebView view, String url) {
                if(!failed) main.removeCallbacks(retry);
                fullscreen();
            }
            @Override public void onReceivedError(WebView view, int code, String text, String url) {
                if(TV.equals(url)) { failed=true; main.removeCallbacks(retry); main.postDelayed(retry,10000); }
            }
        });
        web.loadUrl(TV); fullscreen();
    }
    private void checkUpdate() {
        HttpURLConnection connection=null;
        try {
            connection=(HttpURLConnection)new URL(ORIGIN+"/api/tv-version").openConnection();
            connection.setConnectTimeout(4000); connection.setReadTimeout(4000);
            connection.setInstanceFollowRedirects(false); connection.setUseCaches(false);
            if(connection.getResponseCode()!=200) return;
            ByteArrayOutputStream out=new ByteArrayOutputStream();
            try(InputStream in=connection.getInputStream()) {
                byte[] b=new byte[512]; int n;
                while((n=in.read(b))!=-1) {out.write(b,0,n);if(out.size()>4096)return;}
            }
            final String next=new org.json.JSONObject(out.toString("UTF-8")).getString("version");
            main.post(() -> {
                if(!active)return;
                if(revision!=null && !revision.equals(next))web.loadUrl(TV);
                revision=next;
            });
        } catch(Exception ignored) { /* Keep the current display during a server restart. */ }
        finally {if(connection!=null)connection.disconnect();}
    }
    @Override protected void onResume() {
        super.onResume(); active=true; web.onResume(); fullscreen();
        if(failed)main.post(retry);
        updates=Executors.newSingleThreadScheduledExecutor();
        updates.scheduleWithFixedDelay(this::checkUpdate,0,30,TimeUnit.SECONDS);
    }
    @Override protected void onPause() {
        active=false;main.removeCallbacks(retry);
        if(updates!=null)updates.shutdownNow();
        web.onPause();super.onPause();
    }
    @Override public void onWindowFocusChanged(boolean focused) {
        super.onWindowFocusChanged(focused);if(focused)fullscreen();
    }
    @Override public void onBackPressed() {
        new AlertDialog.Builder(this).setTitle("NAVBOT TV")
            .setItems(new String[]{"Yangilash", "Yoqilganda ochilishni sozlash", "Ilovadan chiqish"},(d,which)->{
                if(which==0)web.loadUrl(TV);
                else if(which==1)configureHome();else finish();
            }).setNegativeButton("Bekor qilish",null).show();
    }
    private void configureHome() {
        new AlertDialog.Builder(this).setTitle("Avtomatik ochilish")
            .setMessage("Keyingi sozlamada NAVBOT TV ni standart bosh ekran (Home) sifatida tanlang. Ortga qaytarish uchun Android sozlamalarida oldingi Launcher ni tanlashingiz mumkin.")
            .setPositiveButton("Sozlamani ochish", (d,which) -> {
                android.content.Intent intent=new android.content.Intent(android.provider.Settings.ACTION_HOME_SETTINGS);
                if(intent.resolveActivity(getPackageManager())!=null)startActivity(intent);
                else new AlertDialog.Builder(this).setMessage("Android sozlamalari → Ilovalar → Standart ilovalar → Bosh ekran bo‘limidan NAVBOT TV ni tanlang.").setPositiveButton("OK",null).show();
            }).setNegativeButton("Bekor qilish",null).show();
    }
    @Override protected void onDestroy() {web.destroy();super.onDestroy();}
}

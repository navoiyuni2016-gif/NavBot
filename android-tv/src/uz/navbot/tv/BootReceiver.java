package uz.navbot.tv;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

/** Best-effort boot startup; default HOME is the fallback for restricted firmware. */
public final class BootReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        String action=intent.getAction();
        if(!Intent.ACTION_BOOT_COMPLETED.equals(action)
                && !Intent.ACTION_MY_PACKAGE_REPLACED.equals(action))return;
        try {
            context.startActivity(new Intent(context,MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_CLEAR_TOP));
        } catch(RuntimeException restricted) {
            Log.w("NavbotTV","Boot launch restricted; select NAVBOT TV as default Home.");
        }
    }
}

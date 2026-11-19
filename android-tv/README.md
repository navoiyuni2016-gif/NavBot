# NAVBOT TV for X96 Max / Android TV

A standalone, signed APK without third-party kiosk licensing. Android 5.0+ (API21), landscape TV/box, all CPU architectures (no native libraries). Opens the fixed LAN URL `http://172.20.30.31/tv`; the device must be on the server network. No login credentials or JavaScript native bridge. Other page navigation is blocked. Uses the installed Android System WebView; keep it updated.

Install `downloads/NAVBOT-TV.apk` through USB/file manager, permitting this file manager to install unknown apps when Android asks. Open NAVBOT TV from the launcher. Immersive fullscreen and keep-screen-on apply while the app is open. Back opens Reload/Exit. It does not change the Android launcher or promise automatic launch after power-on.

The APK contains no copy of the TV website. After the server includes `/api/tv-version`, the app checks the public HTML/i18n fingerprint every 30 seconds while active and reloads on a change; normal queue polling and settings remain handled by the website. Server updates do not require reinstalling the APK. Native behavior or fixed IP changes require a new APK. First load needs the LAN server; connection errors retry every 10 seconds. The current page remains during transient update-check failures. Paper/printer functions are not included.

Build: `build.sh` needs Java17+, Android build-tools35.0.0, android-35/android.jar, and ECJ3.38.0. Set ANDROID_BUILD_TOOLS, ANDROID_JAR, ECJ_JAR, NAVBOT_KEYSTORE and NAVBOT_KEY_PASSWORD. Keystore alias `navbot-tv`. The release signing key and password are outside git at `/workspace/.navbot-signing/`; preserve a private backup to sign future APK upgrades. Never publish the key/password. Generated APK is signed with v1/v2/v3 and verified with apksigner.

Validation: compiled against Android API35, dexed for API21, signature and manifest checked, public HTTP endpoints tested. Android hardware/emulator execution, X96 vendor firmware fullscreen behavior and physical audio remain unverified. Recorded audio autoplay is enabled; WebView speech synthesis support varies by device.

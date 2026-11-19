#!/usr/bin/env bash
set -euo pipefail
# Android build-tools 35.0.0, platform android-35, ECJ 3.38, Java 17+.
: "${ANDROID_BUILD_TOOLS:?Set Android build-tools directory}"
: "${ANDROID_JAR:?Set platform android.jar path}"
: "${ECJ_JAR:?Set ecj.jar path}"
: "${NAVBOT_KEYSTORE:?Set private release keystore path}"
: "${NAVBOT_KEY_PASSWORD:?Set release key password}"
export NAVBOT_KEY_PASSWORD
project_root=$(cd "$(dirname "$0")/.." && pwd)
build_dir=$(mktemp -d)
trap 'rm -rf "$build_dir"' EXIT
mkdir -p "$build_dir/classes" "$build_dir/dex"
java -jar "$ECJ_JAR" -8 -nowarn -proc:none -bootclasspath "$ANDROID_JAR:$ANDROID_BUILD_TOOLS/core-lambda-stubs.jar" -d "$build_dir/classes" "$project_root"/android-tv/src/uz/navbot/tv/*.java
find "$build_dir/classes" -name '*.class' > "$build_dir/classes.txt"
"$ANDROID_BUILD_TOOLS/d8" --min-api 21 --lib "$ANDROID_JAR" --output "$build_dir/dex" @"$build_dir/classes.txt"
"$ANDROID_BUILD_TOOLS/aapt" package -f -M "$project_root/android-tv/AndroidManifest.xml" -S "$project_root/android-tv/res" -I "$ANDROID_JAR" -F "$build_dir/unsigned.apk"
python3 - "$build_dir/unsigned.apk" "$build_dir/dex/classes.dex" <<'PY'
import sys,zipfile
with zipfile.ZipFile(sys.argv[1],'a',compression=zipfile.ZIP_DEFLATED) as apk:apk.write(sys.argv[2],'classes.dex')
PY
"$ANDROID_BUILD_TOOLS/zipalign" -f 4 "$build_dir/unsigned.apk" "$build_dir/aligned.apk"
"$ANDROID_BUILD_TOOLS/apksigner" sign --v4-signing-enabled false --ks "$NAVBOT_KEYSTORE" --ks-key-alias navbot-tv --ks-pass env:NAVBOT_KEY_PASSWORD --key-pass env:NAVBOT_KEY_PASSWORD --out "$project_root/downloads/NAVBOT-TV.apk" "$build_dir/aligned.apk"
"$ANDROID_BUILD_TOOLS/apksigner" verify --verbose "$project_root/downloads/NAVBOT-TV.apk"

chmod 644 "$project_root/downloads/NAVBOT-TV.apk"

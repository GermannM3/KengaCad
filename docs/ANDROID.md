# Android APK install and factory robot link

## Why the APK was blocked

Release builds without a dedicated keystore are signed with the **debug** certificate.
Google Play Protect and many OEMs (Samsung, Xiaomi, Huawei) refuse such APKs even after
"Allow unknown apps".

From **v2.3.0** the release APK is signed with `kengacad-android.keystore` (CI secrets).

## Local signed build

```powershell
.\scripts\setup_android_keystore.ps1
.\scripts\publish_github_android_secrets.ps1
.\scripts\sync_mobile_config.ps1
dotnet publish KengaCAD.Mobile\KengaCAD.Mobile.csproj -f net9.0-android -c Release -p:AndroidPackageFormat=apk
```

Look for `*-Signed.apk` under `KengaCAD.Mobile\bin\Release\net9.0-android\`.

## ADB install (most reliable)

```text
adb devices
adb install -r installers\Output\KengaCAD_Professional_2.3.0_android.apk
```

## Factory connectivity model

| Role | Where | What |
|------|-------|------|
| Offline programming | Windows KengaCAD | CAD, sim, multi-robot, OPC UA |
| Shop-floor transfer | Android | Same LAN as robot, FTP upload |
| UR control | Android UR Dashboard :29999 | robotmode / load / play / stop |
| Live I/O | Windows OPC UA | full NodeId sync |

Phone never drives unprotected motion: FTP only drops files; UR play requires confirm dialog.

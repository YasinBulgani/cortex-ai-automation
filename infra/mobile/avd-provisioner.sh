#!/usr/bin/env bash
# BGTS Mobil Otomasyon — Lokal AVD & iOS Simulator provisioner
# ------------------------------------------------------------
# macOS için: 6 Android AVD + 4 iOS Simulator oluşturur.
# Linux için: yalnızca Android AVD kısmı çalışır (iOS Sim mümkün değil).
#
# Ön koşullar (macOS):
#   - Xcode + Command Line Tools kurulu
#   - Android Studio kurulu, ANDROID_HOME ayarlı
#   - `avdmanager`, `sdkmanager`, `emulator` PATH'te
#   - `xcrun simctl` çalışıyor
#
# Kullanım:
#   chmod +x infra/mobile/avd-provisioner.sh
#   ./infra/mobile/avd-provisioner.sh           # oluşturur
#   ./infra/mobile/avd-provisioner.sh --delete  # temizler

set -euo pipefail

ARCH="arm64-v8a"        # Apple Silicon için; Intel Mac'te "x86_64" kullanın
IMAGE_TAG="google_apis"

ANDROID_PROFILES=(
  "bgts_pixel_8:pixel_8:34"
  "bgts_pixel_8_pro:pixel_8_pro:34"
  "bgts_galaxy_s23:pixel_7:33"       # OneUI skin yok, pixel_7 yakın profil
  "bgts_pixel_6:pixel_6:32"
  "bgts_pixel_5:pixel_5:30"
  "bgts_nexus_5x:Nexus 5X:28"
)

IOS_SIMULATORS=(
  "bgts_iphone_15_pro:iPhone 15 Pro:iOS17.4"
  "bgts_iphone_15:iPhone 15:iOS17.4"
  "bgts_iphone_14:iPhone 14:iOS16.4"
  "bgts_iphone_se_3:iPhone SE (3rd generation):iOS15.5"
)

action="${1:-create}"

log()  { printf "\e[36m[bgts-mobile]\e[0m %s\n" "$*"; }
warn() { printf "\e[33m[bgts-mobile]\e[0m %s\n" "$*"; }
err()  { printf "\e[31m[bgts-mobile]\e[0m %s\n" "$*" >&2; }

check_android() {
  if ! command -v avdmanager >/dev/null 2>&1; then
    err "avdmanager bulunamadı. Android SDK kurun ve ANDROID_HOME'u ayarlayın."
    return 1
  fi
  if [[ -z "${ANDROID_HOME:-}" ]]; then
    warn "ANDROID_HOME boş — \$HOME/Library/Android/sdk varsayıyorum"
    export ANDROID_HOME="$HOME/Library/Android/sdk"
  fi
}

check_ios() {
  if ! command -v xcrun >/dev/null 2>&1; then
    warn "xcrun yok — iOS Simulator atlanacak (muhtemelen Linux host)."
    return 1
  fi
  return 0
}

install_system_image() {
  local api="$1"
  local pkg="system-images;android-${api};${IMAGE_TAG};${ARCH}"
  log "System image kontrol: ${pkg}"
  if sdkmanager --list_installed 2>/dev/null | grep -q "${pkg}"; then
    log "  ✓ zaten kurulu"
  else
    log "  ↓ indiriliyor..."
    yes | sdkmanager "${pkg}" >/dev/null
  fi
}

create_android() {
  for entry in "${ANDROID_PROFILES[@]}"; do
    IFS=':' read -r avd_name device api <<< "$entry"
    log "AVD oluşturuluyor: $avd_name (api=$api device=$device)"
    install_system_image "$api"
    if avdmanager list avd 2>/dev/null | grep -q "Name: ${avd_name}"; then
      log "  → zaten var, atlıyor"
      continue
    fi
    echo "no" | avdmanager create avd \
      -n "$avd_name" \
      --package "system-images;android-${api};${IMAGE_TAG};${ARCH}" \
      --device "$device" \
      --force >/dev/null
    log "  ✓ oluşturuldu"
  done
}

create_ios() {
  for entry in "${IOS_SIMULATORS[@]}"; do
    IFS=':' read -r sim_name device runtime <<< "$entry"
    log "iOS Sim oluşturuluyor: $sim_name ($device)"
    if xcrun simctl list devices 2>/dev/null | grep -q "$sim_name"; then
      log "  → zaten var, atlıyor"
      continue
    fi
    device_type_id=$(xcrun simctl list devicetypes | awk -F '[()]' -v d="$device" 'index($0,d){print $2; exit}')
    runtime_id=$(xcrun simctl list runtimes | awk -F '[()]' -v r="$runtime" 'index($0,r){print $2; exit}')
    if [[ -z "$device_type_id" || -z "$runtime_id" ]]; then
      warn "  ! device_type ya da runtime bulunamadı, atlıyor"
      continue
    fi
    xcrun simctl create "$sim_name" "$device_type_id" "$runtime_id" >/dev/null
    log "  ✓ oluşturuldu"
  done
}

delete_all() {
  log "Mevcut BGTS AVD'ler siliniyor..."
  for entry in "${ANDROID_PROFILES[@]}"; do
    IFS=':' read -r avd_name _ _ <<< "$entry"
    avdmanager delete avd -n "$avd_name" >/dev/null 2>&1 || true
  done
  if check_ios; then
    for entry in "${IOS_SIMULATORS[@]}"; do
      IFS=':' read -r sim_name _ _ <<< "$entry"
      xcrun simctl delete "$sim_name" >/dev/null 2>&1 || true
    done
  fi
  log "✓ temizlik tamam"
}

case "$action" in
  --delete|delete)
    check_android && delete_all
    ;;
  create|*)
    check_android && create_android
    check_ios && create_ios
    log "Tamamlandı. Çalıştırmak için: emulator -avd bgts_pixel_8"
    log "iOS Sim: xcrun simctl boot bgts_iphone_15_pro; open -a Simulator"
    ;;
esac

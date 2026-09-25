#!/usr/bin/env bash
# examples/lekiwi/dino_camera_settings.sh: apply the Dino LeKiwi camera controls on the Raspberry Pi.
# UVC controls reset on reboot and on USB replug, so run this before lekiwi_host (start_dino_host.sh
# does) or from the udev rule in this directory. Values were verified on the robot on 2026-09-25:
# - wrist (OV5640 module): auto exposure lowered the rate to ~8 fps in dim light; disabling the
#   dynamic frame rate restores ~30 fps. Autofocus hunts, so the focus is fixed (100 keeps the egg
#   sharp at the catch pose; slight blur at the grasp is accepted).
# - front: aperture-priority auto exposure halved the rate to 15 fps; manual exposure 30 ms with
#   gain 32 gives ~30 fps and a usable image in the room. Brighter venues need a shorter exposure.
# Override any value with an environment variable, e.g. FRONT_EXPOSURE=150 ./dino_camera_settings.sh
set -u

WRIST_DEV="${WRIST_DEV:-/dev/v4l/by-path/platform-xhci-hcd.1-usb-0:1:1.0-video-index0}"
FRONT_DEV="${FRONT_DEV:-/dev/v4l/by-path/platform-xhci-hcd.1-usb-0:2:1.0-video-index0}"
WRIST_FOCUS="${WRIST_FOCUS:-100}"        # focus_absolute 0-1023, verified 2026-09-25
FRONT_EXPOSURE="${FRONT_EXPOSURE:-300}"  # exposure_time_absolute in 100 us units; 300 = 30 ms (30 fps)
FRONT_GAIN="${FRONT_GAIN:-32}"           # 0-63
POWER_LINE="${POWER_LINE:-1}"            # 1 = 50 Hz (Japan east), 2 = 60 Hz (USA); avoids flicker banding

apply() {
  local dev="$1"; shift
  if [ ! -e "$dev" ]; then
    echo "dino_camera_settings: $dev not present, skipping" >&2
    return 0
  fi
  local ctrl
  for ctrl in "$@"; do
    if ! v4l2-ctl -d "$dev" --set-ctrl="$ctrl"; then
      echo "dino_camera_settings: $dev: failed to set $ctrl" >&2
    fi
  done
}

apply "$WRIST_DEV" \
  exposure_dynamic_framerate=0 \
  focus_automatic_continuous=0 \
  "focus_absolute=$WRIST_FOCUS" \
  "power_line_frequency=$POWER_LINE"

apply "$FRONT_DEV" \
  auto_exposure=1 \
  "exposure_time_absolute=$FRONT_EXPOSURE" \
  "gain=$FRONT_GAIN" \
  "power_line_frequency=$POWER_LINE"

echo "dino_camera_settings: applied (wrist focus $WRIST_FOCUS, front exposure $FRONT_EXPOSURE gain $FRONT_GAIN, power line $POWER_LINE)"

#!/usr/bin/env bash
# examples/lekiwi/start_dino_host.sh: start the Dino LeKiwi host on the Raspberry Pi with the camera
# controls applied first (dino_camera_settings.sh), so every session gets the same 30 fps, fixed-focus
# wrist view and the manual front exposure. Run from the fork checkout in the lerobot312 env:
#   ./examples/lekiwi/start_dino_host.sh            # robot id dino_kiwi
#   ROBOT_ID=other ./examples/lekiwi/start_dino_host.sh
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
ROBOT_ID="${ROBOT_ID:-dino_kiwi}"

"$HERE/dino_camera_settings.sh"
exec python -m lerobot.robots.lekiwi.lekiwi_host --robot.id="$ROBOT_ID" "$@"

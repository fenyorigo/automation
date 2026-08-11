#!/usr/bin/env bash
set -euo pipefail

LABEL="${1:?Használat: $0 <megnevezés>}"

python -m connectlife.dump \
  --username "${CONNECTLIFE_USERNAME:?CONNECTLIFE_USERNAME is required}"

SOURCE=""

for file in 009-104*.json; do
    [[ "$file" == *"-static.json" ]] && continue
    [[ "$file" == *"-property-list.json" ]] && continue

    nickname=$(jq -r '.deviceNickName // empty' "$file")

    if [[ "$nickname" == "Dolgozó" ]]; then
        SOURCE="$file"
        break
    fi
done

if [[ -z "$SOURCE" ]]; then
    echo "Hiba: nem található a Dolgozó klíma a dumpban." >&2
    exit 1
fi

STAMP=$(date '+%Y%m%d-%H%M%S')
TARGET="snapshots/dolgozo/${STAMP}-${LABEL}.json"

cp "$SOURCE" "$TARGET"

echo
echo "Mentve: $TARGET"
echo

jq -r '
  {
    nickname: .deviceNickName,
    online: .offlineState,
    power: .statusList.t_power,
    mode: .statusList.t_work_mode,
    measured_temperature: .statusList.f_temp_in,
    target_temperature: .statusList.t_temp,
    fan_speed: .statusList.t_fan_speed,
    fan_mute: .statusList.t_fan_mute,
    eco: .statusList.t_eco,
    sleep: .statusList.t_sleep,
    super: .statusList.t_super,
    swing_up_down: .statusList.t_up_down
  }
' "$TARGET"

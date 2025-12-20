#!/usr/bin/env bash
##############################################################################

# AirCron – daily zone-automation wrapper for Spotify (shpotify) + Apple Music

# ▸ Robust AirPlay / Airfoil connect + disconnect verbs

# ▸ Service-aware volume logic

# ▸ Safe quoting, single run_osascript entry-point

# ▸ Self-logging to ~/Library/Logs/AirCron/cron.log

##############################################################################

set -o pipefail

LOG_FILE=~/Library/Logs/AirCron/cron.log
mkdir -p "$(dirname "$LOG_FILE")"
exec >>"$LOG_FILE" 2>&1

echo "$(date): DEBUG: Args: $*"

# Best-effort single-run lock to avoid overlapping cron jobs
LOCK_FILE=/tmp/aircron_run.lock
if command -v flock >/dev/null 2>&1; then
    exec 200>"$LOCK_FILE"
    if ! flock -n 200; then
        echo "$(date): Another AirCron invocation is running; skipping."
        exit 0
    fi
else
    echo "$(date): INFO: flock not available; continuing without lock"
fi

###########################################################################

# ── Helpers ───────────────────────────────────────────────────────────────

###########################################################################

# Escape for AppleScript strings

essc() {
printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

# Normalize speaker names from CSV or UI inputs
normalize_speaker_name() {
    echo "$1" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

# Convert comma-separated names into an AppleScript list
csv_to_as_list() {
    local csv="$1" list=""
    local IFS=',' arr item
    read -ra arr <<< "$csv"
    for item in "${arr[@]}"; do
        item="$(normalize_speaker_name "$item")"
        [ -z "$item" ] && continue
        item="$(essc "$item")"
        if [ -z "$list" ]; then
            list="\"$item\""
        else
            list="$list, \"$item\""
        fi
    done
    if [ -z "$list" ]; then
        printf "{}"
    else
        printf "{%s}" "$list"
    fi
}

# Clamp a percentage to 0-100 and strip trailing '%'
clamp_pct() {
    local raw=${1%%%}
    # drop decimals if present
    raw=${raw%%.*}
    if ! [[ "$raw" =~ ^-?[0-9]+$ ]]; then
        raw=50
    fi
    if [ "$raw" -lt 0 ]; then raw=0; fi
    if [ "$raw" -gt 100 ]; then raw=100; fi
    printf '%s' "$raw"
}

# Wait for a process name to appear (best effort)
wait_for_process() {
    local proc="$1" tries="${2:-10}" delay="${3:-0.5}"
    local i
    for i in $(seq 1 "$tries"); do
        if pgrep -x "$proc" >/dev/null; then
            return 0
        fi
        sleep "$delay"
    done
    return 1
}

# Ensure an app is running; launch if missing and wait briefly
ensure_app() {
    local proc="$1" app_name="$2"
    if ! pgrep -x "$proc" >/dev/null; then
        echo "$(date): $app_name not running, launching..."
        open -g -a "$app_name" >/dev/null 2>&1 || open -a "$app_name" >/dev/null 2>&1
    fi
    wait_for_process "$proc" 12 0.5 || echo "$(date): WARN: $app_name not ready after wait"
}

# run osascript with logging

run_osascript() {
local script="$1"
echo "$(date): Running osascript >>>"
echo "$script"
echo "$script" | /usr/bin/osascript 2>&1
local rc=${PIPESTATUS[1]}
[ $rc -ne 0 ] && echo "$(date): osascript exit $rc"
return $rc
}

# Ensure Music.app is running

ensure_music() {
ensure_app "Music" "Music"
}

# Ensure Airfoil is running

ensure_airfoil() {
ensure_app "Airfoil" "Airfoil"
}

# Check Music process (used for play/pause)

music_running() {
pgrep -x "Music" >/dev/null
}

###########################################################################

# ── Spotify CLI lookup ────────────────────────────────────────────────────

###########################################################################
if   [ -x "/usr/local/bin/spotify" ];    then SPOTIFY_CMD="/usr/local/bin/spotify"
elif [ -x "/opt/homebrew/bin/spotify" ]; then SPOTIFY_CMD="/opt/homebrew/bin/spotify"
elif [ -x "/usr/bin/spotify" ];        then SPOTIFY_CMD="/usr/bin/spotify"
elif command -v spotify >/dev/null;      then SPOTIFY_CMD="$(command -v spotify)"
else SPOTIFY_CMD=""
fi

ensure_spotify_cli() {
    if [ -z "$SPOTIFY_CMD" ]; then
        echo "$(date): spotify-cli missing"
        return 1
    fi
    return 0
}

###########################################################################

# ── Parse CLI arguments ──────────────────────────────────────────────────

###########################################################################
SPEAKER="$1"     # "All Speakers", single name, or Custom:A,B,C
ACTION="$2"      # play|pause|resume|volume|connect|disconnect
ARG1="$3"        # playlist / URI / volume %
ARG2="$4"        # spare
SERVICE="$5"     # applemusic | spotify | (blank ⇒ spotify)

[ -z "$SERVICE" ] && SERVICE="spotify"

echo "$(date): DEBUG: SPEAKER='$SPEAKER' ACTION='$ACTION' SERVICE='$SERVICE'"

###########################################################################

# ── Speaker connect / disconnect ─────────────────────────────────────────

###########################################################################

set_airfoil_source_spotify() {
    run_osascript 'tell application "Airfoil"
        try
            set existingSources to (every application source whose application file is "/Applications/Spotify.app")
            if (count of existingSources) > 0 then
                set current audio source to first item of existingSources
            else
                set aSource to make new application source
                set application file of aSource to "/Applications/Spotify.app"
                set current audio source to aSource
            end if
        end try
    end tell'
}

connect_speakers() {
local zone esc_zone
zone="$1"
esc_zone=$(essc "$1")
if [ "$2" = "applemusic" ]; then
ensure_music
        if [[ "$1" == "All Speakers" ]]; then
            run_osascript 'tell application "Music" to repeat with d in (every AirPlay device)
    set selected of d to true
end repeat'
        elif [[ "$1" == Custom:* ]]; then
            local names="${1#Custom:}"
            local list
            list=$(csv_to_as_list "$names")
            run_osascript "tell application \"Music\"
                set connectNames to ${list}
                repeat with d in (every AirPlay device)
                    if name of d is in connectNames then set selected of d to true
                end repeat
            end tell"
        else
            run_osascript "tell application \"Music\"
                repeat with d in (every AirPlay device)
                    if name of d is \"${esc_zone}\" then set selected of d to true
                end repeat
            end tell"
fi
else
        # Spotify → Airfoil
        ensure_airfoil
        set_airfoil_source_spotify
        ensure_app "Spotify" "Spotify"
if [[ "$1" == "All Speakers" ]]; then
run_osascript 'tell application "Airfoil" to connect to (every speaker)'
elif [[ "$1" == Custom:* ]]; then
IFS=',' read -ra arr <<< "${1#Custom:}"
for spk in "${arr[@]}"; do
clean_spk="$(normalize_speaker_name "$spk")"
esc_spk=$(essc "$clean_spk")
run_osascript "tell application \"Airfoil\" to connect to (every speaker whose name is \"${esc_spk}\")"
done
else
run_osascript "tell application \"Airfoil\" to connect to (every speaker whose name is \"${esc_zone}\")"
fi
fi
}

disconnect_speakers() {
local zone esc_zone
zone="$1"
esc_zone=$(essc "$1")
if [ "$2" = "applemusic" ]; then
ensure_music
if [[ "$1" == "All Speakers" ]]; then
run_osascript 'tell application "Music" to repeat with d in (every AirPlay device)
    set selected of d to false
end repeat'
        elif [[ "$1" == Custom:* ]]; then
            local names="${1#Custom:}"
            local list
            list=$(csv_to_as_list "$names")
            run_osascript "tell application \"Music\"
                set dropNames to ${list}
                repeat with d in (every AirPlay device)
                    if name of d is in dropNames then set selected of d to false
                end repeat
            end tell"
        else
            run_osascript "tell application \"Music\"
                repeat with d in (every AirPlay device)
                    if name of d is \"${esc_zone}\" then set selected of d to false
                end repeat
            end tell"
fi
else
ensure_airfoil
if [[ "$1" == "All Speakers" ]]; then
run_osascript 'tell application "Airfoil" to disconnect from (every speaker whose connected is true)'
elif [[ "$1" == Custom:* ]]; then
IFS=',' read -ra arr <<< "${1#Custom:}"
for spk in "${arr[@]}"; do
clean_spk="$(normalize_speaker_name "$spk")"
esc_spk=$(essc "$clean_spk")
run_osascript "tell application \"Airfoil\" to disconnect from (every speaker whose name is \"${esc_spk}\")"
done
else
run_osascript "tell application \"Airfoil\" to disconnect from (every speaker whose name is \"${esc_zone}\")"
fi
fi
}

###########################################################################

# ── Volume helpers ───────────────────────────────────────────────────────

###########################################################################
set_global_volume() {
    local service="$1" pct
    pct=$(clamp_pct "$2")

    case "$service" in
        spotify)
            if ensure_spotify_cli; then
                $SPOTIFY_CMD vol "$pct"
            fi
            ;;
        applemusic)
            ensure_music
            run_osascript "tell application \"Music\" to set sound volume to ${pct}"
            ;;
        *)
            echo "$(date): WARN: Unknown service '$service' for volume"
            ;;
    esac
}

set_speaker_volume() {
local zone arr esc_spk f pct
zone="$2"; pct=$(clamp_pct "$3"); f=$(awk "BEGIN {printf \"%.2f\", ${pct}/100}")
if [[ "$zone" == Custom:* ]]; then
IFS=',' read -ra arr <<< "${zone#Custom:}"
else
arr=("$zone")
fi

case "$1" in
    spotify)
        ensure_airfoil
        ensure_app "Spotify" "Spotify"
        for spk in "${arr[@]}"; do
            clean_spk="$(normalize_speaker_name "$spk")"
            esc_spk=$(essc "$clean_spk")
            run_osascript "tell application \"Airfoil\"
                try
                    set (volume of (first speaker whose name is \"${esc_spk}\")) to ${f}
                end try
            end tell"
        done
        ;;
    applemusic)
        ensure_music
        for spk in "${arr[@]}"; do
            clean_spk="$(normalize_speaker_name "$spk")"
            esc_spk=$(essc "$clean_spk")
            run_osascript "tell application \"Music\"
                try
                    if \"${esc_spk}\" is \"All Speakers\" then
                        repeat with d in (every AirPlay device)
                            set volume of d to ${pct}
                        end repeat
                    else
                        repeat with d in (every AirPlay device)
                            if name of d is \"${esc_spk}\" then set volume of d to ${pct}
                        end repeat
                    end if
                end try
            end tell"
        done
        ;;
    *)
        echo "$(date): WARN: Unknown service '$1' for speaker volume"
        ;;
esac
}

###########################################################################

# ── Action dispatcher ────────────────────────────────────────────────────

###########################################################################
case "$ACTION" in
play)
connect_speakers "$SPEAKER" "$SERVICE"
if [ "$SERVICE" = "applemusic" ]; then
ensure_music
run_osascript "tell application \"Music\" to play playlist \"$(essc "$ARG1")\""
else
if ! ensure_spotify_cli; then exit 1; fi
ensure_app "Spotify" "Spotify"
$SPOTIFY_CMD play uri "$ARG1"
fi
;;
pause)
if [ "$SERVICE" = "applemusic" ]; then
ensure_music; run_osascript 'tell application "Music" to pause'
else
if ensure_spotify_cli; then
    ensure_app "Spotify" "Spotify"
    $SPOTIFY_CMD pause
fi
fi
;;
resume)
if [ "$SERVICE" = "applemusic" ]; then
ensure_music; run_osascript 'tell application "Music" to play'
else
if ensure_spotify_cli; then
    ensure_app "Spotify" "Spotify"
    $SPOTIFY_CMD play
fi
fi
;;
volume)
if [ "$SPEAKER" = "All Speakers" ]; then
set_global_volume "$SERVICE" "$ARG1"
else
set_speaker_volume "$SERVICE" "$SPEAKER" "$ARG1"
fi
;;
connect)
connect_speakers    "$SPEAKER" "$SERVICE" ;;
disconnect)
disconnect_speakers "$SPEAKER" "$SERVICE" ;;
*)
echo "$(date): ERROR – unknown action '$ACTION'"; exit 1 ;;
esac

echo "$(date): AirCron '$ACTION' finished OK"

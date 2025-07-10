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

###########################################################################

# ── Helpers ───────────────────────────────────────────────────────────────

###########################################################################

# Escape for AppleScript strings

essc() {
printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

# run osascript with logging

run_osascript() {
local script="$1"
echo "$(date): Running osascript >>>"
echo "$script"
echo "$script" | osascript 2>&1
local rc=${PIPESTATUS[1]}
[ $rc -ne 0 ] && echo "$(date): osascript exit $rc"
return $rc
}

# Ensure Music.app is running

ensure_music() {
if ! pgrep -x "Music" >/dev/null; then
echo "$(date): Music not running, launching..."
open -a Music
sleep 2
fi
}

# Ensure Airfoil is running

ensure_airfoil() {
if ! pgrep -x "Airfoil" >/dev/null; then
echo "$(date): Airfoil not running, launching..."
open -a Airfoil
sleep 2
fi
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
            local list="\"${names//,/\",\"}\""
            run_osascript "tell application \"Music\"
                set connectNames to {${list}}
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
        run_osascript 'tell application "Airfoil"
            set aSource to make new application source
            set application file of aSource to "/Applications/Spotify.app"
            set current audio source to aSource
        end tell'
if [[ "$1" == "All Speakers" ]]; then
run_osascript 'tell application "Airfoil" to connect to (every speaker)'
elif [[ "$1" == Custom:* ]]; then
IFS=',' read -ra arr <<< "${1#Custom:}"
for spk in "${arr[@]}"; do
esc_spk=$(essc "$spk")
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
            local list="\"${names//,/\",\"}\""
            run_osascript "tell application \"Music\"
                set dropNames to {${list}}
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
clean_spk="$(echo "$spk" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
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
local pct=${1%%%}   # strip any trailing '%'
# Set volume for both services
ensure_music
run_osascript "tell application \"Music\" to set sound volume to ${pct}"
if [ -n "$SPOTIFY_CMD" ]; then
$SPOTIFY_CMD vol ${pct}
fi
}

set_speaker_volume() {
local zone arr esc_spk f pct
zone="$1"; pct=${2%%%}; f=$(awk "BEGIN {printf \"%.2f\", ${pct}/100}")
if [[ "$zone" == Custom:* ]]; then
IFS=',' read -ra arr <<< "${zone#Custom:}"
else
arr=("$zone")
fi

# Set volume for both Airfoil (Spotify) and Apple Music AirPlay devices
ensure_airfoil
ensure_music

for spk in "${arr[@]}"; do
clean_spk="$(echo "$spk" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
esc_spk=$(essc "$clean_spk")

# Set Airfoil speaker volume
run_osascript "tell application \"Airfoil\"
    try
        set (volume of (first speaker whose name is \"${esc_spk}\")) to ${f}
    end try
end tell"

# Set Apple Music AirPlay device volume (works even if disconnected)
run_osascript "tell application \"Music\"
    try
        repeat with d in (every AirPlay device)
            if name of d is \"${esc_spk}\" then set volume of d to ${pct}
        end repeat
    end try
end tell"
done
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
if [ -z "$SPOTIFY_CMD" ]; then echo "$(date): spotify-cli missing"; exit 1; fi
$SPOTIFY_CMD play uri "$ARG1"
fi
;;
pause)
if [ "$SERVICE" = "applemusic" ]; then
ensure_music; run_osascript 'tell application "Music" to pause'
else
[ -n "$SPOTIFY_CMD" ] && $SPOTIFY_CMD pause
fi
;;
resume)
if [ "$SERVICE" = "applemusic" ]; then
ensure_music; run_osascript 'tell application "Music" to play'
else
[ -n "$SPOTIFY_CMD" ] && $SPOTIFY_CMD play
fi
;;
volume)
if [ "$SPEAKER" = "All Speakers" ]; then
set_global_volume "$ARG1"
else
set_speaker_volume "$SPEAKER" "$ARG1"
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

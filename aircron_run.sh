#!/usr/bin/env bash

# AirCron shell wrapper script
# Called by cron jobs to execute actions on specific speaker zones

SPEAKER="$1"
ACTION="$2"
shift 2  # Remove first two arguments

# Find spotify-cli in common locations
SPOTIFY_CMD=""
if [ -x "/usr/local/bin/spotify" ]; then
    SPOTIFY_CMD="/usr/local/bin/spotify"
elif [ -x "/opt/homebrew/bin/spotify" ]; then
    SPOTIFY_CMD="/opt/homebrew/bin/spotify"
elif [ -x "/usr/bin/spotify" ]; then
    SPOTIFY_CMD="/usr/bin/spotify"
elif command -v spotify >/dev/null 2>&1; then
    SPOTIFY_CMD="spotify"
else
    echo "$(date): ERROR - spotify-cli not found" >> ~/Library/Logs/AirCron/cron.log
    exit 1
fi

# Log all actions
LOG_FILE=~/Library/Logs/AirCron/cron.log
mkdir -p "$(dirname "$LOG_FILE")"
echo "$(date): AirCron $ACTION for '$SPEAKER' with args: $* (using $SPOTIFY_CMD)" >> "$LOG_FILE"

# Handle "All Speakers" by targeting all available speakers
if [ "$SPEAKER" = "All Speakers" ]; then
    # For "All Speakers", first execute the Spotify action globally
    case "$ACTION" in
        play) 
            echo "$(date): Executing global $ACTION with args: $*" >> "$LOG_FILE"
            "$SPOTIFY_CMD" play uri "$@"
            ;;
        pause) 
            echo "$(date): Executing global $ACTION" >> "$LOG_FILE"
            "$SPOTIFY_CMD" pause 
            ;;
        resume) 
            echo "$(date): Executing global $ACTION" >> "$LOG_FILE"
            "$SPOTIFY_CMD" play 
            ;;
        volume) 
            echo "$(date): Executing global Spotify volume control with volume: $1" >> "$LOG_FILE"
            "$SPOTIFY_CMD" vol "$1" >> "$LOG_FILE" 2>&1
            echo "$(date): Spotify volume command exit code: $?" >> "$LOG_FILE"
            ;;
    esac
    
    # Then try to connect all available speakers to Airfoil
    ALL_SPEAKERS=$(osascript -e 'tell application "Airfoil" to get (name of every speaker)' 2>/dev/null | tr ',' '\n' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
    
    if [ -n "$ALL_SPEAKERS" ]; then
        echo "$(date): Found speakers for connection: $ALL_SPEAKERS" >> "$LOG_FILE"
        echo "$ALL_SPEAKERS" | while IFS= read -r speaker; do
            if [ -n "$speaker" ]; then
                echo "$(date): Attempting to connect speaker: $speaker" >> "$LOG_FILE"
                # Try to connect speaker, but don't fail if it doesn't work
                osascript -e "tell app \"Airfoil\" to try
                    connect (every speaker whose name is \"$speaker\")
                end try" 2>/dev/null || echo "$(date): Could not connect speaker: $speaker" >> "$LOG_FILE"
            fi
        done
    else
        echo "$(date): No speakers found in Airfoil, but Spotify action completed" >> "$LOG_FILE"
    fi
elif [[ "$SPEAKER" == Custom:* ]]; then
    # Handle custom speaker selection
    CUSTOM_SPEAKERS=$(echo "$SPEAKER" | sed 's/Custom://')
    
    if [ -z "$CUSTOM_SPEAKERS" ]; then
        echo "No speakers specified in custom selection"
        exit 1
    fi
    
    # Split speakers by comma and execute action for each
    echo "$CUSTOM_SPEAKERS" | tr ',' '\n' | while IFS= read -r speaker; do
        speaker=$(echo "$speaker" | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')  # trim whitespace
        if [ -n "$speaker" ]; then
            echo "Executing $ACTION for custom speaker: $speaker" >> "$LOG_FILE"
            case "$ACTION" in
                play) 
                    "$SPOTIFY_CMD" play uri "$@" && osascript -e "tell app \"Airfoil\" to connect (every speaker whose name is \"$speaker\")" 
                    ;;
                pause) 
                    "$SPOTIFY_CMD" pause 
                    ;;
                resume) 
                    "$SPOTIFY_CMD" play 
                    ;;
                volume) 
                    # For custom speakers, control individual Airfoil speaker volume
                    echo "$(date): Setting Airfoil speaker volume for: $speaker to $1%" >> "$LOG_FILE"
                    # Convert percentage (0-100) to Airfoil volume (0.0-1.0)
                    AIRFOIL_VOLUME=$(echo "scale=2; $1 / 100" | bc -l)
                    osascript -e "tell application \"Airfoil\" to try
                        set (volume of every speaker whose name is \"$speaker\") to $AIRFOIL_VOLUME
                    end try" >> "$LOG_FILE" 2>&1
                    echo "$(date): Airfoil speaker volume command exit code: $?" >> "$LOG_FILE"
                    ;;
            esac
        fi
    done
else
    # Handle single speaker - use Airfoil speaker volume control
    case "$ACTION" in
        play) 
            "$SPOTIFY_CMD" play uri "$@" && osascript -e "tell app \"Airfoil\" to connect (every speaker whose name is \"$SPEAKER\")" 
            ;;
        pause) 
            "$SPOTIFY_CMD" pause 
            ;;
        resume) 
            "$SPOTIFY_CMD" play 
            ;;
        volume) 
            # For individual speakers, control Airfoil speaker volume, not Spotify volume
            echo "$(date): Setting Airfoil speaker volume for: $SPEAKER to $1%" >> "$LOG_FILE"
            # Convert percentage (0-100) to Airfoil volume (0.0-1.0)
            AIRFOIL_VOLUME=$(echo "scale=2; $1 / 100" | bc -l)
            osascript -e "tell application \"Airfoil\" to try
                set (volume of every speaker whose name is \"$SPEAKER\") to $AIRFOIL_VOLUME
            end try" >> "$LOG_FILE" 2>&1
            echo "$(date): Airfoil speaker volume command exit code: $?" >> "$LOG_FILE"
            ;;
    esac
fi

echo "AirCron action completed successfully" 
#!/bin/bash

essc() {
printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

zone="Joel's MacBook Pro"
esc_zone=$(essc "$zone")

cmd="tell application \"Music\"
    try
        set current AirPlay devices to (the first AirPlay device whose name is \"${esc_zone}\")
    end try
end tell"

echo "Generated AppleScript command:"
echo "=========================="
echo "$cmd"
echo "=========================="
echo "Command length: ${#cmd}"

#!/bin/bash
essc() {
printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

result=$(essc "Joel's MacBook Pro")
echo "Result: '${result}'"
echo "Length: ${#result}"

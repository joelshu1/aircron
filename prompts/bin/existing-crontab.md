theorchids-Mini:~ theorchid$ crontab -l
# Run connect.scpt every day at 7:00 AM
0 7 * * * osascript /usr/local/bin/connect.scpt

# Run vollow.sh every day at 7:50 AM
50 7 * * * /usr/local/bin/vollow.sh

# Run vol60.sh every day at 8:30 AM
30 8 * * * /usr/local/bin/vol60.sh

# Run regulate.scpt every day at 10:00 AM
0 10 * * * osascript /usr/local/bin/regulate.scpt

# Run vol80.sh every day at 10:00 AM
0 10 * * * /usr/local/bin/vol80.sh

# Run volfull.sh every day at 11:00 AM
0 11 * * * /usr/local/bin/volfull.sh

# Run playtoastdaytime.sh every day at 8:00 AM
0 8 * * * /usr/local/bin/playtoastdaytime.sh

# Run regulate.scpt every day at 1:00 PM
0 13 * * * osascript /usr/local/bin/regulate.scpt

# Run regulate.scpt every day at 5:00 PM
0 17 * * * osascript /usr/local/bin/regulate.scpt

# Run playtoastnighttime.sh every day at 5:30 PM
30 17 * * * /usr/local/bin/playtoastnighttime.sh

# Run regulate.scpt every day at 8:00 PM
0 20 * * * osascript /usr/local/bin/regulate.scpt

# Stop
30 22 * * * /usr/local/bin/stop.sh

theorchids-Mini:~ theorchid$ 
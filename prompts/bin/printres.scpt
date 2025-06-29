tell application "Google Chrome"
    set newWindow to make new window
    set newTab to make new tab at newWindow with properties {URL:"https://baochao65.larksuite.com/share/base/view/shrusDhoGJeo6cwUakVPQjMq0Ec"}
    activate newWindow
    delay 60 -- Wait for the page to load
end tell

set screenshotPath to "/tmp/larksuite_screenshot.png"

-- Capture the screenshot
do shell script "screencapture -x " & quoted form of screenshotPath

-- Print the screenshot, check if printer command executes successfully
try
    do shell script "lp " & quoted form of screenshotPath
on error
    display dialog "Printing failed. Please check your printer configuration."
end try

-- Wait for the print job to initiate
delay 5

-- Delete the screenshot after printing
do shell script "rm " & quoted form of screenshotPath

-- Close the Chrome window opened for the screenshot
tell application "Google Chrome"
    if exists newWindow then
        close newWindow
    end if
end tell

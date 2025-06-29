tell application "Airfoil"
	set (volume of every speaker whose name is "TBSS") to 0.3
	set (volume of every speaker whose name starts with "orchid-up") to 0.5
	connect to every speaker whose name starts with "TBSS"
	connect to every speaker whose name starts with "orchid-"
end tell

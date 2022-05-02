from pathlib import Path
import os
import sys
import glob

if len(sys.argv) != 3:
	print("Usage: %s [git hash] [build number]" % (sys.argv[0]))
	sys.exit(-1)

githash     = "%05X" % int(sys.argv[1], 16)
buildnumber = "%03d" % int(sys.argv[2])

for boardfileinfo in Path(".").rglob("*.kicad_pcb"):
	if boardfileinfo.is_dir():
		continue

	boardfileAbsPath = str(boardfileinfo.absolute())

	with open(boardfileAbsPath, 'r') as file:
		filedata = file.read()

	filedata = filedata.replace('GIT_XXXXX', ('GIT_%s' % githash))
	filedata = filedata.replace('BUILD_XXX', ('BUILD_%s' % buildnumber))

	with open(boardfileAbsPath, 'w') as file:
		file.write(filedata)
import os
import sys
import glob

if len(sys.argv) != 3:
	print("Usage: %s [git hash] [build number]" % (sys.argv[0]))
	sys.exit(-1)

githash     = "%05X" % int(sys.argv[1], 16)
buildnumber = "%03d" % int(sys.argv[2])

pcbfiles = glob.glob("*.kicad_pcb")
if len(pcbfiles) == 0:
	raise Exception("No PCBs found")

for pcbfile in pcbfiles:
	pcbfile = os.path.join( os.getcwd(), pcbfile)

	with open(pcbfile, 'r') as file :
		filedata = file.read()

	filedata = filedata.replace('GIT_XXXXX', ('GIT_%d' % githash))
	filedata = filedata.replace('BUILD_XXX', ('BUILD_%d' % buildnumber))

	with open(pcbfile, 'w') as file:
		file.write(filedata)
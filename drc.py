import re
from typing import List

import pywinauto
import pywintypes
import os
import sys
import time
import glob

# It's a good idea to flush stdout so that Jenkins gets a better idea of progress.
def printWithFlush(toWrite):
	sys.stdout.write(toWrite)
	if toWrite.endswith('\n') == False:
		sys.stdout.write('\n')
	sys.stdout.flush()

class violationLocation:
	itemName: str
	posY: float
	posX: float

	def __init__(self, posX, posY, itemName):
		self.posX = posX
		self.posY = posY
		self.itemName = itemName

class violationInfo:
	locations: List[violationLocation]

	def __init__(self, newSectionName):
		self.section = newSectionName
		self.id = None
		self.message = None
		self.rule = None
		self.severity = None
		self.locations = []

class DRCReport:
	friendlyName: str
	violations: List[violationInfo]

	def __init__(self, friendlyName):
		self.friendlyName = friendlyName
		self.violations = []

	def containsErrors(self):
		return len(self.violations) > 0

def main():
	# Enumerate PCB files, processing each in turn...
	pcbfiles = glob.glob("*.kicad_pcb")
	if len(pcbfiles) == 0:
		raise Exception("No PCBs found")

	results = []
	for pcbfilefriendlyname in pcbfiles:
		pcbfile = os.path.join(os.getcwd(), pcbfilefriendlyname)
		results.append(doDRC(pcbfile))

	# .. and write out our result XML.
	resultXML = seraliseResults(results)
	with open("drc.xml", "w") as f:
		f.write(resultXML)


def seraliseResults(resultsToSerialise):
	resLines = []
	resLines.append("<testsuites>")
	for resultInfo in resultsToSerialise:
		violationIdx = 0
		for violation in resultInfo.violations:
			# We output one 'testcase' per DRC error, containing a single failure.
			resLines.append(f"\t<testcase classname=\"kicad\" name=\"DRC_{resultInfo.friendlyName}_{violationIdx}\">")
			resLines.append(f"\t\t<failure type=\"{violation.section} severity {violation.severity}\">")
			resLines.append(f"\t\t\t{violation.rule}: {violation.message}")
			for loc in violation.locations:
				resLines.append(f"\t\t\tSee {loc.itemName} at ({loc.posX}, {loc.posY})")
			resLines.append(f"\t\t</failure>")
			resLines.append("\t</testcase>")
			violationIdx = violationIdx + 1
	resLines.append("</testsuites>")

	return "\n".join(resLines)

def doDRC(pcbfile):
	pcbfilefriendlyname = os.path.basename(pcbfile)

	printWithFlush("Starting pcbnew")
	app = pywinauto.application.Application().start("c:\\Program Files\\KiCad\\6.0\\bin\\pcbnew.exe")

	printWithFlush("Awaiting main window")
	mainWindow = None
	while True:
		try:
			app.top_window().wait("exists", timeout = 1)

			# If pcbnew is already running, hit 'yes' to the confirmation dialog that asks if we want to start another instance.
			if app.top_window().child_window(best_match="pcbnew is already running").exists():
				app.top_window().Yes.click()
				app.top_window().wait("exists", timeout = 5)
				continue
			if app.top_window().child_window(best_match="Configure global footprint library").exists():
				app.top_window().OK.click()
				app.top_window().wait("exists", timeout = 5)
				continue

			# On first run, we might see this dialog asking if we want to use hardware acceleration for graphics.
			if 	app.top_window().child_window(best_match="Enable Acceleration").exists() or \
				app.top_window().child_window(best_match="Enable Graphics Acceleration").exists():
				# If there's a 'no thanks' button, click it. Otherwise, there's some legacy behavior on old KiCard versions
				# which we handle by just hitting the 'n' key.
				if app.top_window().NoThanks.exists():
					app.top_window().NoThanks.click()
				else:
					app.top_window().type_keys('N')
				continue

			# We may also see this setup window.
			if 	app.window(best_match="Configure KiCad Settings Path").exists():
				# Just accept defaults.
				app.top_window().OK.click()
				continue

			for candidateTitle in ("Pcbnew", "PCB Editor"):
				mainWindow = app.window(title=candidateTitle)
				if mainWindow.exists() != 0:
					break

			if mainWindow is not None:
				break

		except RuntimeError:
			pass

	printWithFlush("Opening file")
	mainWindow.menu_select("File->Open")

	app.OpenBoardFile.type_keys(pcbfile, with_spaces = True)
	app.OpenBoardFile.Open.click()

	while True:
		try:
			if app.OpenBoardFile.exists(timeout=None, retry_interval=None):
				printWithFlush( 'Retrying file open dialog completion')
				app.OpenBoardFile.Open.click()
				continue
			else:
				break
		except Exception as e:
			printWithFlush(str(e))
			continue

	#
	# Once we open the file, we must search for the main window again. This is because it will
	# have changed its caption from 'Pcbnew' to 'Pcbnew - <name of file we opened>'.
	#
	printWithFlush("Open complete, finding main window")

	while True:
		try:
			mainWindow = list(filter(lambda x: (x.window_text().find("Pcbnew") == 0) or (x.window_text().find("— PCB Editor") != -1), app.windows()))
			if len(mainWindow) != 1:
				raise Exception()
			mainWindow = mainWindow[0]
			break
		except AttributeError:
			printWithFlush("Waiting for load to complete")
			time.sleep(1)
			continue
		except pywinauto.controls.hwndwrapper.InvalidWindowHandle:
			printWithFlush("Waiting for load to complete")
			time.sleep(1)
			continue

	printWithFlush("waiting for DRC menu to be enabled")

	while True:
		try:
			try:
				if app.Drc_Control.wait("exists", timeout=0.5):
					break
				printWithFlush("Still waiting for DRC menu..")
			except pywinauto.timings.TimeoutError:
				try:
					mainWindow.menu_select("Inspect->Design Rules Checker")
				except pywinauto.base_wrapper.ElementNotEnabled:
					printWithFlush( 'Waiting for menu option to be enabled')
		except pywintypes.error:
			pass
		except RuntimeError:
			pass

	printWithFlush("setting DRC window options")
#	app.Drc_Control.child_window(best_match="Test for parity between PCB and schematic").check()
	app.Drc_Control.child_window(best_match="Refill all zones before performing DRC").check()

	# And start the DRC.
	printWithFlush("Doing DRC")
	if app.Drc_Control.Run_DRC.exists():
		app.Drc_Control.Run_DRC.wait("enabled")
		app.Drc_Control.Run_DRC.click()
	else:
		raise Exception("Can't find button to start DRC")

	# Now the DRC is started.
	while True:
		try:
			# See if the 'are you sure you want to refill the copper zones' dialog appears, and if so, OK it.
			app.Confirmation.wait("exists", timeout=0.5)
			if app.Confirmation.yes.exists():
				app.Confirmation.yes.click()
				continue
			elif app.Confirmation.Refill.exists():
				app.Confirmation.Refill.click()
				continue
			else:
				raise Exception("Can't find refill OK button")
		except pywinauto.timings.TimeoutError:
			# ok, nevermind, there is no 'refill copper zones' dialog here.
			pass
		except pywintypes.error:
			pass

		# See if DRC has completed. It'll enable the 'Run DRC' button when it has.
		try:
			app.Drc_Control.Run_DRC.wait("enabled", timeout=0.5)
			printWithFlush("DRC complete")
			break
		except pywintypes.error:
			pass
		except pywinauto.timings.TimeoutError:
			pass

	# Save a DRC report
	printWithFlush("Saving DRC report..")
	app.Drc_Control.Save.click()
	reportFileBox = app.window(best_match="Save Report to File", enabled_only=True)
	reportFileBox.type_keys(os.path.join(os.getcwd(), "report.txt"))
	reportFileBox.child_window(best_match="Save").wait("enabled", 2).click()

	# If the file already exists, overwrite it. Otherwise, just wait for the save to complete.
	while True:
		confirmBox = app.window(best_match="Confirm Save As", enabled_only=True)
		if confirmBox.exists():
			printWithFlush("Overwriting old DRC report")
			confirmBox.Yes.click()
			confirmBox.wait_not("visible", 3)

		overwriteBox = app.window(best_match="Save Report to File", enabled_only=True)
		if overwriteBox.exists() == False:
			break

	printWithFlush("Saving DRC report complete.")

	# Now we can close the DRC window
	app.Drc_Control.close()

	# and close the main application. If pcbnew shows the 'do you want to save your changes' dialog, this will time out,
	# so hit 'exit without save' and try again if we see a timeout. Also, sometimes we may see an assertion failure related
	# to opengl, so cancel that too if we see it:
	printWithFlush("closing pcbnew..")
	while app.is_process_running():
		try:
			if app.Dialog0.ExitWithoutSave.exists():
				printWithFlush("Closing 'save changes' dialog via 'exit without save'")
				app.Dialog0.ExitWithoutSave.click()
				continue
			if app.Dialog0.DiscardChanges.exists():
				printWithFlush("Closing 'save changes' dialog via 'discard changes'")
				app.Dialog0.DiscardChanges.click()
				continue
			elif app.wxWidgetsDebugAlert.exists():
				printWithFlush("Closing 'assertion failure' dialog")
				printWithFlush( app.wxWidgetsDebugAlert.dump_tree())
				app.wxWidgetsDebugAlert.Yes.click()
				continue
			else:
				mainWindow.close(wait_time = 1)
		except Exception as e:
			printWithFlush("Exception closing pcbnew - " + str(e))

	# Now read the DRC report, and see if any errors were detected.
	return parseDRCReport(pcbfilefriendlyname, os.path.join(os.getcwd(), "report.txt"))

def parseDRCReport(pcbfilefriendlyname, reportFilename):
	errorInfo = []
	currentSection = None
	with open(reportFilename, "r") as f:
		drclines = f.readlines()

		for line in drclines:
			m = re.match( "\*\* Found [0-9]* (.*) \*\*", line)
			if m is not None:
				currentSection = m.groups()[0]
				continue

			# Something like "[silk_over_copper]: Silkscreen clipped by solder mask"
			m = re.match( "^\[(.*)\]: (.*)$", line)
			if m is not None:
				errorInfo.append(violationInfo(currentSection))
				errorInfo[-1].id = m.groups()[0]
				errorInfo[-1].message = m.groups()[1]
				continue

			for key in ["Rule", "Severity"]:
				m = re.match( f".*{key}: ([^;]*).*?", line)
				if m is not None:
					setattr(errorInfo[-1], key.lower(), m.groups()[0].strip())

			# Something line "    @(132.2500 mm, 68.8500 mm): Line on F.Silkscreen"
			m = re.match( "^    @\(([0-9.]*) mm, ([0-9.]*) mm\): (.*)", line)
			if m is not None:
				errorInfo[-1].locations.append(violationLocation(float(m.groups()[0]), float(m.groups()[1]), m.groups()[2] ))
				continue

	# And we're done.
	toRet = DRCReport(pcbfilefriendlyname)
	toRet.violations = errorInfo
	return toRet

if __name__ == "__main__":
	main()

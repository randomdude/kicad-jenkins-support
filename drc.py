import pywinauto
import pywintypes
import os
import sys
import time
import glob

# It's a good idea to flush stdout so that Jenkins gets a better idea of progress.
def printWithFlush(toWrite):
	sys.stdout.write(toWrite)
	if toWrite[-1] != '\n':
		sys.stdout.write('\n')
	sys.stdout.flush()

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
	resLines = []
	resLines.append("<testsuites>")
	for resultInfo in results:
		resLines.append("\t<testcase classname=\"kicad\" name=\"DRC_"  + resultInfo['filename'] +"\">")
		if resultInfo['errorStatus'] == 1:
			resLines.append("\t\t<failure type=\"DRC found errors\">")
			for drcFailure in filter(lambda x: x.strip().find("@") == 0, resultInfo['drclines']):
				resLines.append("\t\t\t" + drcFailure.strip())
			resLines.append("\t\t</failure>")
		resLines.append("\t</testcase>")
	resLines.append("</testsuites>")

	with open("drc.xml", "w") as f:
		f.write("\n".join(resLines))

def doDRC(pcbfile):
	pcbfilefriendlyname = os.path.basename(pcbfile)

	printWithFlush("Starting pcbnew")
	app = pywinauto.application.Application().start("c:\\Program Files\\KiCad\\bin\\pcbnew.exe")

	printWithFlush("Awaiting main window")
	while True:
		try:
			app.top_window().wait("exists", timeout = 5)

			# If pcbnew is already running, hit 'yes' to the confirmation dialog that asks if we want to start another instance.
			if app.top_window().child_window(best_match="pcbnew is already running").exists():
				app.top_window().Yes.click();
				app.top_window().wait("exists", timeout = 5)
				continue
			if app.top_window().child_window(best_match="Configure global footprint library").exists():
				app.top_window().OK.click();
				app.top_window().wait("exists", timeout = 5)
				continue
			# On first run, we might see this dialog asking if we want to use hardware acceleration for graphics.
			if app.top_window().child_window(best_match="Enable Acceleration").exists() or app.top_window().child_window(best_match="Enable Graphics Acceleration").exists() :
				# If there's a 'no thanks' button, click it. Otherwise, there's some legacy behavior on old KiCard versions
				# which we handle by just hitting the 'n' key.
				if app.top_window().NoThanks.exists():
					app.top_window().NoThanks.click()
				else:
					app.top_window().type_keys('N')
				continue

			mainWindow = app.window(title="Pcbnew")
			if mainWindow.exists() != 0:
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
			printWithFlush( e)
			continue

	#
	# Once we open the file, we must search for the main window again. This is because it will
	# hanve changed its caption from 'Pcbnew' to 'Pcbnew - <name of file we opened>'.
	#
	printWithFlush("Open complete, finding main window")

	while True:
		try:
			mainWindow = filter(lambda x: (x.window_text().find("Pcbnew") ==0), app.windows())
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
	while True:
		try:
			app.Drc_Control.child_window(best_match="Refill all zones before performing DRC").check()
			# Set the output path. We must use .check_by_click here, since otherwise pcbnew doesn't enable the textbox.
			checkbox = app.Drc_Control.child_window(best_match="CreateReportFileCheckBox")
			reportFileBox = app.Drc_Control.child_window(best_match="Create Report File:Edit")

			while True:
				if checkbox.get_check_state() == 0:
					checkbox.check_by_click()
					try:
						reportFileBox.wait("enabled")
						break
					except pywinauto.timings.TimeoutError:
						printWithFlush("retrying checkbox checking")
						continue
			break
		except pywintypes.error:
			pass

	reportFileBox.type_keys(os.getcwd() + "\\report.txt")

	# And start the DRC.
	printWithFlush("Doing DRC")
	# 5.1.0_1 renames 'start DRC' to 'run DRC'.
	if app.Drc_Control.Run_DRC.exists():
		app.Drc_Control.Run_DRC.wait("enabled")
		app.Drc_Control.Run_DRC.click()
	elif app.Drc_Control.Start_DRC.exists():
		app.Drc_Control.Start_DRC.wait("enabled")
		app.Drc_Control.Start_DRC.click()
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
			break
		except pywinauto.timings.TimeoutError:
			# ok, nevermind, there is no 'refill copper zones' dialog here.
			pass
		except pywintypes.error as e:
			pass

		# See if DRC has completed.
		#
		# My version of KiCad (5.0.2-1) throws an assert failure when generating DRC and outputting to a report file (!!)
		# the assert is in CallStrftime, and gives us a yes/no/cancel dialog, with 'no' being the option to ignore the 
		# failure. Ignoring the failure seems safe - it means the date is not printed in the report but has no other effects
		# (so far!) so I'm just bodging this and doing that for now.
		# The assertion failure:
		#
		# ../wxWidgets-3.0.4/src/common/datetime.cpp(298): assert "Assert failure" failed in CallStrftime(): strftime() failed
		# Do you want to stop the program?\nYou can also choose [Cancel] to suppress further warnings
		#
		#
		try:
			if app.wxWidgetsDebugAlert.exists(timeout=0.5):
				app.wxWidgetsDebugAlert.No.click()
			# Is the DRC complete yet?
			if app.Disk_File_Report_Completed.exists(timeout=0.5):
				printWithFlush("DRC complete")
				break
		except pywintypes.error:
			pass
		except pywinauto.timings.TimeoutError:
			pass

	# Close the DRC completion dialog
	app.Disk_File_Report_Completed.wait("exists", timeout = 5)
	app.Disk_File_Report_Completed.close()

	# Now we can close the DRC window
	app.Drc_Control.close()

	# and close the main application. If pcbnew shows the 'do you want to save your changes' dialog, this will time out,
	# so hit 'exit without save' and try again if we see a timeout. Also, sometimes we may see an assertion failure related
	# to opengl, so cancel that too if we see it:
	printWithFlush("closing pcbnew..")
	retryClose = True
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
	errorstatus = 0
	with open(os.getcwd() + "\\report.txt", "r") as f:
		drclines = f.readlines()
		errorstatuslines = filter(lambda x: x.find("** Found ") == 0, drclines)
		errorcounts = map(lambda x: int(x.split()[2]), errorstatuslines)
		if len(errorcounts) != 2:
			printWithFlush("didn't find two '** Found' lines in report")
			errorstatus = 1
		elif (errorcounts[0] != 0) | (errorcounts[1] != 0):
			errorstatus = 1
	
	# Store the result in our dict and we're done.
	return { 'filename': pcbfilefriendlyname, 'errorStatus': errorstatus, 'drclines': drclines }

if __name__ == "__main__":
	main()

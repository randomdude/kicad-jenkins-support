import pywinauto
import pywintypes
import os
import sys
import time

print "Starting pcbnew"
app = pywinauto.application.Application().start("c:\\Program Files\\KiCad\\bin\\pcbnew.exe")

print "Awaiting main window"
while True:
	try:
		app.top_window().wait("exists", timeout = 5)

		# If pcbnew is already running, hit 'yes' to the confirmation dialog that asks if we want to start another instance.
		if app.top_window().child_window(best_match="pcbnew is already running").exists():
			app.top_window().Yes.click();
			app.top_window().wait("exists", timeout = 5)
			continue

		break

	except RuntimeError:
		pass

print "Opening file"
app.Pcbnew.menu_select("File->Open")

app.OpenBoardFile.type_keys(os.getcwd() + "\\atxbreakout.kicad_pcb", with_spaces = True)
app.OpenBoardFile.Open.click()

while True:
	try:
		if app.OpenBoardFile.exists(timeout=None, retry_interval=None):
			print 'Retying file open dialog completion'
			app.OpenBoardFile.Open.click()
			continue
		else:
			break
	except Exception as e:
		print e
		continue

print "Open complete"

while True:
	try:
		mainWindow = filter(lambda x: (x.window_text().find("Pcbnew") ==0), app.windows())
		if len(mainWindow) != 1:
			raise Exception()
		mainWindow = mainWindow[0]
		break
	except AttributeError:
		print "Waiting for load to complete"
		time.sleep(1)
		continue
	except pywinauto.controls.hwndwrapper.InvalidWindowHandle:
		print "Waiting for load to complete"
		time.sleep(1)
		continue

print "File load complete, waiting for DRC menu to be enabled"

while True:
	try:
		try:
			mainWindow.menu_select("Tools->DRC")
		except pywinauto.MatchError:
			mainWindow.menu_select("Inspect->Design Rules Checker")
		break
	except pywinauto.base_wrapper.ElementNotEnabled:
		time.sleep(1)
		print 'Waiting for menu option to be enabled'


print "Waiting for DRC window to appear"
while True: 
	try:
		if app.Drc_Control.exists(timeout=1, retry_interval=None):
			break
	except pywintypes.error:
		pass


print "setting DRC window options"
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
					print "retrying checkbox checking"
					continue
		break
	except pywintypes.error:
		pass

reportFileBox.type_keys(os.getcwd() + "\\report.txt")

# And start the DRC.
print "Doing DRC"
app.Drc_Control.Start_DRC.click()

# Wait for, and accept, the 'are you sure you want to refill the copper zones' dialog
app.Confirmation.wait("exists")
app.Confirmation.yes.click()

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
while True:
	try:
		app.wxWidgetsDebugAlert.wait("exists")
		app.wxWidgetsDebugAlert.No.click()
		break
	except pywintypes.error:
		continue
	except pywinauto.timings.TimeoutError:
		# No assert failure happened. yay.
		break

# Wait for DRC to complete, and then close the completion dialog
app.Disk_File_Report_Completed.wait("exists")
print "DRC complete"
app.Disk_File_Report_Completed.close()

# Now we can close the DRC window
app.Drc_Control.close()

# and close the main application. If pcbnew shows the 'do you want to save your changes' dialog, this will time out,
# so hit 'exit without save' and try again if we see a timeout. Also, sometimes we may see an assertion failure related
# to opengl, so cancel that too if we see it:
print "closing pcbnew.."
retryClose = True
while app.is_process_running():
	try:
		if retryClose:
			retryClose = False
			mainWindow.close(wait_time = 1)
	except pywinauto.timings.TimeoutError:
		try:
			if app.Dialog0.ExitWithoutSave.exists():
				print "Closing 'save changes' dialog"
				app.Dialog0.ExitWithoutSave.click()
				continue
			elif app.wxWidgetsDebugAlert.exists():
				print "Closing 'assertion failure' dialog"
				print app.wxWidgetsDebugAlert.dump_tree()
				app.wxWidgetsDebugAlert.Yes.click()
				continue
			else:
				raise
		except Exception as e:
			print "Exception - " + str(e)


# Now read the DRC report, and return non-zero if any errors were detected.
errorstatus = 0
with open(os.getcwd() + "\\report.txt", "r") as f:
	drclines = f.readlines()
	errorstatuslines = filter(lambda x: x.find("** Found ") == 0, drclines)
	errorcounts = filter(lambda x: int(x.split()[2]), errorstatuslines)
	if len(errorcounts) != 2:
		print "didn't find two '** Found' lines in report"
		errorstatus = 1
	elif (errorcounts[0] != 0) | (errorcounts[1] != 0):
		errorstatus = 1

print "Return status: %d" % errorstatus
sys.exit(errorstatus)

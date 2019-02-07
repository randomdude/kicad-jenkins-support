import pywinauto
import os
from pywinauto.application import Application
import time

app = Application().start("c:\Program Files\KiCad\\bin\pcbnew.exe")

app.Pcbnew.menu_select("File->Open")

app.OpenBoardFile.type_keys(os.cwd + "\\atxbreakout.kicad_pcb", with_spaces = True)
#time.sleep(0.1)
app.OpenBoardFile.Open.click()

while True:
	try:
		if app.OpenBoardFile.exists(timeout=None, retry_interval=None):
#			time.sleep(1)
			print 'Retying file open dialog completion'
			app.OpenBoardFile.Open.click()
			continue
		else:
			break
	except pywintypes.error as e:
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
	except pywinauto.controls.hwndwrapper.InvalidWindowHandle, AttributeError:
		print "Waiting for load to complete"
		time.sleep(1)
		continue

while True:
	try:
		mainWindow.menu_select("Tools->DRC")
		break
	except pywinauto.base_wrapper.ElementNotEnabled:
		time.sleep(1)
		print 'Waiting for menu option to be enabled'

try:
	app.Drc_Control.child_window(best_match="Min uVia sizeEdit2").type_keys("C:\\code\\atxbreakout\\report.txt")
except pywinauto.base_wrapper.ElementNotEnabled:
	# Enable the saving of reports and try again
	app.Drc_Control.child_window(best_match="Create Report FileCheckBox").click()
	app.Drc_Control.child_window(best_match="Min uVia sizeEdit2").type_keys("C:\\code\\atxbreakout\\report.txt")

#app.Drc_Control.child_window(best_match="Enter the report filename").Save.click()
app.Drc_Control.Start_DRC.click()

app.Disk_File_Report_Completed.close()
app.Drc_Control.close()
try:
	mainWindow.close()
except pywinauto.timings.TimeoutError:
	if app.Dialog0.ExitWithoutSave.exists():
		app.Dialog0.ExitWithoutSave.click()
	mainWindow.close()

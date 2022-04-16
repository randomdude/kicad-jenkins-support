from pathlib import Path

import pcbnew
import shutil
import os
import glob

for boardfile in Path(".").rglob("*.kicad_pcb"):
	if boardfile.is_dir():
		continue

	board = pcbnew.LoadBoard(str(boardfile.absolute()))
	outputFilename = os.path.join(os.path.abspath('.'), f"gerbers_{os.path.basename(str(boardfile.name))}")
	print(f"Exporting board {boardfile.name}..")

	tempDir = os.path.join(os.path.abspath('.'), "generated")
	if Path(tempDir).exists():
		shutil.rmtree(tempDir)
	os.mkdir(tempDir)

	# Ensure all zones are filled before going any further
	filler = pcbnew.ZONE_FILLER(board)
	zones = board.Zones()
	filler.Fill(zones)

	pc = pcbnew.PLOT_CONTROLLER(board)
	po = pc.GetPlotOptions()

	po.SetPlotFrameRef(False)
	po.SetUseGerberProtelExtensions(True)
	po.SetExcludeEdgeLayer(True)
	po.SetUseGerberAttributes(False)
	po.SetDrillMarksType(pcbnew.PCB_PLOT_PARAMS.NO_DRILL_SHAPE)
	po.SetOutputDirectory(tempDir)

	layersToPlot = [  
		(pcbnew.F_Cu, "F_Cu", "-F.Cu.gtl"),
		(pcbnew.B_Cu, "B_Cu", "-B.Cu.gbl"),
		(pcbnew.B_Mask, "B_Mask", "-B.Mask.gbs"),
		(pcbnew.F_Mask, "F_Mask", "-F.Mask.gts"),
		(pcbnew.B_SilkS, "B_SilkS", "-B.SilkS.gbo"),
		(pcbnew.F_SilkS, "F_SilkS", "-F.SilkS.gto"),
		(pcbnew.Edge_Cuts, "Edge_Cuts", "-Edge.Cuts.gm1")
	]

	for layerInfo in layersToPlot:
		pc.SetLayer(layerInfo[0])
		pc.OpenPlotfile(layerInfo[1], pcbnew.PLOT_FORMAT_GERBER, "idk")
		plotFilename = pc.GetPlotFileName()
		pc.PlotLayer()
		pc.ClosePlot()

	# And then plot drills.
	drlwriter = pcbnew.EXCELLON_WRITER( board )

	drlwriter.SUPPRESS_LEADING = 2
	mirror = False
	minimalHeader = False
	offset = pcbnew.wxPoint(0,0)
	mergeNPTH = True
	drlwriter.SetOptions( mirror, minimalHeader, offset, mergeNPTH )

	metricFmt = True
	drlwriter.SetFormat( metricFmt, pcbnew.EXCELLON_WRITER.DECIMAL_FORMAT)

	genDrl = True
	genMap = False
	drlwriter.CreateDrillandMapFilesSet( tempDir, genDrl, genMap )

	print("Exported OK. Zipping..")
	shutil.make_archive(outputFilename, 'zip', tempDir)
	print("OK.")
	shutil.rmtree(tempDir)

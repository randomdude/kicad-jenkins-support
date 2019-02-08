import pcbnew
import shutil
import os
import glob

for boardfile in glob.glob("*.kicad_pcb"):

	board = pcbnew.LoadBoard(boardfile)

	pc = pcbnew.PLOT_CONTROLLER(board)
	po = pc.GetPlotOptions()

	po.SetPlotFrameRef(False)
	po.SetUseGerberProtelExtensions(True)
	po.SetExcludeEdgeLayer(True)
	po.SetUseGerberAttributes(False)
	po.SetLineWidth(100000)
	po.SetDrillMarksType(pcbnew.PCB_PLOT_PARAMS.NO_DRILL_SHAPE)
	po.SetOutputDirectory("generated")

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
	drlwriter.CreateDrillandMapFilesSet( "generated", genDrl, genMap );


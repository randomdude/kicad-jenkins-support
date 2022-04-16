from pathlib import Path

import pcbnew
import shutil
import os
import glob
from svg_processor import SvgProcessor

# Some of this stuff is taken from https://github.com/scottbez1/splitflap/tree/580a11538d801041cedf59a3c5d1c91b5f56825d/electronics
# The idea is to export each layer to an SVG, then change the colour of each, and finally
# combine them all into one layer. This is because KiCad won't change colours on svg export.

for boardfile in Path(".").rglob("*.kicad_pcb"):
	board = pcbnew.LoadBoard(str(boardfile.absolute()))
	svgfilename = boardfile.name + ".svg"

	# Ensure all zones are filled before going any further
	filler = pcbnew.ZONE_FILLER(board)
	zones = board.Zones()
	filler.Fill(zones)

	pc = pcbnew.PLOT_CONTROLLER(board)
	po = pc.GetPlotOptions()
	po.SetPlotFrameRef(False)

	# todo: clean up string literals
	layers = [
		(pcbnew.B_Cu		, "B_Cu"   		, "#4d7fc4", "0.666"),
		(pcbnew.F_Cu		, "F_Cu"   		, "#c83434", "0.5"),
		(pcbnew.F_SilkS		, "F.SilkS"		, "#f2eda1", "0.8"),
		(pcbnew.B_SilkS		, "B.SilkS"		, "#e8b2a7", "0.8"),
		(pcbnew.F_Fab		, "F.Fab"  		, "#afafaf", "0.8"),
		(pcbnew.B_Fab		, "B.Fab"  		, "#585d84", "0.8"),
		(pcbnew.Edge_Cuts	, "Edge_Cuts"	, "#d0d2cd", "1.0"),
	]

	processed_svg_files = []

	# Plot each layer, in turn, to a temporary file, and then change the colour of the
	# generated svg.
	for a in layers:
		pc.SetLayer(a[0])
		pc.OpenPlotfile(f"layer_ {a[1]}", pcbnew.PLOT_FORMAT_SVG, "idk")
		layerFilename = pc.GetPlotFileName()
		pc.PlotLayer()
		pc.ClosePlot()

		processor = SvgProcessor(layerFilename)
		def colorize(original):
				if original.lower() == '#000000':
					return a[2]
				return original
		processor.apply_color_transform(colorize)
		processor.wrap_with_group({
				'opacity': a[3],
		})

		processed_svg_files.append((processor, layerFilename))

	# Finally, combine all the layers together.
	shutil.copyfile(layerFilename, svgfilename)
	output_processor = SvgProcessor(svgfilename)
	output_processor.remove_content()
	for processor, _ in processed_svg_files:
		output_processor.import_groups(processor)
	output_processor.write(svgfilename)

	# The only thing left to do is to remove all those temporary files.
	for _, filename in processed_svg_files:
		os.remove(filename)

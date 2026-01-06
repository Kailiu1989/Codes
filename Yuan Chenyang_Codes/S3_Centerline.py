# -*- coding: utf-8 -*-
import arcpy
from arcpy.sa import *
import os


def process_Centerline(base_path):
    # Set up the environment
    arcpy.env.workspace = base_path
    arcpy.CheckOutExtension("Spatial")
    arcpy.env.XYTolerance = "0.0001 Meters"
    arcpy.env.scratchWorkspace = r"D:\LargeDiskSpace"  # Set temporary workspace with sufficient storage
    arcpy.env.tileSize = "4096 4096"  # Set a larger tile size
    arcpy.env.parallelProcessingFactor = "100%"  # Use all CPU cores

    # Define input and output paths
    input_feature = os.path.join(base_path, "River_Break.shp")
    output_raster = os.path.join(base_path, "euclidean_allocation.tif")
    clip_feature = os.path.join(base_path, "Final_Vector_Clean.shp")

    # Define processing parameters
    cell_size = 0.0003  # Raster cell size

    # Perform Euclidean allocation
    allocation_raster = EucAllocation(input_feature, cell_size=cell_size)

    # Save the output raster
    allocation_raster.save(output_raster)
    print("Euclidean allocation raster created with cell size:", cell_size)

    # Convert raster to polygon
    polygon_output = os.path.join(base_path, "allocation_polygon.shp")
    arcpy.RasterToPolygon_conversion(output_raster, polygon_output, "NO_SIMPLIFY")

    # Convert polygon to polyline
    line_output = os.path.join(base_path, "allocation_line.shp")
    arcpy.PolygonToLine_management(polygon_output, line_output)

    # Clip the lines using the clip feature
    clipped_line_output = os.path.join(base_path, "clipped_centerline.shp")
    arcpy.Clip_analysis(line_output, clip_feature, clipped_line_output)

    print("Clipped centerline created based on input shapefile.")

    # Delete intermediate files no longer needed
    # arcpy.Delete_management(output_raster)
    arcpy.Delete_management(polygon_output)
    arcpy.Delete_management(line_output)

# Example usage:
# process_Centerline(r'D:\WorkContent\Channel shift\test\2023')

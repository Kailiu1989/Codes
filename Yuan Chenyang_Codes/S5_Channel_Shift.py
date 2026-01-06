# -*- coding: utf-8 -*-
import arcpy
import os


def analyze_Channel_Shift(base_path, past, now, river_name, name):
    base_path_cf = os.path.join(base_path, "channel shift")
    base_past = os.path.join(base_path, str(past))
    base_now = os.path.join(base_path, str(now))
    arcpy.env.XYTolerance = "0.001 Meters"
    arcpy.env.workspace = base_path_cf

    # Define centerline file paths
    centerline_1970 = os.path.join(base_past, river_name)
    centerline_recent = os.path.join(base_now, river_name)
    output_intersection = 'Intersection.shp'
    arcpy.Intersect_analysis([centerline_1970, centerline_recent], output_intersection, "ALL", "", "POINT")

    split_lines_1970 = 'Split_Centerline_1970.shp'
    split_lines_recent = 'Split_Centerline_Recent.shp'
    arcpy.SplitLineAtPoint_management(centerline_1970, output_intersection, split_lines_1970, "0.01 Meters")
    arcpy.SplitLineAtPoint_management(centerline_recent, output_intersection, split_lines_recent, "0.01 Meters")

    output_polygons = 'Enclosed_Areas.shp'
    arcpy.FeatureToPolygon_management([split_lines_1970, split_lines_recent], output_polygons)

    river_1970 = os.path.join(base_past, "Final_Vector_Clean.shp")
    river_recent = os.path.join(base_now, "Final_Vector_Clean.shp")
    arcpy.RepairGeometry_management(river_1970)
    arcpy.RepairGeometry_management(river_recent)
    union_output = 'Rivers_Union.shp'
    arcpy.Union_analysis([river_1970, river_recent], union_output)

    erase_output = 'Erase_Output.shp'
    arcpy.Erase_analysis(output_polygons, union_output, erase_output)

    arcpy.AddField_management(erase_output, "AREA_SQM", "DOUBLE")
    arcpy.CalculateField_management(erase_output, "AREA_SQM", "!shape.area!", "PYTHON3")

    # Set area threshold filter
    total_area = sum([row[0] for row in arcpy.da.SearchCursor(erase_output, ["AREA_SQM"])])
    threshold_area = total_area * 0.001
    significant_areas = name
    expression = f"\"AREA_SQM\" > {threshold_area}"
    arcpy.Select_analysis(erase_output, significant_areas, expression)

    # Clean up temporary files
    arcpy.Delete_management(output_intersection)
    arcpy.Delete_management(split_lines_1970)
    arcpy.Delete_management(split_lines_recent)
    arcpy.Delete_management(output_polygons)
    arcpy.Delete_management(union_output)
    arcpy.Delete_management(erase_output)

    print("River change analysis completed and results are saved.")

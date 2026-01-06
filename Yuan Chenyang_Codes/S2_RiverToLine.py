# -*- coding: utf-8 -*-

import arcpy
import os


def process_river_toline(base_path):
    arcpy.env.workspace = base_path
    input_river_polygon = os.path.join(base_path, "Final_Vector_Clean.shp")
    river_break = os.path.join(base_path, "River_Break.shp")

    # Ensure the output river bank feature class exists and add a field to distinguish left and right banks
    if not arcpy.Exists(river_break):
        arcpy.CreateFeatureclass_management(
            out_path=base_path,
            out_name='River_Break.shp',
            geometry_type='POLYLINE',
            template=None,
            spatial_reference=arcpy.Describe(input_river_polygon).spatialReference)
        arcpy.AddField_management(river_break, "Bank", "TEXT")

    # Iterate through each polygon feature, create a buffer, extract the outline, and split into banks
    with arcpy.da.SearchCursor(input_river_polygon, ["SHAPE@"]) as polygon_cursor:
        for polygon_row in polygon_cursor:
            # Create a 1-meter buffer around the polygon
            buffered_polygon = arcpy.Buffer_analysis(
                polygon_row[0], arcpy.Geometry(), "1 Meters", "FULL", "ROUND", "NONE")

            # Convert the buffer polygon to its outline polyline
            temp_outline = arcpy.PolygonToLine_management(buffered_polygon[0], arcpy.Geometry())

            bank_lines = {'Left': None, 'Right': None}
            bank_lengths = {'Left': 0, 'Right': 0}

            for line in temp_outline:
                if line and line.pointCount > 2:
                    points = [point for part in line for point in part]
                    # Identify the westernmost, easternmost, southernmost, and northernmost points
                    west_most_point = min(points, key=lambda p: p.X)
                    east_most_point = max(points, key=lambda p: p.X)
                    south_most_point = min(points, key=lambda p: p.Y)
                    north_most_point = max(points, key=lambda p: p.Y)

                    # Determine the primary flow direction of the river
                    if abs(east_most_point.X - west_most_point.X) >= abs(north_most_point.Y - south_most_point.Y):
                        min_point, max_point = west_most_point, east_most_point
                    else:
                        min_point, max_point = south_most_point, north_most_point

                    min_index = points.index(min_point)
                    max_index = points.index(max_point)

                    if min_index <= max_index:
                        left_points = points[min_index:max_index + 1]
                        right_points = points[max_index:] + points[:min_index + 1]
                    else:
                        left_points = points[max_index:min_index + 1]
                        right_points = points[min_index:] + points[:max_index + 1]

                    # Create polyline geometries for left and right banks
                    left_line = arcpy.Polyline(arcpy.Array(left_points), line.spatialReference)
                    right_line = arcpy.Polyline(arcpy.Array(right_points), line.spatialReference)

                    # Retain only the longest line for each bank
                    if left_line.length > bank_lengths['Left']:
                        bank_lines['Left'] = left_line
                        bank_lengths['Left'] = left_line.length
                    if right_line.length > bank_lengths['Right']:
                        bank_lines['Right'] = right_line
                        bank_lengths['Right'] = right_line.length

            # Insert the longest left and right bank lines into the river_break feature class
            with arcpy.da.InsertCursor(river_break, ["SHAPE@", "Bank"]) as river_cursor:
                if bank_lines['Left']:
                    river_cursor.insertRow([bank_lines['Left'], 'Left'])
                if bank_lines['Right']:
                    river_cursor.insertRow([bank_lines['Right'], 'Right'])

    print("Process completed")

# Example usage:
# process_river_toline(r'D:\WorkContent\Channel shift\test\2023')

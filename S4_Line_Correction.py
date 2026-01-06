# -*- coding: utf-8 -*-
import arcpy
import os

def connect_river_lines(base_path):
    arcpy.env.workspace = base_path
    arcpy.env.overwriteOutput = True

    # Path to the input line feature class (create a temporary copy to protect the original file)
    input_line_feature = os.path.join(base_path, "clipped_centerline.shp")
    temp_line_feature = os.path.join(base_path, "temp_clipped_centerline.shp")
    projected_line_feature = os.path.join(base_path, "projected_temp_clipped_centerline.shp")
    arcpy.CopyFeatures_management(input_line_feature, temp_line_feature)
    print("Created temporary copy of the input line feature.")

    # Set projection to Albers Equal Area Conic
    albers_projection = arcpy.SpatialReference("North America Albers Equal Area Conic")
    arcpy.Project_management(temp_line_feature, projected_line_feature, albers_projection)
    print("Projected the temporary line feature to Albers Equal Area Conic projection.")

    # Extract endpoints of all line features
    endpoints = os.path.join(base_path, "endpoints.shp")
    arcpy.FeatureVerticesToPoints_management(projected_line_feature, endpoints, "BOTH_ENDS")
    print("Extracted endpoints of all lines.")

    # Use topology to identify isolated endpoints, keeping only breakpoints
    arcpy.MakeFeatureLayer_management(endpoints, "endpoints_layer")
    arcpy.SelectLayerByLocation_management("endpoints_layer", "BOUNDARY_TOUCHES", projected_line_feature, invert_spatial_relationship=True)
    isolated_points = os.path.join(base_path, "isolated_endpoints.shp")
    arcpy.CopyFeatures_management("endpoints_layer", isolated_points)
    print("Isolated endpoints identified as breakpoints.")

    # Create an empty polyline feature class to store connection lines and add a length field
    connection_lines = os.path.join(base_path, "temp_connections.shp")
    arcpy.CreateFeatureclass_management(base_path, "temp_connections.shp", "POLYLINE",
                                        spatial_reference=projected_line_feature)
    arcpy.AddField_management(connection_lines, "Length", "DOUBLE")
    print("Created temporary connection lines feature class.")

    # Use a cursor to read endpoints, compute the shortest connecting lines, and store them
    points = [row[0] for row in arcpy.da.SearchCursor(isolated_points, ["SHAPE@XY"])]
    while len(points) > 1:
        min_distance = float('inf')
        closest_pair = None
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                dist = ((points[i][0] - points[j][0]) ** 2 + (points[i][1] - points[j][1]) ** 2) ** 0.5
                if dist < min_distance:
                    min_distance = dist
                    closest_pair = (points[i], points[j])

        # If a suitable pair of points is found, create a connecting line
        if closest_pair and min_distance <= 100:  # Ensure the connection does not exceed 100 meters
            array = arcpy.Array([arcpy.Point(*closest_pair[0]), arcpy.Point(*closest_pair[1])])
            polyline = arcpy.Polyline(array)
            line_length = polyline.length  # Compute the length of the polyline

            # Check line length and insert if within the limit
            if line_length <= 100:
                with arcpy.da.InsertCursor(connection_lines, ["SHAPE@", "Length"]) as cursor:
                    cursor.insertRow([polyline, line_length])

            # Remove the points that have been connected
            points.remove(closest_pair[0])
            points.remove(closest_pair[1])
        else:
            break  # If no more connectable point pairs are found, terminate the loop

    print("Completed connecting closest breakpoints with lines.")

    # Merge the original line features and the newly created connection lines
    output_line_feature = os.path.join(base_path, "Connected_River.shp")
    arcpy.Merge_management([projected_line_feature, connection_lines], output_line_feature)
    print("Merged original lines and connection lines.")

    # Clean up temporary files
    arcpy.Delete_management(endpoints)
    arcpy.Delete_management(connection_lines)
    arcpy.Delete_management(isolated_points)
    arcpy.Delete_management(temp_line_feature)
    arcpy.Delete_management(projected_line_feature)
    print("Cleaned up temporary files.")

    print("All lines have been connected and merged into:", output_line_feature)

# Example usage:
# connect_river_lines(r'D:\WorkContent\Channel shift\test\2023')

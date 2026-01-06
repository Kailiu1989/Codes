# -*- coding: utf-8 -*-

import arcpy
from arcpy.sa import *
import os

def preprocess_rivers(base_path, input_shp_name):
    arcpy.env.workspace = base_path  # Set the workspace environment
    arcpy.env.overwriteOutput = True

    input_vector_path = os.path.join(base_path, input_shp_name)
    buffered_path = os.path.join(base_path, "Buffered_Rivers.shp")
    output_vector_clean_path = os.path.join(base_path, "Final_Vector_Clean.shp")

    # Ensure the Spatial Analyst extension is available
    arcpy.CheckOutExtension("Spatial")

    # Add an area field
    arcpy.management.AddField(input_vector_path, "AREA_SQM", "DOUBLE")

    # Calculate area for each feature
    arcpy.management.CalculateField(input_vector_path, "AREA_SQM", "!shape.area!", "PYTHON_9.3")

    # Compute total area of all features
    total_area = 0
    with arcpy.da.SearchCursor(input_vector_path, ["AREA_SQM"]) as cursor:
        for row in cursor:
            total_area += row[0]

    # Compute threshold as 0.5% of total area
    threshold_area = total_area * 0.005

    # Build selection expression: features with area greater than threshold
    expression = f"AREA_SQM > {threshold_area}"

    # Remove existing temporary layer if present
    if arcpy.Exists("lyr"):
        arcpy.management.Delete("lyr")

    arcpy.management.MakeFeatureLayer(input_vector_path, "lyr")
    arcpy.management.SelectLayerByAttribute("lyr", "NEW_SELECTION", expression)

    # Create buffer of 1 meter around selected features
    arcpy.Buffer_analysis("lyr", buffered_path, "1 Meters", "FULL", "ROUND", "NONE")

    # Use EliminatePolygonPart to remove polygon parts smaller than 50% or 0.5% of total area
    arcpy.EliminatePolygonPart_management(
        in_features=buffered_path,
        out_feature_class=output_vector_clean_path,
        condition="AREA_OR_PERCENT",
        part_area_percent="50",
        part_area="0.005",
        part_option="ANY"
    )

    # Save the cleaned features
    arcpy.management.CopyFeatures("lyr", output_vector_clean_path)

    print("All operations completed. Results saved to:", output_vector_clean_path)

    # Clean up temporary layers
    arcpy.Delete_management("lyr")
    arcpy.Delete_management(buffered_path)

# Example usage:
# preprocess_rivers(r"D:\WorkContent\Channel shift\Missibi\GSW_Ununion", "Missibi_1980s.shp")

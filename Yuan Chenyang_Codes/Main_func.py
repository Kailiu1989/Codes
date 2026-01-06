# -*- coding: utf-8 -*-
########################################################################################
import arcpy
from arcpy.sa import *
import os
########################################################################################
# Function imports
from Func.S1_ProProcessing import preprocess_rivers
from Func.S2_RiverToLine import process_river_toline
from Func.S3_Centerline import process_Centerline
from Func.S4_Line_Correction import connect_river_lines
from Func.S5_Channel_Shift import analyze_Channel_Shift

from Para_Cal.P1_Point_DisTance import analyze_channel_shift_Point_Dis
from Para_Cal.P2_Avg_Shift import analyze_channel_shift_AvgLen
from Para_Cal.P3_Shift_Area import analyze_channel_shift_Area
from Para_Cal.P4_Curvature_of_Area import analyze_channel_shift_curvature
from Para_Cal.P5_River_Width import analyze_River_Width
from Para_Cal.P6_Meander_Ratio import analyze_channel_shift_Metrics
########################################################################################
# Parameter settings

base = r"H:\Figure2\Red River shapefile\Buffer"
base_path = os.path.join(base, "Time2")
input_shp_name = "River Time 2.shp"

past = "Time1"

recent = "Time2"

river_name = "clipped_centerline.shp"
name = 'Significant_Areas.shp'
flag = 2

########################################################################################
if flag == 1:
    preprocess_rivers(base_path, input_shp_name)  # Data preprocessing

    process_river_toline(base_path)  # Convert river polygon features to polyline

    process_Centerline(base_path)  # Generate centerlines

    # connect_river_lines(base_path)  # Optional: connect centerlines to reduce breaks
if flag == 2:
    analyze_Channel_Shift(base, past, recent, river_name, name)

if flag == 3:
    # Channel Shift area intersection point distances
    Point_Dis = analyze_channel_shift_Point_Dis(base, past, recent, river_name, name)
    print("Distances between significant areas and intersection points:", Point_Dis)
    print("Number of distances calculated:", len(Point_Dis))

    # Channel Shift area average displacement distances
    avg_distance = analyze_channel_shift_AvgLen(base, past, recent, river_name, name)
    print("Average distances for all areas:", avg_distance)
    print("Number of distances calculated:", len(avg_distance))

    # Channel Shift area sizes
    areas = analyze_channel_shift_Area(base, past, recent, river_name, name)
    print("Areas for all areas:", areas)
    print("Number of areas calculated:", len(areas))

    # Channel Shift area centerline curvature
    curvature_ratios = analyze_channel_shift_curvature(base, past, recent, river_name, name)
    print("Calculated curvature ratios for intersected areas:", curvature_ratios)
    print("Number of curvature calculated:", len(curvature_ratios))

    # River width calculation
    area, total_length_m, average_width = analyze_River_Width(base, past, river_name)
    print(f"Area: {area:.2f} square meters")
    print(f"Clipped centerline length: {total_length_m:.2f} meters")
    print(f"Average width: {average_width:.2f} meters")

    # River meander ratio calculation
    curvature_radii, meander_ratios = analyze_channel_shift_Metrics(base, past, recent, river_name, name)
    # Print results
    print("Calculated curvature radii:", curvature_radii)
    print("Calculated meander ratios:", meander_ratios)
    print("Number of curvature radii:", len(curvature_radii))
    print("Number of meander ratios:", len(meander_ratios))

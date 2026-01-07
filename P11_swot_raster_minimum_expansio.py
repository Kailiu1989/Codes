# -*- coding: utf-8 -*-
import os
import arcpy


def P11_Process_rasters_with_max(path4):
    # Define input and output paths
    one_to_one_folder = os.path.join(path4, '04_Aligned_tifs')
    max_tif_path = os.path.join(path4, '05_Max_Tif_1', 'max_valid_pixel_range_Clip.tif')
    final_one_folder = os.path.join(path4, '06_Expanded_tifs')

    # Create the output folder if it does not exist
    if not os.path.exists(final_one_folder):
        os.makedirs(final_one_folder)

    # Traverse all TIFF files in the aligned raster directory
    for root, _, files in os.walk(one_to_one_folder):
        for file in files:
            if file.endswith('.tif'):
                tif_path = os.path.join(root, file)

                # Construct output raster path
                output_tif = os.path.join(final_one_folder, file)

                # Delete existing output raster with the same name
                if arcpy.Exists(output_tif):
                    arcpy.management.Delete(output_tif)

                # Mosaic the input raster and the max-valid-pixel raster
                arcpy.management.MosaicToNewRaster(
                    [tif_path, max_tif_path],      # Input raster list
                    final_one_folder,              # Output workspace
                    file,                          # Output raster name
                    pixel_type="32_BIT_FLOAT",     # Output pixel type
                    number_of_bands=1,             # Number of bands
                    mosaic_method="MINIMUM",       # Mosaic rule: minimum value
                    mosaic_colormap_mode="First"   # Colormap handling mode
                )

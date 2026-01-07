# -*- coding: utf-8 -*-
import os
import numpy as np
import rasterio
import arcpy

def P8_generate_maximum_valid_wse_extent(path4):
    """
    Process TIFF files by removing NoData values, mosaicking rasters,
    and generating a maximum valid pixel extent raster.

    Parameters:
    path4 (str): Root directory containing the TIFF files.
    """
    use_tif_folder = os.path.join(path4, '02_Extract_Tifs')
    max_tif_folder = os.path.join(path4, '03_Max_Tif')

    if not os.path.exists(max_tif_folder):
        os.makedirs(max_tif_folder)
    # Get all tif files in the Use_Tif folder
    tif_files = [f for f in os.listdir(use_tif_folder) if f.lower().endswith('.tif')]

    rasters = []
    valid_pixel_counts = []
    invalid_tif_files = []

    nodata_values = set()

    total_tif_files = len(tif_files)  # Total number of TIFF files
    valid_tif_count = 0  # Number of TIFF files with valid pixels
    invalid_tif_count = 0  # Number of TIFF files without valid pixels

    for tif_file in tif_files:
        tif_path = os.path.join(use_tif_folder, tif_file)

        with rasterio.open(tif_path) as src:
            data = src.read(1).astype(float)  # Read first band and convert to float
            nodata_value = src.nodata  # Get NoData value

            nodata_values.add(nodata_value)

            # Remove NoData values and NaN
            if nodata_value is not None:
                data[data == nodata_value] = np.nan
            data = data[np.isfinite(data)]  # Remove NaN or invalid values

            # Count valid pixels
            valid_pixel_count = len(data)
            valid_pixel_counts.append(valid_pixel_count)

            if valid_pixel_count > 0:
                valid_tif_count += 1  # File contains valid pixels
            else:
                invalid_tif_count += 1  # File contains no valid pixels

            # If no valid pixels exist, mark as invalid file
            if valid_pixel_count == 0:
                invalid_tif_files.append(tif_path)
                continue

            # Save valid data to a new raster
            temp_no_data_removed = os.path.join(max_tif_folder, f'no_data_removed_{tif_file}')
            with rasterio.open(tif_path) as src:
                profile = src.profile
                profile.update(dtype=rasterio.float32, nodata=nodata_value)
                with rasterio.open(temp_no_data_removed, 'w', **profile) as dst:
                    # Fill NoData values
                    new_data = np.copy(src.read(1).astype(float))
                    new_data[np.isnan(new_data)] = nodata_value
                    dst.write(new_data, 1)

            rasters.append(temp_no_data_removed)

    # Mosaic all processed TIFF files into Mosaic_All.tif
    mosaic_tif_path = os.path.join(max_tif_folder, 'Mosaic_All.tif')

    # Use arcpy to mosaic to a new raster
    arcpy.MosaicToNewRaster_management(
        rasters,
        max_tif_folder,
        'Mosaic_All.tif',
        pixel_type="32_BIT_FLOAT",
        number_of_bands=1,
        mosaic_method="MAXIMUM",
        mosaic_colormap_mode="FIRST"
    )

    # Use Raster Calculator to generate maximum extent
    # Set pixels with values to 99999, and NoData pixels to 0
    max_tif_path = os.path.join(max_tif_folder, 'max_valid_pixel_range.tif')
    if arcpy.Exists(max_tif_path):
        arcpy.Delete_management(max_tif_path)

    calc_expression = f"Con(IsNull(\"{mosaic_tif_path}\"), 0, 99999)"
    arcpy.gp.RasterCalculator_sa(calc_expression, max_tif_path)

    # Further use SetNull to set pixels with value 0 to NoData
    max_tif_path_clip = os.path.join(max_tif_folder, 'max_valid_pixel_range_Clip.tif')
    if arcpy.Exists(max_tif_path_clip):
        arcpy.Delete_management(max_tif_path_clip)

    clip_expression = f"SetNull(\"{max_tif_path}\" == 0, \"{max_tif_path}\")"
    arcpy.gp.RasterCalculator_sa(clip_expression, max_tif_path_clip)

    # Count valid pixels in the clipped TIFF file
    max_valid_pixel_count = 0
    with rasterio.open(max_tif_path_clip) as src:
        data = src.read(1).astype(float)
        nodata_value = src.nodata
        if nodata_value is not None:
            data[data == nodata_value] = np.nan
        data = data[np.isfinite(data)]
        max_valid_pixel_count = np.sum(data == 1)

    # Delete TIFF files with zero valid pixels and related files
    for tif_path in invalid_tif_files:
        os.remove(tif_path)

        # Delete related auxiliary files (e.g., .tfw, .aux, .xml, etc.)
        related_extensions = ['.tfw', '.aux', '.xml', '.tif.xml', '.tif.ovr']
        for ext in related_extensions:
            related_file = tif_path.replace('.tif', ext)
            if os.path.exists(related_file):
                os.remove(related_file)

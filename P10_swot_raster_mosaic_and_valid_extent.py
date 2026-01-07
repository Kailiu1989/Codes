# -*- coding: utf-8 -*-
import os
import numpy as np
import rasterio
import arcpy


def P10_Merged_All_SWOT(path4):
    """
    Process TIFF files by removing NoData values, mosaicking rasters,
    and generating the maximum valid pixel extent raster.

    Parameters
    ----------
    path4 : str
        Root directory containing the input TIFF files.
    """
    use_tif_folder = os.path.join(path4, '04_Aligned_tifs')
    max_tif_folder = os.path.join(path4, '05_Max_Tif_1')

    if not os.path.exists(max_tif_folder):
        os.makedirs(max_tif_folder)

    # Retrieve all TIFF files from the aligned raster folder
    tif_files = [f for f in os.listdir(use_tif_folder) if f.lower().endswith('.tif')]

    rasters = []
    valid_pixel_counts = []
    invalid_tif_files = []

    nodata_values = set()

    total_tif_files = len(tif_files)      # Total number of TIFF files
    valid_tif_count = 0                   # Number of TIFF files with valid pixels
    invalid_tif_count = 0                 # Number of TIFF files without valid pixels

    for tif_file in tif_files:
        tif_path = os.path.join(use_tif_folder, tif_file)

        with rasterio.open(tif_path) as src:
            data = src.read(1).astype(float)   # Read the first band as float
            nodata_value = src.nodata          # Retrieve NoData value

            nodata_values.add(nodata_value)

            # Remove NoData values and NaNs
            if nodata_value is not None:
                data[data == nodata_value] = np.nan
            data = data[np.isfinite(data)]

            # Count valid pixels
            valid_pixel_count = len(data)
            valid_pixel_counts.append(valid_pixel_count)

            if valid_pixel_count > 0:
                valid_tif_count += 1
            else:
                invalid_tif_count += 1

            # Mark files with zero valid pixels as invalid
            if valid_pixel_count == 0:
                invalid_tif_files.append(tif_path)
                continue

            # Save raster with NoData values preserved
            temp_no_data_removed = os.path.join(max_tif_folder, f'no_data_removed_{tif_file}')
            with rasterio.open(tif_path) as src:
                profile = src.profile
                profile.update(dtype=rasterio.float32, nodata=nodata_value)
                with rasterio.open(temp_no_data_removed, 'w', **profile) as dst:
                    new_data = np.copy(src.read(1).astype(float))
                    new_data[np.isnan(new_data)] = nodata_value
                    dst.write(new_data, 1)

            rasters.append(temp_no_data_removed)

    # Mosaic all processed TIFF files into a single raster
    mosaic_tif_path = os.path.join(max_tif_folder, 'Mosaic_All.tif')

    arcpy.MosaicToNewRaster_management(
        rasters,
        max_tif_folder,
        'Mosaic_All.tif',
        pixel_type="32_BIT_FLOAT",
        number_of_bands=1,
        mosaic_method="MAXIMUM",
        mosaic_colormap_mode="FIRST"
    )

    # Generate a raster indicating the maximum valid pixel extent
    max_tif_path = os.path.join(max_tif_folder, 'max_valid_pixel_range.tif')
    if arcpy.Exists(max_tif_path):
        arcpy.Delete_management(max_tif_path)

    # Raster calculator expression: valid pixels set to 99999, null pixels set to 0
    calc_expression = f"Con(IsNull(\"{mosaic_tif_path}\"), 0, 99999)"
    arcpy.gp.RasterCalculator_sa(calc_expression, max_tif_path)

    # Further clip the raster by setting zero values to NoData
    max_tif_path_clip = os.path.join(max_tif_folder, 'max_valid_pixel_range_Clip.tif')
    if arcpy.Exists(max_tif_path_clip):
        arcpy.Delete_management(max_tif_path_clip)

    # Set pixels with value 0 to NoData
    clip_expression = f"SetNull(\"{max_tif_path}\" == 0, \"{max_tif_path}\")"
    arcpy.gp.RasterCalculator_sa(clip_expression, max_tif_path_clip)

    # Count the number of valid pixels (value == 1) in the clipped raster
    max_valid_pixel_count = 0
    with rasterio.open(max_tif_path_clip) as src:
        data = src.read(1).astype(float)
        nodata_value = src.nodata
        if nodata_value is not None:
            data[data == nodata_value] = np.nan
        data = data[np.isfinite(data)]
        max_valid_pixel_count = np.sum(data == 1)

    # Remove TIFF files with zero valid pixels and their associated sidecar files
    for tif_path in invalid_tif_files:
        os.remove(tif_path)

        # Remove related auxiliary files (e.g., .tfw, .aux, .xml)
        related_extensions = ['.tfw', '.aux', '.xml', '.tif.xml', '.tif.ovr']
        for ext in related_extensions:
            related_file = tif_path.replace('.tif', ext)
            if os.path.exists(related_file):
                os.remove(related_file)

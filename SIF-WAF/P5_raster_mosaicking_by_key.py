# -*- coding: utf-8 -*-
import os
import shutil
import arcpy
from collections import defaultdict


def _parse_keys_from_filename(filename):
    """
    Parse temporal and spatial keys from a raster filename.

    Expected filename structure (underscore-separated):
    - Spatial key: parts[5] and parts[6]
    - Date key: first 8 digits of parts[8], formatted as YYYY_MM_DD

    Parameters
    ----------
    filename : str
        GeoTIFF filename.

    Returns
    -------
    tuple or None
        (date_key, spatial_key) if parsing is successful,
        None otherwise.
    """
    parts = filename.split("_")
    if len(parts) < 9:
        return None

    spatial_key = "_".join(parts[5:7])

    date_raw = parts[8][:8]
    if not date_raw.isdigit() or len(date_raw) != 8:
        return None

    date_key = f"{date_raw[:4]}_{date_raw[4:6]}_{date_raw[6:8]}"
    return date_key, spatial_key


def P5_mosaic_rasters_by_key(swot_root_dir):
    """
    Mosaic clipped WSE rasters by spatial key and harmonize filenames
    using a consistent temporal identifier.

    If multiple rasters share the same spatial key, they are mosaicked
    into a single raster using MosaicToNewRaster. If no mosaicking is
    required, the directory is renamed directly and filenames are
    standardized.

    Parameters
    ----------
    swot_root_dir : str
        Root directory of SWOT raster processing workflow.

    Directory Structure
    -------------------
    swot_root_dir/
    ├── 03_wse_Clip/
    └── 04_wse_merge/

    Returns
    -------
    None
    """

    input_raster_dir = os.path.join(
        swot_root_dir,
        "03_wse_Clip"
    )
    output_raster_dir = os.path.join(
        swot_root_dir,
        "04_wse_merge"
    )

    raster_groups = defaultdict(list)

    for raster_name in os.listdir(input_raster_dir):
        if not raster_name.lower().endswith(".tif"):
            continue

        parsed_keys = _parse_keys_from_filename(raster_name)
        if parsed_keys is None:
            continue

        date_key, spatial_key = parsed_keys
        raster_path = os.path.join(input_raster_dir, raster_name)
        raster_groups[spatial_key].append((date_key, raster_path))

    requires_mosaic = any(
        len(rasters) > 1 for rasters in raster_groups.values()
    )

    # Case 1: Mosaic is required
    if requires_mosaic:
        os.makedirs(output_raster_dir, exist_ok=True)

        for spatial_key, raster_list in raster_groups.items():
            date_keys = [item[0] for item in raster_list]
            unique_dates = sorted(set(date_keys))

            output_date_key = unique_dates[0]
            output_name = f"{output_date_key}_{spatial_key}.tif"
            output_path = os.path.join(output_raster_dir, output_name)

            if len(raster_list) == 1:
                arcpy.management.CopyRaster(
                    raster_list[0][1],
                    output_path
                )
            else:
                input_rasters = [item[1] for item in raster_list]
                arcpy.management.MosaicToNewRaster(
                    input_rasters=input_rasters,
                    output_location=output_raster_dir,
                    raster_dataset_name_with_extension=output_name,
                    pixel_type="32_BIT_FLOAT",
                    number_of_bands=1,
                    mosaic_method="LAST",
                    mosaic_colormap_mode="MATCH"
                )

    # Case 2: No mosaic needed → rename directory and files
    else:
        if os.path.exists(output_raster_dir):
            shutil.rmtree(output_raster_dir)

        os.rename(input_raster_dir, output_raster_dir)

        for spatial_key, raster_list in raster_groups.items():
            date_key = raster_list[0][0]
            old_path = raster_list[0][1].replace(
                "03_wse_Clip",
                "04_wse_merge"
            )
            new_path = os.path.join(
                output_raster_dir,
                f"{date_key}_{spatial_key}.tif"
            )
            if old_path != new_path:
                os.rename(old_path, new_path)

# -*- coding: utf-8 -*-
import os
import arcpy
from arcpy.sa import ExtractByMask


def _compare_tif_file_count(source_dir, target_dir):
    """
    Compare the number of GeoTIFF files between two directories.

    Parameters
    ----------
    source_dir : str
        Directory containing source GeoTIFF files.
    target_dir : str
        Directory containing output GeoTIFF files.

    Returns
    -------
    bool
        True if file counts differ, False otherwise.
    """
    source_count = len(
        [f for f in os.listdir(source_dir) if f.lower().endswith(".tif")]
    )
    target_count = len(
        [f for f in os.listdir(target_dir) if f.lower().endswith(".tif")]
    )
    return source_count != target_count


def P4_clip_rasters_by_shapefile(
    working_dir,
    clip_polygon_path,
    region_key
):
    """
    Clip projected WSE raster datasets using a polygon shapefile mask.

    Raster clipping is performed using ExtractByMask. Only rasters
    that have not yet been clipped are processed to avoid redundancy.

    Parameters
    ----------
    working_dir : str
        Root directory for a single processing unit (e.g., region or key).
    clip_polygon_path : str
        Path to the polygon shapefile used as the clipping mask.
    region_key : str
        Identifier for the processing unit (reserved for pipeline tracking).

    Directory Structure
    -------------------
    working_dir/
    ├── 02_wse_proj/
    └── 03_wse_Clip/

    Returns
    -------
    None
    """

    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = working_dir

    projected_raster_dir = os.path.join(
        working_dir,
        "02_wse_proj"
    )
    clipped_raster_dir = os.path.join(
        working_dir,
        "03_wse_Clip"
    )

    os.makedirs(clipped_raster_dir, exist_ok=True)

    if not _compare_tif_file_count(
        projected_raster_dir,
        clipped_raster_dir
    ):
        return

    for raster_name in os.listdir(projected_raster_dir):
        if not raster_name.lower().endswith(".tif"):
            continue

        input_raster_path = os.path.join(
            projected_raster_dir,
            raster_name
        )
        output_raster_path = os.path.join(
            clipped_raster_dir,
            raster_name
        )

        if os.path.exists(output_raster_path):
            continue

        try:
            clipped_raster = ExtractByMask(
                input_raster_path,
                clip_polygon_path
            )
            clipped_raster.save(output_raster_path)
        except Exception:
            continue

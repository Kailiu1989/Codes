# -*- coding: utf-8 -*-
import os
import arcpy


def _all_rasters_in_wgs84(raster_dir):
    """
    Check whether all GeoTIFF rasters in a directory
    are already projected to WGS 1984 (EPSG:4326).

    Parameters
    ----------
    raster_dir : str
        Directory containing GeoTIFF rasters.

    Returns
    -------
    bool
        True if all rasters are in WGS 1984, False otherwise.
    """
    arcpy.env.workspace = raster_dir
    raster_list = arcpy.ListRasters("*.tif")

    if not raster_list:
        return False

    for raster_name in raster_list:
        raster_path = os.path.join(raster_dir, raster_name)
        desc = arcpy.Describe(raster_path)
        spatial_ref = desc.spatialReference

        if spatial_ref.factoryCode != 4326:
            return False

    return True


def P3_project_rasters_to_wgs84(swot_root_dir):
    """
    Project filtered WSE GeoTIFF rasters to WGS 1984 (EPSG:4326).

    If all rasters are already in WGS 1984, the input directory
    is renamed directly as the output directory to avoid
    unnecessary reprojection.

    Parameters
    ----------
    swot_root_dir : str
        Root directory of SWOT raster processing workflow.

    Directory Structure
    -------------------
    swot_root_dir/
    ├── 01_filter_Origin_tifs/
    └── 02_wse_proj/

    Returns
    -------
    None
    """

    input_raster_dir = os.path.join(
        swot_root_dir,
        "01_filter_Origin_tifs"
    )
    output_raster_dir = os.path.join(
        swot_root_dir,
        "02_wse_proj"
    )

    arcpy.env.workspace = input_raster_dir
    arcpy.env.overwriteOutput = True

    raster_files = arcpy.ListRasters("*.tif")
    if not raster_files:
        return

    target_spatial_ref = arcpy.SpatialReference(4326)

    # Case 1: All rasters are already in WGS 1984
    if _all_rasters_in_wgs84(input_raster_dir):
        try:
            os.rename(input_raster_dir, output_raster_dir)
        except OSError:
            pass
        return

    # Case 2: Reprojection is required
    if not os.path.exists(output_raster_dir):
        os.makedirs(output_raster_dir)

    for raster_name in raster_files:
        input_raster_path = os.path.join(
            input_raster_dir,
            raster_name
        )
        output_raster_path = os.path.join(
            output_raster_dir,
            raster_name
        )

        if os.path.exists(output_raster_path):
            continue

        try:
            arcpy.ProjectRaster_management(
                in_raster=input_raster_path,
                out_raster=output_raster_path,
                out_coor_system=target_spatial_ref
            )
        except Exception:
            continue

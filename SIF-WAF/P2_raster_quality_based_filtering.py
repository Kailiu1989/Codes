# -*- coding: utf-8 -*-
import os
import arcpy


def _compare_tif_file_count(source_dir, target_dir):
    """
    Compare the number of GeoTIFF files between two directories.

    Parameters
    ----------
    source_dir : str
        Directory containing source GeoTIFF files.
    target_dir : str
        Directory containing processed GeoTIFF files.

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


def P2_filter_rasters_by_quality_threshold(
    wse_raster_dir,
    quality_raster_dir,
    quality_threshold,
    output_root_dir
):
    """
    Filter WSE raster datasets based on a quality raster threshold.

    For each WSE raster, the corresponding quality raster is identified
    by matching filename prefixes. Pixels with quality values greater
    than or equal to the given threshold are set to NoData.

    Parameters
    ----------
    wse_raster_dir : str
        Directory containing WSE GeoTIFF rasters.
    quality_raster_dir : str
        Directory containing quality classification GeoTIFF rasters.
    quality_threshold : float
        Threshold value used to mask low-quality pixels.
    output_root_dir : str
        Root directory for filtered output rasters.

    Returns
    -------
    None
    """

    output_dir = os.path.join(output_root_dir, "01_filter_Origin_tifs")
    os.makedirs(output_dir, exist_ok=True)

    if not _compare_tif_file_count(wse_raster_dir, output_dir):
        return

    for wse_filename in os.listdir(wse_raster_dir):
        if not wse_filename.lower().endswith(".tif"):
            continue

        wse_path = os.path.join(wse_raster_dir, wse_filename)
        if not os.path.exists(wse_path):
            continue

        # Extract matching prefix (before the last underscore)
        wse_prefix = "_".join(wse_filename.split("_")[:-1])

        quality_filename = next(
            (
                f for f in os.listdir(quality_raster_dir)
                if f.lower().endswith(".tif")
                and "_".join(f.split("_")[:-2]) == wse_prefix
            ),
            None
        )

        if quality_filename is None:
            continue

        quality_path = os.path.join(quality_raster_dir, quality_filename)

        try:
            quality_raster = arcpy.Raster(quality_path)
            quality_min_value = float(
                arcpy.GetRasterProperties_management(
                    quality_raster, "MINIMUM"
                ).getOutput(0)
            )
        except Exception:
            continue

        # Skip rasters that do not require filtering
        if quality_min_value >= quality_threshold:
            continue

        output_raster_path = os.path.join(output_dir, wse_filename)
        if os.path.exists(output_raster_path):
            continue

        try:
            wse_raster = arcpy.Raster(wse_path)
        except RuntimeError:
            continue

        raster_expression = (
            f'SetNull("{quality_raster}" >= {quality_threshold}, "{wse_raster}")'
        )

        try:
            arcpy.gp.RasterCalculator_sa(
                raster_expression,
                output_raster_path
            )
        except arcpy.ExecuteError:
            continue

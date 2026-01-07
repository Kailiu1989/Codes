# -*- coding: utf-8 -*-
import os
import arcpy


def P9_align_rasters_to_reference(project_root: str) -> None:
    """
    Align all raster datasets in 02_Extract_Tifs to the reference raster
    (03_Max_Tif/max_valid_pixel_range_Clip.tif).

    This version is robust against ArcPy environment pitfalls and ensures:
    - consistent snap raster
    - consistent cell size
    - consistent spatial reference
    """

    input_dir = os.path.join(project_root, "02_Extract_Tifs")
    output_dir = os.path.join(project_root, "04_Aligned_tifs")
    reference_raster = _get_reference_raster(project_root)

    # ---------- basic checks ----------
    if not arcpy.Exists(reference_raster):
        raise FileNotFoundError(f"Reference raster not found: {reference_raster}")

    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"Input raster folder not found: {input_dir}")

    os.makedirs(output_dir, exist_ok=True)

    # ---------- reference properties ----------
    ref_desc = arcpy.Describe(reference_raster)
    ref_sr = ref_desc.spatialReference
    ref_cellsize = arcpy.management.GetRasterProperties(
        reference_raster, "CELLSIZEX"
    ).getOutput(0)

    # ---------- list rasters ----------
    arcpy.env.workspace = input_dir
    raster_list = arcpy.ListRasters("*", "TIF")
    if not raster_list:
        print("P9: No input rasters found, skip alignment.")
        return

    # ---------- safe environment scope ----------
    with arcpy.EnvManager(
        workspace=input_dir,
        snapRaster=reference_raster,
        outputCoordinateSystem=ref_sr,
        overwriteOutput=True
    ):
        for raster_name in raster_list:
            in_raster = os.path.join(input_dir, raster_name)
            out_raster = os.path.join(output_dir, raster_name)

            # skip if already exists
            if arcpy.Exists(out_raster):
                continue

            try:
                arcpy.management.Resample(
                    in_raster=in_raster,
                    out_raster=out_raster,
                    cell_size=ref_cellsize,
                    resampling_type="NEAREST"
                )
            except arcpy.ExecuteError:
                print(f"P9 warning: failed to align {raster_name}")
                print(arcpy.GetMessages(2))
            except Exception as e:
                print(f"P9 unexpected error: {raster_name} -> {e}")


def _get_reference_raster(project_root: str) -> str:
    """
    Get reference raster path.
    """
    return os.path.join(
        project_root,
        "03_Max_Tif",
        "max_valid_pixel_range_Clip.tif"
    )

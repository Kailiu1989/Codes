# -*- coding: utf-8 -*-
from arcpy.sa import ExtractByMask
import arcpy
import os
import glob


def _remove_corrupted_rasters(raster_folder: str) -> None:
    """
    Remove GeoTIFF files that cannot return valid raster statistics
    (e.g., MINIMUM value cannot be read).
    """
    arcpy.env.workspace = raster_folder
    tif_files = glob.glob(os.path.join(raster_folder, "*.tif"))

    for tif_path in tif_files:
        try:
            _ = float(
                arcpy.GetRasterProperties_management(
                    tif_path, "MINIMUM"
                ).getOutput(0)
            )
        except Exception:
            base_name = os.path.splitext(tif_path)[0]
            related_extensions = [
                ".tif", ".tfw", ".ovr",
                ".aux.xml", ".tif.xml", ".tif.aux.xml"
            ]

            for ext in related_extensions:
                file_to_remove = base_name + ext
                if os.path.exists(file_to_remove):
                    try:
                        os.remove(file_to_remove)
                    except PermissionError:
                        pass


def P7_extract_wse_by_monthly_drawdown_mask(
    swot_root_path: str,
    mask_root_path: str
) -> None:
    """
    Match monthly SWOT WSE GeoTIFF files with corresponding
    drawdown-area shapefiles and perform raster extraction by mask.
    """

    arcpy.CheckOutExtension("Spatial")
    arcpy.env.overwriteOutput = True

    wse_raster_folder = os.path.join(swot_root_path, "04_wse_merge")
    drawdown_shp_folder = os.path.join(mask_root_path, "01_Monthly_Drawdown_Area")
    output_raster_folder = os.path.join(mask_root_path, "02_Extract_Tifs")

    os.makedirs(output_raster_folder, exist_ok=True)

    wse_rasters = [
        f for f in os.listdir(wse_raster_folder)
        if f.lower().endswith(".tif")
    ]

    drawdown_shapefiles = [
        f for f in os.listdir(drawdown_shp_folder)
        if f.lower().endswith(".shp")
    ]

    processed_count = 0
    extracted_count = 0
    no_overlap_count = 0
    unmatched_count = 0
    unmatched_files = []

    for raster_name in wse_rasters:
        raster_path = os.path.join(wse_raster_folder, raster_name)

        raster_parts = raster_name.split("_")
        raster_year = raster_parts[0]
        raster_month = str(int(raster_parts[1]))
        raster_year_month = f"{raster_year}_{raster_month}"

        matched_shapefile = None

        for shp_name in drawdown_shapefiles:
            shp_parts = shp_name.replace(".shp", "").split("_")

            shp_year = None
            shp_month = None

            for i, part in enumerate(shp_parts):
                if part.startswith("20") and part.isdigit():
                    shp_year = part
                    if i + 1 < len(shp_parts):
                        shp_month = shp_parts[i + 1]
                    break

            if shp_year and shp_month:
                shp_year_month = f"{shp_year}_{int(shp_month)}"
            else:
                continue

            if shp_year_month == raster_year_month:
                matched_shapefile = os.path.join(
                    drawdown_shp_folder, shp_name
                )
                break

        if matched_shapefile:
            try:
                output_raster = os.path.join(
                    output_raster_folder,
                    raster_name.replace(".tif", "_masked.tif")
                )

                extracted_raster = ExtractByMask(
                    raster_path, matched_shapefile
                )
                extracted_raster.save(output_raster)
                extracted_count += 1

            except arcpy.ExecuteError:
                no_overlap_count += 1
        else:
            unmatched_count += 1
            unmatched_files.append(raster_name)

        processed_count += 1

    arcpy.CheckInExtension("Spatial")

    _remove_corrupted_rasters(output_raster_folder)

    valid_rasters = [
        f for f in os.listdir(output_raster_folder)
        if f.lower().endswith(".tif")
    ]

    print("Raster extraction completed.")
    print(f"Processed rasters: {processed_count}")
    print(f"Successfully extracted: {len(valid_rasters)}")
    print(f"No spatial overlap: {no_overlap_count}")
    print(f"No matching shapefile: {unmatched_count}")

    if unmatched_files:
        print("Unmatched raster files:")
        for f in unmatched_files:
            print(f"  {f}")

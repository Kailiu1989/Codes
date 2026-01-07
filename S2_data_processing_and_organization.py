# -*- coding: utf-8 -*-
import os
import arcpy
# -*- coding: utf-8 -*-
from arcpy.sa import ExtractByMask
import arcpy
import os
import glob

# -*- coding: utf-8 -*-
import os
import numpy as np
import rasterio
import arcpy

def _project_shapefile_to_wgs84(input_shapefile: str, output_shapefile: str) -> None:
    """
    Project a shapefile to the WGS 1984 geographic coordinate system (EPSG:4326).

    Parameters
    ----------
    input_shapefile : str
        Path to the input shapefile.
    output_shapefile : str
        Path to the output projected shapefile.
    """
    spatial_ref_wgs84 = arcpy.SpatialReference(4326)

    if arcpy.Exists(output_shapefile):
        arcpy.management.Delete(output_shapefile)

    arcpy.management.Project(
        in_dataset=input_shapefile,
        out_dataset=output_shapefile,
        out_coor_system=spatial_ref_wgs84
    )


def P6_erase_waterbody_from_base_frame(
    base_frame_shapefile: str,
    waterbody_shapefile_folder: str,
    output_root_folder: str,
    output_suffix: str = "_Use"
) -> None:
    """
    Erase multiple waterbody shapefiles from a base frame shapefile.

    All shapefiles are first projected to WGS 1984 to ensure
    spatial consistency before applying the erase operation.

    Parameters
    ----------
    base_frame_shapefile : str
        Path to the base frame shapefile.
    waterbody_shapefile_folder : str
        Directory containing waterbody shapefiles to be erased.
    output_root_folder : str
        Root directory for output results.
    output_suffix : str, optional
        Suffix appended to output shapefile names (default: "_Use").
    """

    if not arcpy.Exists(base_frame_shapefile):
        raise FileNotFoundError(
            f"Base frame shapefile not found: {base_frame_shapefile}"
        )

    if not os.path.isdir(waterbody_shapefile_folder):
        raise FileNotFoundError(
            f"Waterbody shapefile folder not found: {waterbody_shapefile_folder}"
        )

    os.makedirs(output_root_folder, exist_ok=True)

    output_area_folder = os.path.join(
        output_root_folder, "01_Monthly_Drawdown_Area"
    )
    temp_projection_folder = os.path.join(
        output_root_folder, "00_Temp_Frame_WGS84"
    )

    os.makedirs(output_area_folder, exist_ok=True)
    os.makedirs(temp_projection_folder, exist_ok=True)

    base_frame_wgs84 = os.path.join(
        temp_projection_folder, "base_frame_wgs84.shp"
    )

    _project_shapefile_to_wgs84(
        base_frame_shapefile,
        base_frame_wgs84
    )

    arcpy.env.workspace = waterbody_shapefile_folder
    waterbody_shapefiles = arcpy.ListFeatureClasses("*.shp")

    if not waterbody_shapefiles:
        raise RuntimeError(
            f"No waterbody shapefiles (*.shp) found in folder: "
            f"{waterbody_shapefile_folder}"
        )

    processed_counter = 0

    for waterbody_shp in waterbody_shapefiles:
        waterbody_wgs84 = os.path.join(
            temp_projection_folder,
            f"{os.path.splitext(waterbody_shp)[0]}_wgs84.shp"
        )

        _project_shapefile_to_wgs84(
            waterbody_shp,
            waterbody_wgs84
        )

        output_shapefile = os.path.join(
            output_area_folder,
            f"{os.path.splitext(waterbody_shp)[0]}{output_suffix}.shp"
        )

        if arcpy.Exists(output_shapefile):
            arcpy.management.Delete(output_shapefile)

        arcpy.analysis.Erase(
            in_features=base_frame_wgs84,
            erase_features=waterbody_wgs84,
            out_feature_class=output_shapefile
        )

        processed_counter += 1

    print(
        f"[P6] Waterbody erase completed: "
        f"{processed_counter} drawdown-area shapefiles generated."
    )


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

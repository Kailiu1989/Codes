# -*- coding: utf-8 -*-
import logging
from typing import Dict, Optional, Sequence, Set, Tuple, List
import os
import shutil
import arcpy
from collections import defaultdict
from arcpy.sa import ExtractByMask

def _group_geotiffs_by_prefix(
    directory: str,
    suffix_token_count: int,
) -> Dict[str, List[Tuple[str, str]]]:
    """
    Group GeoTIFF files by a shared filename prefix.

    Filenames are split using underscores ("_"). The last `suffix_token_count`
    tokens form a group-specific suffix (e.g., processing level or quality flag),
    while the remaining tokens define the logical group prefix.

    Parameters
    ----------
    directory : str
        Directory containing GeoTIFF (*.tif) files.
    suffix_token_count : int
        Number of underscore-separated tokens to treat as the suffix.

    Returns
    -------
    Dict[str, List[Tuple[str, str]]]
        Mapping from prefix_key to a list of (suffix_key, filename).
    """
    grouped_files: Dict[str, List[Tuple[str, str]]] = {}

    for filename in os.listdir(directory):
        if not filename.lower().endswith(".tif"):
            continue

        stem = filename[:-4]  # remove ".tif"
        tokens = stem.split("_")

        if len(tokens) <= suffix_token_count:
            continue

        prefix_key = "_".join(tokens[:-suffix_token_count])
        suffix_key = "_".join(tokens[-suffix_token_count:])

        grouped_files.setdefault(prefix_key, []).append((suffix_key, filename))

    return grouped_files


def _select_priority_suffix(
    suffix_to_filename: Dict[str, str],
    priority_codes: Sequence[str],
) -> Optional[str]:
    """
    Select the highest-priority suffix key based on predefined priority codes.

    The first matching priority code encountered (from high to low priority)
    determines the selected suffix.

    Parameters
    ----------
    suffix_to_filename : Dict[str, str]
        Mapping from suffix_key to filename.
    priority_codes : Sequence[str]
        Priority codes ordered from highest to lowest.

    Returns
    -------
    Optional[str]
        Selected suffix_key, or None if no priority code is matched.
    """
    for code in priority_codes:
        for suffix_key in suffix_to_filename:
            if code in suffix_key:
                return suffix_key
    return None


def _remove_geotiff_sidecars(
    directory: str,
    filename: str,
    extensions: Sequence[str],
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Remove a GeoTIFF file and its associated sidecar files.

    Parameters
    ----------
    directory : str
        Directory containing the files.
    filename : str
        GeoTIFF filename (with .tif extension).
    extensions : Sequence[str]
        File extensions to remove together with the GeoTIFF.
    logger : Optional[logging.Logger]
        Logger for warning messages; if None, no logging is performed.
    """
    base_name = os.path.splitext(filename)[0]

    for ext in extensions:
        file_path = os.path.join(directory, base_name + ext)
        if not os.path.exists(file_path):
            continue
        try:
            os.remove(file_path)
        except OSError as exc:
            if logger:
                logger.warning(f"Failed to remove file: {file_path} ({exc})")


def P0_clean_wse_tif_by_priority(
    folder_path: str,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Retain only the highest-priority SWOT WSE GeoTIFF per group.

    Grouping rule
    -------------
    - Prefix: filename tokens excluding the last 3 underscore-separated tokens
    - Suffix: last 3 tokens

    Priority order (high to low)
    ----------------------------
    PGC > PIC3 > PIC2 > PIC1 > PIC0

    Removed together with discarded GeoTIFFs
    ----------------------------------------
    .tif, .tfw, .tif.aux.xml, .tif.ovr, .tif.xml

    Parameters
    ----------
    folder_path : str
        Directory containing WSE GeoTIFF products.
    logger : Optional[logging.Logger]
        Optional logger for minimal status or warning messages.
    """
    priority_codes = ("PGC", "PIC3", "PIC2", "PIC1", "PIC0")
    sidecar_extensions = (".tif", ".tfw", ".tif.aux.xml", ".tif.ovr", ".tif.xml")

    groups = _group_geotiffs_by_prefix(
        directory=folder_path,
        suffix_token_count=3,
    )

    for prefix_key, entries in groups.items():
        suffix_to_filename = {suffix: fname for suffix, fname in entries}
        selected_suffix = _select_priority_suffix(
            suffix_to_filename,
            priority_codes,
        )

        if selected_suffix is None:
            if logger:
                logger.info(
                    f"[WSE] No matching priority found for group: {prefix_key}. Files retained."
                )
            continue

        for suffix_key, fname in entries:
            if suffix_key == selected_suffix:
                continue
            _remove_geotiff_sidecars(
                folder_path,
                fname,
                sidecar_extensions,
                logger=logger,
            )


def P0_clean_wse_qual_tif_by_priority(
    folder_path: str,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Retain only the highest-priority SWOT WSE_QUAL GeoTIFF per group.

    Grouping rule
    -------------
    - Prefix: filename tokens excluding the last 4 underscore-separated tokens
    - Suffix: last 4 tokens

    Priority order (high to low)
    ----------------------------
    PGD > PGC > PID > PIC3 > PIC2 > PIC1 > PIC0

    Removed together with discarded GeoTIFFs
    ----------------------------------------
    .tif, .tfw, .tif.aux.xml, .tif.ovr, .tif.xml

    Parameters
    ----------
    folder_path : str
        Directory containing WSE_QUAL GeoTIFF products.
    logger : Optional[logging.Logger]
        Optional logger for minimal status or warning messages.
    """
    priority_codes = ("PGD", "PGC", "PID", "PIC3", "PIC2", "PIC1", "PIC0")
    sidecar_extensions = (".tif", ".tfw", ".tif.aux.xml", ".tif.ovr", ".tif.xml")

    groups = _group_geotiffs_by_prefix(
        directory=folder_path,
        suffix_token_count=4,
    )

    for prefix_key, entries in groups.items():
        suffix_to_filename = {suffix: fname for suffix, fname in entries}
        selected_suffix = _select_priority_suffix(
            suffix_to_filename,
            priority_codes,
        )

        if selected_suffix is None:
            if logger:
                logger.info(
                    f"[WSE_QUAL] No matching priority found for group: {prefix_key}. Files retained."
                )
            continue

        for suffix_key, fname in entries:
            if suffix_key == selected_suffix:
                continue
            _remove_geotiff_sidecars(
                folder_path,
                fname,
                sidecar_extensions,
                logger=logger,
            )

def _count_geotiffs_recursive(directory: str) -> int:
    """
    Recursively count GeoTIFF files under a directory.

    Parameters
    ----------
    directory : str
        Root directory to be scanned.

    Returns
    -------
    int
        Total number of files with .tif or .tiff extensions
        (case-insensitive).
    """
    count = 0
    for _, _, files in os.walk(directory):
        for fname in files:
            if fname.lower().endswith((".tif", ".tiff")):
                count += 1
    return count


def _index_rasters_by_basename(
    directory: str,
    suffix: str,
) -> Dict[str, str]:
    """
    Build a mapping from raster basename to filename
    for files ending with a specific suffix.

    Example
    -------
    suffix = "_wse.tif"
    "scene001_wse.tif" -> {"scene001": "scene001_wse.tif"}

    Parameters
    ----------
    directory : str
        Directory to be scanned (non-recursive).
    suffix : str
        Filename suffix identifying target rasters.

    Returns
    -------
    Dict[str, str]
        Mapping from basename to full filename.
    """
    index: Dict[str, str] = {}

    for fname in os.listdir(directory):
        if fname.endswith(suffix):
            base_name = fname[:-len(suffix)]
            index[base_name] = fname

    return index


def _remove_raster_and_sidecars(
    directory: str,
    filename: str,
    sidecar_extensions: Sequence[str],
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Remove a raster file together with its associated
    auxiliary (sidecar) files.

    Parameters
    ----------
    directory : str
        Directory containing the raster.
    filename : str
        Main raster filename (e.g., "xxx_wse.tif").
    sidecar_extensions : Sequence[str]
        Extensions appended to the raster stem.
    logger : Optional[logging.Logger]
        Optional logger for warning messages.
    """
    stem, _ = os.path.splitext(filename)

    for ext in sidecar_extensions:
        path = os.path.join(directory, stem + ext)
        if not os.path.exists(path):
            continue
        try:
            os.remove(path)
        except OSError as exc:
            if logger:
                logger.warning(
                    f"Failed to remove file: {path} ({exc})"
                )


def _cleanup_unpaired_wse_pairs(
    wse_dir: str,
    qual_dir: str,
    logger: Optional[logging.Logger] = None,
    remove_sidecars: bool = True,
) -> Tuple[Set[str], Set[str]]:
    """
    Remove unpaired WSE and WSE_QUAL rasters based on basename matching.

    Pairing rule
    ------------
    - WSE:      *_wse.tif
    - WSE_QUAL: *_wse_qual.tif
    - A valid pair must share the same basename.

    Parameters
    ----------
    wse_dir : str
        Directory containing WSE rasters.
    qual_dir : str
        Directory containing WSE_QUAL rasters.
    logger : Optional[logging.Logger]
        Optional logger for reporting removals.
    remove_sidecars : bool
        Whether to remove auxiliary raster files.

    Returns
    -------
    Tuple[Set[str], Set[str]]
        Basenames removed from (wse_dir, qual_dir).
    """
    wse_suffix = "_wse.tif"
    qual_suffix = "_wse_qual.tif"

    wse_index = _index_rasters_by_basename(wse_dir, wse_suffix)
    qual_index = _index_rasters_by_basename(qual_dir, qual_suffix)

    shared_keys = set(wse_index) & set(qual_index)
    orphan_wse = set(wse_index) - shared_keys
    orphan_qual = set(qual_index) - shared_keys

    sidecar_exts = (
        ".tif",
        ".tfw",
        ".tif.aux.xml",
        ".tif.ovr",
        ".tif.xml",
    )

    for key in orphan_wse:
        fname = wse_index[key]
        if remove_sidecars:
            _remove_raster_and_sidecars(
                wse_dir, fname, sidecar_exts, logger
            )
        else:
            os.remove(os.path.join(wse_dir, fname))

        if logger:
            logger.info(f"Removed unpaired WSE raster: {fname}")

    for key in orphan_qual:
        fname = qual_index[key]
        if remove_sidecars:
            _remove_raster_and_sidecars(
                qual_dir, fname, sidecar_exts, logger
            )
        else:
            os.remove(os.path.join(qual_dir, fname))

        if logger:
            logger.info(f"Removed unpaired WSE_QUAL raster: {fname}")

    return orphan_wse, orphan_qual


def P1_validate_and_align_wse_pairs(
    wse_dir: str,
    qual_dir: str,
    logger: Optional[logging.Logger] = None,
    strict: bool = False,
) -> None:
    """
    Validate and enforce one-to-one correspondence between
    WSE and WSE_QUAL raster datasets.

    Designed as a pipeline validation step:
    - Silent on success
    - Logging-based reporting
    - Optional strict failure mode

    Parameters
    ----------
    wse_dir : str
        Directory containing WSE rasters.
    qual_dir : str
        Directory containing WSE_QUAL rasters.
    logger : Optional[logging.Logger]
        Logger for warnings and status messages.
    strict : bool
        If True, raise RuntimeError if inconsistencies persist.

    Raises
    ------
    FileNotFoundError
        If input directories do not exist.
    NotADirectoryError
        If input paths are not directories.
    RuntimeError
        If strict=True and pairing remains inconsistent.
    """
    for directory in (wse_dir, qual_dir):
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Path does not exist: {directory}")
        if not os.path.isdir(directory):
            raise NotADirectoryError(
                f"Path is not a directory: {directory}"
            )

    count_wse = _count_geotiffs_recursive(wse_dir)
    count_qual = _count_geotiffs_recursive(qual_dir)

    if count_wse == count_qual:
        return

    if logger:
        logger.warning(
            "GeoTIFF count mismatch detected "
            f"(WSE={count_wse}, WSE_QUAL={count_qual}). "
            "Attempting automatic alignment."
        )

    _cleanup_unpaired_wse_pairs(
        wse_dir, qual_dir, logger=logger, remove_sidecars=True
    )

    count_wse_after = _count_geotiffs_recursive(wse_dir)
    count_qual_after = _count_geotiffs_recursive(qual_dir)

    if count_wse_after != count_qual_after:
        message = (
            "GeoTIFF count mismatch persists after cleanup "
            f"(WSE={count_wse_after}, "
            f"WSE_QUAL={count_qual_after})."
        )
        if strict:
            raise RuntimeError(message)
        if logger:
            logger.warning(message)
    else:
        if logger:
            logger.info(
                "WSE and WSE_QUAL datasets successfully aligned."
            )


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

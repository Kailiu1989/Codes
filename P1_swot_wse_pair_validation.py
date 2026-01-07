# -*- coding: utf-8 -*-
import os
import logging
from typing import Dict, Optional, Sequence, Set, Tuple


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

# -*- coding: utf-8 -*-
import os
import logging
from typing import Dict, List, Optional, Sequence, Tuple


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

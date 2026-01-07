# -*- coding: utf-8 -*-
from __future__ import annotations
import logging
from typing import List, Tuple
from pathlib import Path
from S1_SWOT_data_preprocessing import (
    P0_clean_wse_tif_by_priority,
    P0_clean_wse_qual_tif_by_priority,
    P1_validate_and_align_wse_pairs,
    P2_filter_rasters_by_quality_threshold,
    P3_project_rasters_to_wgs84,
    P4_clip_rasters_by_shapefile,
    P5_mosaic_rasters_by_key
)

from S2_data_processing_and_organization import (
    P6_erase_waterbody_from_base_frame,
    P7_extract_wse_by_monthly_drawdown_mask,
    P8_generate_maximum_valid_wse_extent,
    P9_align_rasters_to_reference,
    P10_Merged_All_SWOT,
    P11_Process_rasters_with_max,
)

from S3_sif_waf_pixelwise_reconstruction import P12_run_sif_waf_reconstruction
from S4_run_postprocessing_with_buffer import P13_run_postprocessing_with_buffer


def get_subfolder_names(folder_path):
    """
    Returns a list of names of all direct subfolders in the folder_path,
    without sorting and without requiring the names to be digits.

    Parameters
    ----------
    folder_path: str or Path
        The path of the parent folder to scan.

    Returns
    -------
    List[str]
        A list of names of the subfolders.
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        raise ValueError(f"{folder_path} is not a valid path")

    return [p.name for p in folder.iterdir() if p.is_dir()]


def setup_logger(level: int = logging.INFO) -> logging.Logger:
    """Configure a console logger suitable for GitHub/SCI code release."""
    logger = logging.getLogger("pipeline")
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def run_single_site(
    site_id: str,
    swot_root_dir: Path,
    inventory_root_dir: Path,
    waterbody_root_dir: Path,
    icesat2_root_dir: Path,
    output_root_dir: Path,
    std_sigma: float,
    qual_level: int,
    enable_preprocessing: bool,
    logger: logging.Logger,
) -> None:
    """
    Run the full pipeline for one lake/reservoir.
    """
    site_swot_dir = swot_root_dir / site_id
    wse_dir = site_swot_dir / "wse"
    wse_qual_dir = site_swot_dir / "wse_qual"

    frame_shp = inventory_root_dir / site_id / f"{site_id}.shp"
    waterbody_dir = waterbody_root_dir / site_id
    site_output_dir = output_root_dir / site_id
    icesat2_shp = (
        icesat2_root_dir
        / site_id
        / "Process"
        / "06_Clear"
        / f"{site_id}.shp"
    )

    # --- Basic existence checks ---
    if not site_swot_dir.exists():
        logger.warning(f"[SKIP] SWOT folder not found: {site_swot_dir}")
        return
    if not frame_shp.exists():
        logger.warning(f"[SKIP] Frame shapefile not found: {frame_shp}")
        return

    site_output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"[START] Site: {site_id}")

    # ================= Preprocessing (P0–P5) =================
    if enable_preprocessing:
        merged_flag_dir = site_swot_dir / "04_wse_merge"
        if merged_flag_dir.exists():
            logger.info("[PRE] Detected existing '04_wse_merge', preprocessing skipped.")
        else:
            clip_dir = site_swot_dir / "02_wse_Clip"
            if not clip_dir.exists():
                # P0
                P0_clean_wse_tif_by_priority(str(wse_dir))
                P0_clean_wse_qual_tif_by_priority(str(wse_qual_dir))

                # P1
                P1_validate_and_align_wse_pairs(
                    str(wse_dir),
                    str(wse_qual_dir)
                )

                # P2
                P2_filter_rasters_by_quality_threshold(
                    str(site_swot_dir / "wse"),
                    str(site_swot_dir / "wse_qual"),
                    qual_level,
                    str(site_swot_dir),
                )

                # P3
                P3_project_rasters_to_wgs84(str(site_swot_dir))
            else:
                logger.info("[PRE] Detected existing '02_wse_Clip', P0–P3 skipped.")

            # P4
            P4_clip_rasters_by_shapefile(
                str(site_swot_dir),
                str(frame_shp),
                site_id
            )

            # P5
            P5_mosaic_rasters_by_key(str(site_swot_dir))

            logger.info("[PRE] Preprocessing completed (P0–P5).")
    else:
        logger.info("[PRE] Preprocessing disabled by configuration.")

    # ================= Reconstruction (P6–P13) =================

    # P6
    P6_erase_waterbody_from_base_frame(
        str(frame_shp),
        str(waterbody_dir),
        str(site_output_dir),
    )

    # P7
    P7_extract_wse_by_monthly_drawdown_mask(
        str(site_swot_dir),
        str(site_output_dir),
    )

    # P8
    P8_generate_maximum_valid_wse_extent(str(site_output_dir))

    # P9
    P9_align_rasters_to_reference(str(site_output_dir))

    # P10
    P10_Merged_All_SWOT(str(site_output_dir))

    # P11
    P11_Process_rasters_with_max(str(site_output_dir))

    # P12
    P12_run_sif_waf_reconstruction(std_sigma, str(site_output_dir), str(icesat2_shp), "SIF")
    waf_flag = P12_run_sif_waf_reconstruction(std_sigma, str(site_output_dir), str(icesat2_shp), "WAF")

    # P13
    P13_run_postprocessing_with_buffer(
        str(frame_shp),
        str(site_output_dir),
        site_id,
        waf_flag,
    )

    logger.info(f"[DONE] Site: {site_id}")


def main() -> None:
    """
    Main entry point for running the pipeline over all sites.
    """
    logger = setup_logger(logging.INFO)

    # ===================== Experiment parameters =====================
    # std_sigma:
    #   Standard deviation threshold used in the iterative denoising process.
    #   Larger values result in stronger smoothing, while smaller values preserve
    #   more local elevation variability.
    std_sigma = 2

    # qual_level:
    #   Quality control threshold for SWOT WSE data.
    #   Only pixels with wse_qual values less than this level
    #   will be retained for further analysis.
    qual_level = 2

    # enable_preprocessing:
    #   Switch controlling the execution of preprocessing steps.
    #   - True  : Execute the full workflow, including preprocessing (P0–P5)
    #             and subsequent drawdown topography reconstruction (P6–P13).
    #   - False : Skip preprocessing and directly execute the reconstruction
    #             stages (P6–P13), assuming all required intermediate products
    #             already exist.
    enable_preprocessing = False

    # ===================== Data directories ==========================
    # Root directory containing SWOT WSE and WSE quality raster products.
    swot_root_dir = Path(r"path\to\SWOT")

    # Root directory containing maximum water body extent (inventory) for each site.
    inventory_root_dir = Path(r"path\to\Inventory")

    # Root directory containing monthly water body masks (formatted as yyyy_mm).
    waterbody_root_dir = Path(r"path\to\WaterBody")

    # Root directory containing processed ICESat-2 elevation samples
    # within the drawdown zone for each site.
    icesat2_root_dir = Path(r"path\to\ICESat-2")

    # Root directory for all output results, including reconstructed topography,
    # validation products, and log files.
    output_root_dir = Path(r"path\to\result")

    site_ids: List[str] = get_subfolder_names(str(swot_root_dir))
    logger.info(f"Discovered {len(site_ids)} sites under: {swot_root_dir}")

    for idx, site_id in enumerate(site_ids, start=1):
        logger.info(f"Progress: {idx}/{len(site_ids)}")
        try:
            run_single_site(
                site_id=site_id,
                swot_root_dir=swot_root_dir,
                inventory_root_dir=inventory_root_dir,
                waterbody_root_dir=waterbody_root_dir,
                icesat2_root_dir=icesat2_root_dir,
                output_root_dir=output_root_dir,
                std_sigma=std_sigma,
                qual_level=qual_level,
                enable_preprocessing=enable_preprocessing,
                logger=logger,
            )
        except Exception as exc:
            logger.exception(f"[FAIL] Site: {site_id} | Error: {exc}")

    logger.info("All sites processed.")


if __name__ == "__main__":
    main()

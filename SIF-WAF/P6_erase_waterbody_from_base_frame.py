# -*- coding: utf-8 -*-
import os
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

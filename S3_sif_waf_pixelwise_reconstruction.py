# -*- coding: utf-8 -*-
import os
import random
import arcpy
import numpy as np
import rasterio


def _process_pixels_with_filter_v3(std, max_array, data_arrays, nodata_value, max_meta, path4):
    """
    Apply block-wise outlier filtering (mean ± std * sigma) to a stack of rasters.

    Notes
    -----
    - This function writes per-layer filtered rasters to: {path4}/07_SIFed_tifs
    - NoData handling uses NaN and the sentinel value 99999 as defined in the original logic.
    """
    # Convert data_arrays to a NumPy array (if it is not already)
    data_arrays = np.array(data_arrays)

    # Initialize outputs (kept as-is per original logic)
    final_result = np.full(max_array.shape, np.nan)
    valid_pixel_counter = 0

    # Determine initial block size (kept as-is per original logic)
    initial_block_size = (min(max_array.shape) + 2 - 1) // 2
    if initial_block_size > 100:
        initial_block_size = 100

    block_size = initial_block_size
    iteration = 0

    # Iterate over decreasing block sizes until reaching the minimum threshold (kept as-is)
    while block_size > 3:
        block_size = max(initial_block_size // (2 ** iteration), 1)
        print(f"Processing with block size: {block_size}x{block_size} (Iteration: {iteration + 1})")
        iteration += 1

        # Process the raster in tiles/blocks
        for row_start in range(0, max_array.shape[0], block_size):
            for col_start in range(0, max_array.shape[1], block_size):
                row_end = min(row_start + block_size, max_array.shape[0])
                col_end = min(col_start + block_size, max_array.shape[1])

                # Extract current block
                max_block = max_array[row_start:row_end, col_start:col_end]
                data_block = data_arrays[:, row_start:row_end, col_start:col_end]

                # Flatten valid values within this block and track their original indices
                value_list = []
                index_map = {}

                for i in range(data_block.shape[1]):
                    for j in range(data_block.shape[2]):
                        pixel_values = data_block[:, i, j]

                        # Keep only valid values (exclude 99999 and NaNs)
                        valid_indices = np.where((pixel_values != 99999) & ~np.isnan(pixel_values))[0]
                        valid_values = pixel_values[valid_indices]

                        # Append valid values and store their original positions
                        for original_k, val in zip(valid_indices, valid_values):
                            idx = len(value_list)
                            value_list.append(val)
                            index_map[idx] = (original_k, i, j)

                value_array = np.array(value_list)

                # Skip blocks with no valid values
                if len(value_array) == 0:
                    continue

                # Compute filtering bounds
                mean_value = np.mean(value_array)
                std_value = np.std(value_array)
                max_value = np.max(value_array)
                min_value = np.min(value_array)
                lower_bound = mean_value - std * std_value
                upper_bound = mean_value + std * std_value

                # Flag outliers by setting them to the sentinel value 99999
                for idx, value in enumerate(value_list):
                    k, i, j = index_map[idx]
                    if value < lower_bound or value > upper_bound:
                        data_block[k, i, j] = 99999

                # Write the updated block back into the full stack
                data_arrays[:, row_start:row_end, col_start:col_end] = data_block

    # Ensure output folder exists
    filtered_tifs_path = os.path.join(path4, "07_SIFed_tifs")
    if not os.path.exists(filtered_tifs_path):
        os.makedirs(filtered_tifs_path)

    # Persist each filtered layer as an individual GeoTIFF
    for i in range(data_arrays.shape[0]):
        output_tif_path = os.path.join(filtered_tifs_path, f"filter_{i + 1}.tif")
        if os.path.exists(output_tif_path):
            os.remove(output_tif_path)

        _save_tif(data_arrays[i], max_meta, output_tif_path)

    return final_result, valid_pixel_counter


def _read_tif_files(max_tif_path, use_tif_folder):
    """
    Read the max-valid-pixel mask raster and load all GeoTIFF rasters from a folder.

    Returns
    -------
    max_array : np.ndarray
        Mask/reference array read from max_tif_path.
    data_arrays : list[np.ndarray]
        List of 2D arrays (one per input tif) with NoData converted to NaN.
    max_meta : dict
        Rasterio metadata from the max raster.
    nodata_value : float|int|None
        NoData value of the max raster.
    use_tif_files : list[str]
        Full paths of the read tif files in use_tif_folder.
    """
    with rasterio.open(max_tif_path) as max_tif:
        max_array = max_tif.read(1)
        max_meta = max_tif.meta
        nodata_value = max_tif.nodata

    use_tif_files = [os.path.join(use_tif_folder, f) for f in os.listdir(use_tif_folder) if f.endswith(".tif")]

    data_arrays = []
    for tif_file in use_tif_files:
        with rasterio.open(tif_file) as src:
            array = src.read(1)

            # Convert NoData to NaN
            valid_array = np.where(array == src.nodata, np.nan, array)

            # Only accept 2D rasters
            if valid_array.ndim == 2:
                data_arrays.append(valid_array)

    return max_array, data_arrays, max_meta, nodata_value, use_tif_files


def _save_tif(final_result, max_meta, output_tif_path):
    """
    Save a single-band float32 GeoTIFF using rasterio metadata.

    Notes
    -----
    - The output uses NaN as nodata, matching the original logic.
    """
    max_meta.update(dtype=rasterio.float32, count=1, nodata=np.nan)
    with rasterio.open(output_tif_path, "w", **max_meta) as dest:
        dest.write(final_result.astype(rasterio.float32), 1)


def _process_pixels_with_std_mid(max_array, data_arrays, nodata_value):
    """
    Per-pixel robust aggregation:
    - Keep values within ±2σ of the mean (excluding NaN and sentinel 99999)
    - Use the median of filtered values as the final estimate
    """
    data_arrays = np.array(data_arrays)
    final_result = np.full(max_array.shape, np.nan)

    valid_pixel_counter = 0

    for row in range(max_array.shape[0]):
        for col in range(max_array.shape[1]):
            max_value = max_array[row, col]

            if np.isnan(max_value) or max_value == nodata_value:
                continue

            pixel_values = data_arrays[:, row, col]
            valid_values = pixel_values[~np.isnan(pixel_values) & (pixel_values != 99999)]

            if len(valid_values) < 3:
                continue

            mean_value = np.mean(valid_values)
            std_dev = np.std(valid_values)

            filtered_values = valid_values[
                (valid_values >= mean_value - 2 * std_dev) & (valid_values <= mean_value + 2 * std_dev)
            ]

            if len(filtered_values) == 0:
                continue

            final_value = np.median(filtered_values)
            final_result[row, col] = final_value
            valid_pixel_counter += 1

    return final_result, valid_pixel_counter


def _read_tif_files_mid(max_tif_path, use_tif_folder):
    """
    Read the max-valid-pixel raster and all GeoTIFF rasters from the given folder.
    """
    with rasterio.open(max_tif_path) as max_tif:
        max_array = max_tif.read(1)
        max_meta = max_tif.meta
        nodata_value = max_tif.nodata

    use_tif_files = [os.path.join(use_tif_folder, f) for f in os.listdir(use_tif_folder) if f.endswith(".tif")]

    data_arrays = []
    error_arrays = []

    for tif_file in use_tif_files:
        with rasterio.open(tif_file) as src:
            array = src.read(1)
            valid_array = np.where(array == src.nodata, np.nan, array)
            data_arrays.append(valid_array)

            tif_filename = os.path.basename(tif_file)

    return max_array, data_arrays, max_meta, nodata_value, use_tif_files


def _check_shp_feature_count(shp_path, a):
    """
    Check whether a shapefile contains at least `a` features.

    Parameters
    ----------
    shp_path : str
        Path to a shapefile.
    a : int
        Minimum required feature count.

    Returns
    -------
    bool
        True if feature count >= a; otherwise False.
    """
    try:
        result = arcpy.GetCount_management(shp_path)
        count = int(result.getOutput(0))
    except Exception as e:
        arcpy.AddError(f"Unable to get feature count: {e}")
        return False

    return count >= a


def _process_pixels_with_WA_v3(max_array, data_arrays, error_arrays, nodata_value):
    """
    Per-pixel weighted aggregation:
    - Remove sentinel values (99999) and None errors
    - Keep a fraction of lowest-error observations (percent_keep)
    - Compute weighted average using weights = 1 / error
    """
    percent_keep = 0.9
    data_arrays = np.array(data_arrays)
    final_result = np.full(max_array.shape, np.nan)
    valid_pixel_counter = 0

    print(data_arrays.shape)
    print(max_array.shape)

    for row in range(max_array.shape[0]):
        for col in range(max_array.shape[1]):
            max_value = max_array[row, col]

            if np.isnan(max_value) or max_value == nodata_value:
                continue

            pixel_values = data_arrays[:, row, col].tolist()
            pixel_errors = error_arrays

            valid_mask = [value != 99999 for value in pixel_values]
            valid_values = [value for value, valid in zip(pixel_values, valid_mask) if valid]
            valid_errors = [error for error, valid in zip(pixel_errors, valid_mask) if valid]

            filtered_values = []
            filtered_errors = []
            for value, error in zip(valid_values, valid_errors):
                if error is not None:
                    filtered_values.append(value)
                    filtered_errors.append(error)

            num_to_keep = max(1, int(len(filtered_errors) * percent_keep))
            sorted_indices = np.argsort(filtered_errors)
            selected_indices = sorted_indices[:num_to_keep]

            filtered_values = [filtered_values[i] for i in selected_indices]
            filtered_errors = [filtered_errors[i] for i in selected_indices]

            filtered_values = np.array(filtered_values)
            filtered_errors = np.array(filtered_errors)

            weights = 1 / filtered_errors
            weights /= np.sum(weights)

            final_value = np.sum(filtered_values * weights)
            if final_value == 0:
                continue

            final_result[row, col] = final_value
            valid_pixel_counter += 1

    return final_result, valid_pixel_counter


def _extract_and_calculate_error_v3(path4, shp_file, percent, random_state=42):
    """
    Build train/validation splits from an input point shapefile and compute per-TIF mean absolute errors
    by sampling extracted raster values onto the training points.

    Returns
    -------
    tif_error_dict : dict[str, float|None]
        Mapping from tif filename -> mean error (or None if unavailable).
    train_shp_name : str
        Filename of the generated training shapefile (basename only).
    """
    if random_state is not None:
        random.seed(random_state)

    shp_folder, shp_name = os.path.split(shp_file)
    shp_name_no_ext = os.path.splitext(shp_name)[0]

    target_folder = os.path.join(path4, "08_weight_valid_shp_copy")
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    filtered_shp = os.path.join(shp_folder, f"{shp_name_no_ext}_filtered.shp")
    if arcpy.Exists(filtered_shp):
        arcpy.Delete_management(filtered_shp)

    arcpy.MakeFeatureLayer_management(shp_file, "layer")
    arcpy.SelectLayerByAttribute_management("layer", "NEW_SELECTION", "h_uncer <= 7.5")
    arcpy.CopyFeatures_management("layer", filtered_shp)
    arcpy.Delete_management("layer")

    oid_field_name = arcpy.Describe(filtered_shp).OIDFieldName

    total_points = int(arcpy.GetCount_management(filtered_shp).getOutput(0))
    train_count = int(total_points * percent)

    train_shp = os.path.join(shp_folder, f"{shp_name_no_ext}_train.shp")
    valid_shp = os.path.join(shp_folder, f"{shp_name_no_ext}_valid.shp")

    if arcpy.Exists(train_shp):
        arcpy.Delete_management(train_shp)
    if arcpy.Exists(valid_shp):
        arcpy.Delete_management(valid_shp)

    with arcpy.da.UpdateCursor(filtered_shp, [oid_field_name]) as cursor:
        oids = [row[0] for row in cursor]

    train_oids = set(random.sample(oids, train_count))

    arcpy.MakeFeatureLayer_management(filtered_shp, "filtered_layer")
    arcpy.SelectLayerByAttribute_management(
        "filtered_layer", "NEW_SELECTION", f"{oid_field_name} IN ({','.join(map(str, train_oids))})"
    )
    arcpy.CopyFeatures_management("filtered_layer", train_shp)
    arcpy.SelectLayerByAttribute_management("filtered_layer", "SWITCH_SELECTION")
    arcpy.CopyFeatures_management("filtered_layer", valid_shp)
    arcpy.Delete_management("filtered_layer")

    output_shp = os.path.join(target_folder, "Cal_Weight.shp")
    if arcpy.Exists(output_shp):
        arcpy.Delete_management(output_shp)
    arcpy.CopyFeatures_management(train_shp, output_shp)

    tif_folder = os.path.join(path4, "07_SIFed_tifs")
    tif_files = [f for f in os.listdir(tif_folder) if f.lower().endswith(".tif")]
    tif_field_mapping = {}

    for index, tif in enumerate(tif_files):
        tif_path = os.path.join(tif_folder, tif)
        field_name = f"T{index + 1:03d}"
        tif_field_mapping[field_name] = tif
        arcpy.sa.ExtractMultiValuesToPoints(output_shp, [[tif_path, field_name]], "NONE")

        error_field = f"Err_{index + 1:03d}"
        arcpy.AddField_management(output_shp, error_field, "DOUBLE")

        with arcpy.da.UpdateCursor(output_shp, [field_name, "h_08", "h_te_best", error_field]) as cursor:
            for row in cursor:
                tif_value = row[0]
                egm08 = row[1]
                h_te_best = row[2]
                if tif_value is not None and egm08 is not None and h_te_best is not None:
                    row[3] = abs(tif_value - egm08)
                else:
                    row[3] = None
                cursor.updateRow(row)

    error_averages = {}
    fields = arcpy.ListFields(output_shp)
    for field in fields:
        if field.name.startswith("Err_"):
            with arcpy.da.SearchCursor(output_shp, [field.name]) as cursor:
                error_values = [row[0] for row in cursor if row[0] is not None and row[0] <= 1000]
                if error_values:
                    average_error = sum(error_values) / len(error_values)
                    error_averages[field.name] = average_error

    tif_error_dict = {}
    for field_name, tif in tif_field_mapping.items():
        error_field = f"Err_{field_name[1:]}"
        average_error = error_averages.get(error_field, None)
        tif_error_dict[tif] = average_error

    return tif_error_dict, f"{shp_name_no_ext}_train.shp"


def _read_tif_files_WA(max_tif_path, use_tif_folder, tif_error_dict):
    """
    Read rasters and attach a per-file scalar error value (looked up by filename),
    returning error_arrays as a list aligned with use_tif_files.
    """
    with rasterio.open(max_tif_path) as max_tif:
        max_array = max_tif.read(1)
        max_meta = max_tif.meta
        nodata_value = max_tif.nodata

    use_tif_files = [os.path.join(use_tif_folder, f) for f in os.listdir(use_tif_folder) if f.endswith(".tif")]

    data_arrays = []
    error_arrays = []

    for tif_file in use_tif_files:
        with rasterio.open(tif_file) as src:
            array = src.read(1)
            valid_array = np.where(array == src.nodata, np.nan, array)
            data_arrays.append(valid_array)

            tif_filename = os.path.basename(tif_file)
            error_value = tif_error_dict.get(tif_filename, np.nan)
            error_arrays.append(error_value)

    for tif_file, error in zip(use_tif_files, error_arrays):
        continue

    return max_array, data_arrays, error_arrays, max_meta, nodata_value, use_tif_files


def P12_run_sif_waf_reconstruction(std, path4, path5, method):
    """
    Run SIF/WAF reconstruction workflow.

    Parameters
    ----------
    std : float
        Standard deviation multiplier used by SIF filtering (mean ± std * sigma).
    path4 : str
        Project root directory.
    path5 : str
        Path to ICESat-2 validation shapefile (or folder as used in original logic).
    method : str
        Either "WAF" or "SIF" (other values follow the original branching logic).

    Returns
    -------
    bool
        Whether WAF mode was applied (True) or a fallback method was used (False).
    """
    WAF_or_Not = False

    if method == "WAF":
        max_tif_path = os.path.join(path4, "05_Max_Tif_1", "max_valid_pixel_range_Clip.tif")
        use_tif_folder = os.path.join(path4, "07_SIFed_tifs")

        if os.path.exists(path5):
            tif_error_dict, ICESat_2_train_name = _extract_and_calculate_error_v3(path4, path5, 0.7)
            ICESat_2_train = os.path.join(path5, ICESat_2_train_name)
            WAF_or_Not = _check_shp_feature_count(ICESat_2_train, 20)

            if WAF_or_Not:
                max_array, data_arrays, error_arrays, max_meta, nodata_value, valid_tif_num = _read_tif_files_WA(
                    max_tif_path, use_tif_folder, tif_error_dict
                )
                final_result, valid_pixel_counter = _process_pixels_with_WA_v3(
                    max_array, data_arrays, error_arrays, nodata_value
                )
            else:
                max_array, data_arrays, max_meta, nodata_value, valid_tif_num = _read_tif_files_mid(
                    max_tif_path, use_tif_folder
                )
                final_result, valid_pixel_counter = _process_pixels_with_std_mid(
                    max_array, data_arrays, nodata_value
                )
        else:
            max_array, data_arrays, max_meta, nodata_value, valid_tif_num = _read_tif_files_mid(
                max_tif_path, use_tif_folder
            )
            final_result, valid_pixel_counter = _process_pixels_with_std_mid(max_array, data_arrays, nodata_value)

        final_tif_folder = os.path.join(path4, "09_Initial_reconstructed_tif")
        if not os.path.exists(final_tif_folder):
            os.makedirs(final_tif_folder)

        output_tif_path = os.path.join(final_tif_folder, "New_One_Tif.tif")
        _save_tif(final_result, max_meta, output_tif_path)

        return WAF_or_Not

    else:
        max_tif_path = os.path.join(path4, "05_Max_Tif_1", "max_valid_pixel_range_Clip.tif")
        use_tif_folder = os.path.join(path4, "06_Expanded_tifs")

        max_array, data_arrays, max_meta, nodata_value, valid_tif_num = _read_tif_files(max_tif_path, use_tif_folder)

        if method == "SIF":
            _process_pixels_with_filter_v3(std, max_array, data_arrays, nodata_value, max_meta, path4)

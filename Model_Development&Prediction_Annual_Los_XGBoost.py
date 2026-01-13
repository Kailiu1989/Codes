import os
import numpy as np
import pandas as pd
from tqdm import tqdm
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
from sklearn.model_selection import train_test_split


# Evaluation Metrics Definitions
def smape(y_true, y_pred):
    """
    Calculate Symmetric Mean Absolute Percentage Error (SMAPE).

    Parameters:
        y_true (array-like): True values.
        y_pred (array-like): Predicted values.

    Returns:
        float: SMAPE percentage.
    """
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    diff = np.abs(y_true - y_pred) / denominator
    diff[denominator == 0] = 0.0
    return 100.0 * np.mean(diff)


def mape(y_true, y_pred):
    """
    Calculate Mean Absolute Percentage Error (MAPE).

    Parameters:
        y_true (array-like): True values.
        y_pred (array-like): Predicted values.

    Returns:
        float: MAPE percentage.
    """
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    non_zero = y_true != 0
    return np.mean(np.abs((y_true[non_zero] - y_pred[non_zero]) / y_true[non_zero])) * 100


def nse(y_true, y_pred):
    """
    Calculate Nash-Sutcliffe Efficiency (NSE).

    Parameters:
        y_true (array-like): True values.
        y_pred (array-like): Predicted values.

    Returns:
        float: NSE value.
    """
    return 1 - (np.sum((y_true - y_pred) ** 2) / np.sum((y_true - np.mean(y_true)) ** 2))


def rmse(y_true, y_pred):
    """
    Calculate Root Mean Squared Error (RMSE).

    Parameters:
        y_true (array-like): True values.
        y_pred (array-like): Predicted values.

    Returns:
        float: RMSE value.
    """
    return np.sqrt(mean_squared_error(y_true, y_pred))


# Feature Variables
FEATURES = [
    'Longitude', 'Latitude', 'LnArea', 'LnPerimeter', 'ShaIndex', 'Roundness',
    'AreaRatio', 'Elevation', 'Lithology', 'Landform', 'SoilType',
    'ClimateType', 'GlaCovered', 'Continent', 'Basin', 'Endorheic',
    'Slope', 'Curvature', 'TWI', 'EleDiff', 'Permeability',
    'Porosity', 'Sand', 'Silt', 'Clay', 'LnCatArea',
    'LnRecharge', 'CatSlope', 'R-factor', 'K-factor',
    'SoilErosion', 'Temp', 'Pre', 'Eva',
    'Wind', 'Aridity', 'NDVI', 'Bare', 'Cropland',
    'Grass', 'Tree', 'Lmp', 'NTL', 'Pop',
    'RivOrder', 'RivSlope', 'RivRunoff', 'RivSediment', 'Flood'
]

# File Paths
INPUT_FILE = r"path/to/input_data.csv"  # Path to the input CSV file containing training data
OUTPUT_FILE = r"path/to/output_results.csv"  # Path to save the grid search results and evaluation metrics
NEW_DATA_FILE = r"path/to/new_data.xlsx"  # Path to the Excel file containing new data for making predictions
PREDICTED_RESULTS_FILE = r"path/to/predicted_results.xlsx"  # Path to save the prediction results

# Hyperparameter Grid (Set to specific values; modify as needed for grid search)
HYPERPARAM_GRID = {
    'n_estimators': range(0, 1001, 5),
    'max_depth': range(0, 51, 5),
    'min_child_weight': range(0, 51, 5),
    'learning_rate': [0.01, 0.02, 0.05, 0.1, 0.2],
    'subsample': [0.5, 0.7, 1],
    'colsample_bytree': [0.5, 0.7, 1],
    'gamma': [0, 1, 2],
    'random_state': [42],
}


def main():
    # Load input data
    data = pd.read_csv(INPUT_FILE)
    X = data[FEATURES].values
    y = data['Annual_Los'].values

    # Calculate total number of hyperparameter combinations
    total_combinations = np.prod([len(v) for v in HYPERPARAM_GRID.values()])

    # Initialize progress bar
    progress_bar = tqdm(total=total_combinations, desc="Grid Search Progress")

    # Open the result CSV file and write headers if it does not exist
    headers = (
        "n_estimators,max_depth,min_child_weight,learning_rate,subsample,"
        "colsample_bytree,gamma,random_state,average_mae,average_rmse,average_nse,"
        "average_mape,average_smape,average_r2,train_mae,train_rmse,train_nse,"
        "train_mape,train_smape,train_r2,test_mae,test_rmse,test_nse,test_mape,"
        "test_smape,test_r2\n"
    )
    if not os.path.isfile(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'w') as file:
            file.write(headers)

    # Iterate over all hyperparameter combinations
    for n_estimators in HYPERPARAM_GRID['n_estimators']:
        for max_depth in HYPERPARAM_GRID['max_depth']:
            for min_child_weight in HYPERPARAM_GRID['min_child_weight']:
                for learning_rate in HYPERPARAM_GRID['learning_rate']:
                    for subsample in HYPERPARAM_GRID['subsample']:
                        for colsample_bytree in HYPERPARAM_GRID['colsample_bytree']:
                            for gamma in HYPERPARAM_GRID['gamma']:
                                for random_state in HYPERPARAM_GRID['random_state']:
                                    # Update progress bar
                                    progress_bar.update(1)

                                    # Split data into training and testing sets
                                    X_train_full, X_test, y_train_full, y_test = train_test_split(
                                        X, y, test_size=0.3, random_state=random_state
                                    )

                                    # Initialize lists to store metrics for cross-validation
                                    mae_list = []
                                    r2_list = []
                                    smape_list = []
                                    nse_list = []
                                    mape_list = []
                                    rmse_list = []

                                    # Perform 10-fold cross-validation
                                    for fold in range(10):
                                        # Further split training data into training and validation sets
                                        X_train, X_val, y_train, y_val = train_test_split(
                                            X_train_full, y_train_full, test_size=0.3, random_state=fold * 10
                                        )

                                        # Initialize and train the XGBoost regressor with current hyperparameters
                                        model = XGBRegressor(
                                            n_estimators=n_estimators,
                                            max_depth=max_depth,
                                            min_child_weight=min_child_weight,
                                            learning_rate=learning_rate,
                                            subsample=subsample,
                                            colsample_bytree=colsample_bytree,
                                            gamma=gamma,
                                            random_state=42,
                                        )
                                        model.fit(X_train, y_train)

                                        # Predict on the validation set
                                        y_val_pred = model.predict(X_val)

                                        # Calculate and store evaluation metrics
                                        mae_list.append(mean_absolute_error(y_val, y_val_pred))
                                        r2_list.append(r2_score(y_val, y_val_pred))
                                        nse_list.append(nse(y_val, y_val_pred))
                                        smape_list.append(smape(y_val, y_val_pred))
                                        rmse_list.append(rmse(y_val, y_val_pred))
                                        mape_list.append(mape(y_val, y_val_pred))

                                    # Calculate average metrics across all folds
                                    average_metrics = {
                                        'average_mae': np.mean(mae_list),
                                        'average_r2': np.mean(r2_list),
                                        'average_nse': np.mean(nse_list),
                                        'average_smape': np.mean(smape_list),
                                        'average_rmse': np.mean(rmse_list),
                                        'average_mape': np.mean(mape_list)
                                    }

                                    # Display average cross-validation metrics
                                    print(f"Average Validation MAE: {average_metrics['average_mae']}")
                                    print(f"Average Validation R2: {average_metrics['average_r2']}")
                                    print(f"Average Validation NSE: {average_metrics['average_nse']}")
                                    print(f"Average Validation SMAPE: {average_metrics['average_smape']}")
                                    print(f"Average Validation RMSE: {average_metrics['average_rmse']}")
                                    print(f"Average Validation MAPE: {average_metrics['average_mape']}")

                                    # Train the model on the full training set
                                    final_model = XGBRegressor(
                                        n_estimators=n_estimators,
                                        max_depth=max_depth,
                                        min_child_weight=min_child_weight,
                                        learning_rate=learning_rate,
                                        subsample=subsample,
                                        colsample_bytree=colsample_bytree,
                                        gamma=gamma,
                                        random_state=42,
                                    )
                                    final_model.fit(X_train_full, y_train_full)

                                    # Predict on training and testing sets
                                    y_train_pred = final_model.predict(X_train_full)
                                    y_test_pred = final_model.predict(X_test)

                                    # Calculate evaluation metrics for training and testing sets
                                    train_metrics = {
                                        'train_mae': mean_absolute_error(y_train_full, y_train_pred),
                                        'train_rmse': rmse(y_train_full, y_train_pred),
                                        'train_nse': nse(y_train_full, y_train_pred),
                                        'train_smape': smape(y_train_full, y_train_pred),
                                        'train_mape': mape(y_train_full, y_train_pred),
                                        'train_r2': r2_score(y_train_full, y_train_pred)
                                    }

                                    test_metrics = {
                                        'test_mae': mean_absolute_error(y_test, y_test_pred),
                                        'test_rmse': rmse(y_test, y_test_pred),
                                        'test_nse': nse(y_test, y_test_pred),
                                        'test_smape': smape(y_test, y_test_pred),
                                        'test_mape': mape(y_test, y_test_pred),
                                        'test_r2': r2_score(y_test, y_test_pred)
                                    }

                                    # Display training and testing metrics
                                    print("XGBoost Model Evaluation:")
                                    print(
                                        f"Training MAE: {train_metrics['train_mae']}, Testing MAE: {test_metrics['test_mae']}")
                                    print(
                                        f"Training RMSE: {train_metrics['train_rmse']}, Testing RMSE: {test_metrics['test_rmse']}")
                                    print(
                                        f"Training NSE: {train_metrics['train_nse']}, Testing NSE: {test_metrics['test_nse']}")
                                    print(
                                        f"Training MAPE: {train_metrics['train_mape']}, Testing MAPE: {test_metrics['test_mape']}")
                                    print(
                                        f"Training SMAPE: {train_metrics['train_smape']}, Testing SMAPE: {test_metrics['test_smape']}")
                                    print(
                                        f"Training R2: {train_metrics['train_r2']}, Testing R2: {test_metrics['test_r2']}")

                                    # Prepare data row for results CSV
                                    results_row = (
                                        f"{n_estimators},{max_depth},{min_child_weight},{learning_rate},{subsample},"
                                        f"{colsample_bytree},{gamma},{random_state},"
                                        f"{average_metrics['average_mae']},{average_metrics['average_rmse']},"
                                        f"{average_metrics['average_nse']},{average_metrics['average_mape']},"
                                        f"{average_metrics['average_smape']},{average_metrics['average_r2']},"
                                        f"{train_metrics['train_mae']},{train_metrics['train_rmse']},"
                                        f"{train_metrics['train_nse']},{train_metrics['train_mape']},"
                                        f"{train_metrics['train_smape']},{train_metrics['train_r2']},"
                                        f"{test_metrics['test_mae']},{test_metrics['test_rmse']},"
                                        f"{test_metrics['test_nse']},{test_metrics['test_mape']},"
                                        f"{test_metrics['test_smape']},{test_metrics['test_r2']}\n"
                                    )

                                    # Append the results to the CSV file
                                    with open(OUTPUT_FILE, 'a') as file:
                                        file.write(results_row)

                                    # Load new data for prediction
                                    new_data = pd.read_excel(NEW_DATA_FILE, sheet_name='sheet1')

                                    # Replace placeholder strings for missing values with NaN
                                    na_markers = ["<blank>", "<empty>", "<空>", "NA", "N/A", "null", "None", "-", ""]
                                    new_data.replace(na_markers, np.nan, inplace=True)

                                    # Convert all values to numeric; invalid parsing becomes NaN
                                    new_data = new_data.apply(pd.to_numeric, errors="coerce")

                                    # Select only the features used in the model
                                    new_data_features = new_data[FEATURES]

                                    # Predict using the trained model
                                    predicted_annual_los = final_model.predict(new_data_features.values)

                                    # Create a DataFrame for the predictions
                                    predicted_df = pd.DataFrame({
                                        'ID': new_data['ID'],  # Ensure 'ID' column exists; adjust if necessary
                                        'Predicted_Annual_Los': predicted_annual_los
                                    })

                                    # Save predictions to an Excel file
                                    predicted_df.to_excel(PREDICTED_RESULTS_FILE, index=False)
                                    print(f"Predictions completed and saved to: {PREDICTED_RESULTS_FILE}")

    # Close the progress bar
    progress_bar.close()

if __name__ == "__main__":
    main()

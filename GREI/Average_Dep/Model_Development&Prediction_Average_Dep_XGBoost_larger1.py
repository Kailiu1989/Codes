# -*- coding: utf-8 -*-
import os
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import r2_score
from sklearn import metrics


# -----------------------------------------------------------------------------
# File paths (relative paths only)
# -----------------------------------------------------------------------------
INPUT_FILE = r"path/to/input_data_larger1.xlsx"  # Path to the input CSV file containing training data
NEW_DATA_FILE = r"path/to/new_data_larger1.xlsx"  # Path to the Excel file containing new data for making predictions
PREDICTED_RESULTS_FILE = r"path/to/predicted_results_larger1.xlsx"  # Path to save the prediction results


# -----------------------------------------------------------------------------
# Evaluation metric functions
# -----------------------------------------------------------------------------
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

def calculate_mape(y_true, y_pred):
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

def calculate_nse(y_true, y_pred):
    """
     Calculate Nash-Sutcliffe Efficiency (NSE).

     Parameters:
         y_true (array-like): True values.
         y_pred (array-like): Predicted values.

     Returns:
         float: NSE value.
     """
    return 1 - (np.sum((y_true - y_pred) ** 2) / np.sum((y_true - np.mean(y_true)) ** 2))

def calculate_rmse(y_true, y_pred):
    """
    Calculate Root Mean Squared Error (RMSE).

    Parameters:
        y_true (array-like): True values.
        y_pred (array-like): Predicted values.

    Returns:
        float: RMSE value.
    """
    return np.sqrt(metrics.mean_squared_error(y_true, y_pred))


# -----------------------------------------------------------------------------
# Data loading and preprocessing (training data)
# -----------------------------------------------------------------------------
all_data = pd.read_csv(INPUT_FILE)

# Inspect missing values
missing_values = all_data.isnull().sum()
print(missing_values)

# Replace placeholder strings with NaN
all_data.replace('<空>', np.nan, inplace=True)

# Mean imputation for numeric columns
all_data.fillna(all_data.mean(numeric_only=True), inplace=True)

# Feature variables
FEATURES = [
    'Longitude', 'Latitude', 'LgArea', 'LgPerimeter', 'ShaIndex', 'Roundness', 'AreaRatio',
    'Lithology', 'Landform', 'SoilType', 'ClimateType', 'GlaCovered', 'Continent', 'Basin', 'Endorheic',
    'Slope', 'Curvature', 'TWI', 'EleDiff', 'Permeability', 'Porosity', 'Sand', 'Silt', 'Clay',
    'LgCatArea', 'LgRecharge', 'Temp', 'Pre', 'Eva', 'Wind', 'Aridity', 'Lmp', 'NTL', 'Pop',
    'RivOrder', 'RivSlope', 'RivRunoff'
]

X = all_data[FEATURES].values
Y = all_data['LgAverage_Dep'].values

# Sample identifiers (assumes an "ID" column exists)
IDs = all_data['ID'].values

# Train-test split
X_train, X_test, y_train, y_test, ids_train, ids_test = train_test_split(
    X, Y, IDs, test_size=0.3, random_state=42
)


# -----------------------------------------------------------------------------
# Model training (XGBoost + GridSearchCV)
# -----------------------------------------------------------------------------
xgb_model = xgb.XGBRegressor()

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

grid_search = GridSearchCV(
    estimator=xgb_model,
    param_grid=HYPERPARAM_GRID,
    scoring='r2',
    refit=True,
    return_train_score=True,
    cv=5,
    verbose=2,
    n_jobs=-1
)

grid_search.fit(X_train, y_train)

best_model = grid_search.best_estimator_

print(f"Best parameters: {grid_search.best_params_}")
print(f"Best cross-validated R2: {grid_search.best_score_}")

# Predictions
y_pred_train = best_model.predict(X_train)
y_pred_test = best_model.predict(X_test)

# -----------------------------------------------------------------------------
# Performance evaluation
# -----------------------------------------------------------------------------
train_smape = smape(y_train, y_pred_train)
test_smape = smape(y_test, y_pred_test)
train_r2 = r2_score(y_train, y_pred_train)
test_r2 = r2_score(y_test, y_pred_test)
train_mape = calculate_mape(y_train, y_pred_train)
test_mape = calculate_mape(y_test, y_pred_test)
train_nse = calculate_nse(y_train, y_pred_train)
test_nse = calculate_nse(y_test, y_pred_test)
train_rmse = calculate_rmse(y_train, y_pred_train)
test_rmse = calculate_rmse(y_test, y_pred_test)
train_mae = metrics.mean_absolute_error(y_train, y_pred_train)
test_mae = metrics.mean_absolute_error(y_test, y_pred_test)

print(f"Training SMAPE: {train_smape}, Testing SMAPE: {test_smape}")
print(f"Training MAPE: {train_mape}, Testing MAPE: {test_mape}")
print(f"Training NSE: {train_nse}, Testing NSE: {test_nse}")
print(f"Training R^2: {train_r2}, Testing R^2: {test_r2}")
print(f"Training MAE: {train_mae}, Testing MAE: {test_mae}")
print(f"Training RMSE: {train_rmse}, Testing RMSE: {test_rmse}")


# -----------------------------------------------------------------------------
# Prediction for new samples
# -----------------------------------------------------------------------------
new_data = pd.read_excel(NEW_DATA_FILE, sheet_name='Sheet1')

# Replace placeholder strings with NaN
new_data.replace('<空>', np.nan, inplace=True)

# Cast all columns to numeric; non-numeric entries are coerced to NaN
new_data = new_data.apply(pd.to_numeric, errors='coerce')

# Ensure feature alignment and apply mean imputation
new_data_vars = new_data[FEATURES]
new_data_vars = new_data_vars.fillna(new_data_vars.mean(numeric_only=True))

# Generate predictions
predicted_values = best_model.predict(new_data_vars.values)

# Save predictions with IDs
predicted_results_df = pd.DataFrame({
    'ID': new_data['ID'],
    'Predicted_xgboost': predicted_values
})

predicted_results_df.to_excel(PREDICTED_RESULTS_FILE, index=False)
print("Predictions completed and saved to:", PREDICTED_RESULTS_FILE)

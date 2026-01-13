XGBoost Regression Pipeline for Average_Dep (Grid Search + Cross-Validation + Prediction) (Two Models by Area Threshold: >1 and <1)
====================================
Overview
This repository provides two Python scripts that:
1) Load labeled training datasets from Excel files.
2) Train an XGBoost regressor (XGBRegressor) to predict Average_Dep (log-transformed target in code: LgAverage_Dep) using a fixed set of geospatial / environmental predictors (FEATURES).
3) Tune model hyperparameters using GridSearchCV with 5-fold cross-validation (scoring = R2).
4) Evaluate the best model using:
   - a hold-out test split (30% test), and
   - cross-validated performance reported by GridSearchCV.
5) Print multiple evaluation metrics for both training and testing sets (R2, SMAPE, MAPE, NSE, MAE, RMSE).
6) Load a separate Excel file containing new samples and output predicted values to an Excel file.

Two separate pipelines are provided to handle different reservoir/lake size groups:
- Area > 1  (larger1 model)
- Area < 1  (less1 model)

====================================
Intended use
Producing reproducible, publication-quality model tuning/evaluation results and applying the trained model to independent/new samples for Average_Dep prediction, using separate models for large-area and small-area groups.

====================================
Folder contents (example test files)
This folder includes two modeling scripts and corresponding example input files:

Modeling scripts:
- Model_Development&Prediction_Average_Dep_XGBoost_larger1.py   (for Area > 1)
- Model_Development&Prediction_Average_Dep_XGBoost_less1.py     (for Area < 1)

Example datasets: (The complete training datasets cannot be made publicly available due to confidentiality reasons. These example datasets is only used for code testing.)
- Training_larger1.xlsx     (training dataset for Area > 1)
- Predicting_larger1.xlsx   (new samples for prediction; Area > 1)

- Training_less1.xlsx       (training dataset for Area < 1)
- Predicting_less1.xlsx     (new samples for prediction; Area < 1)

You may directly set:
- INPUT_FILE to point to the corresponding Training_*.xlsx
- NEW_DATA_FILE to point to the corresponding Predicting_*.xlsx

Examples:
INPUT_FILE = r"path/to/Training_larger1.xlsx"
NEW_DATA_FILE = r"path/to/Predicting_larger1.xlsx"

INPUT_FILE = r"path/to/Training_less1.xlsx"
NEW_DATA_FILE = r"path/to/Predicting_less1.xlsx"

====================================
Requirements
Python packages:
- numpy
- pandas
- xgboost
- scikit-learn
- openpyxl (required for reading/writing .xlsx via pandas)

Installation:
pip install numpy pandas xgboost scikit-learn openpyxl

====================================
User configuration (file paths)
Edit the following variables in each script:

INPUT_FILE = r"path/to/Training_*.xlsx"
NEW_DATA_FILE = r"path/to/Predicting_*.xlsx"
PREDICTED_RESULTS_FILE = r"path/to/predicted_results_*.xlsx"

Recommended mapping:
(1) Area > 1 model (larger1)
- Script: Model_Development&Prediction_Average_Dep_XGBoost_larger1.py
- INPUT_FILE: Training_larger1.xlsx
- NEW_DATA_FILE: Predicting_larger1.xlsx
- PREDICTED_RESULTS_FILE: predicted_results_larger1.xlsx

(2) Area < 1 model (less1)
- Script: Model_Development&Prediction_Average_Dep_XGBoost_less1.py
- INPUT_FILE: Training_less1.xlsx
- NEW_DATA_FILE: Predicting_less1.xlsx
- PREDICTED_RESULTS_FILE: predicted_results_less1.xlsx

====================================
Input and output specifications

(1) INPUT_FILE (training data; Excel)
The Excel file must contain:
- all feature columns listed in FEATURES
- the target column: LgAverage_Dep
- an identifier column: ID

Missing values handling (training):
- the placeholder string "<空>" is replaced with NaN
- numeric NaNs are filled with column means (mean imputation)

Model split:
- the script uses a 30% hold-out test split (train_test_split with test_size=0.3, random_state=42)

(2) Grid search / cross-validation (internal)
Hyperparameter tuning:
- GridSearchCV with 5-fold CV (cv=5)
- scoring = R2
The script prints:
- best parameters (grid_search.best_params_)
- best cross-validated R2 (grid_search.best_score_)

(3) NEW_DATA_FILE (new samples for prediction; Excel)
The Excel file must contain:
- the same feature columns as FEATURES
- an identifier column: ID

Missing values handling (new samples):
- "<空>" is replaced with NaN
- all columns are coerced to numeric (errors="coerce")
- remaining NaNs are filled with column means computed within the new dataset

(4) PREDICTED_RESULTS_FILE (prediction outputs; Excel)
The output Excel file will contain:
- ID
- Predicted_xgboost   (predicted values of LgAverage_Dep)

====================================
Notes
- This repository includes two separate scripts to model Average_Dep for different area regimes (>1 vs <1). Please use the matching Training_* and Predicting_* files with the corresponding script.
- The target variable in the script is named LgAverage_Dep (log-transformed Average_Dep). The prediction output column is Predicted_xgboost, which corresponds to predicted LgAverage_Dep.

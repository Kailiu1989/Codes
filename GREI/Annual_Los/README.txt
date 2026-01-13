XGBoost Regression Pipeline for Annual_Los (Grid Search + Cross-Validation + Prediction)
====================================
Overview
This repository provides a Python script that:
1) Loads a labeled dataset from a CSV file.
2) Trains an XGBoost regressor (XGBRegressor) to predict Annual_Los using a fixed set of geospatial / environmental / socio-economic predictors (FEATURES).
3) Performs a manual grid search over user-defined hyperparameters.
4) Evaluates each hyperparameter combination using:
   - a hold-out test split (30% test), and
   - a repeated validation split (10 rounds) on the training portion to compute average validation metrics.
5) Writes all evaluation results to a CSV file.
6) Loads a separate Excel file containing new samples and outputs predicted Annual_Los values to an Excel file.
====================================
Intended use
Producing reproducible, publication-quality model evaluation tables and applying the trained model to independent/new samples.
====================================
Folder contents (example test files)
This folder includes one modeling scripts and corresponding example input files:

Modeling scripts: 
Model_Development&Prediction_Annual_Los_XGBoost.py

Example datasets: (The complete training datasets cannot be made publicly available due to confidentiality reasons. These example datasets is only used for code testing.)
- Training.csv     (example training dataset)
- Predicting.xlsx   (example dataset for prediction)

You may directly set:
- INPUT_FILE to point to Training.csv
- NEW_DATA_FILE to point to Predicting.xlsx

Example:
INPUT_FILE = r"path/to/Training.csv"
NEW_DATA_FILE = r"path/to/Predicting.xlsx"
====================================
Requirements
Python packages:
- numpy
- pandas
- tqdm
- xgboost
- scikit-learn
- openpyxl (required for reading/writing .xlsx via pandas)

Installation:
pip install numpy pandas tqdm xgboost scikit-learn openpyxl
====================================
User configuration (file paths)
Edit the following variables in the script:

INPUT_FILE = r"path/to/input_data.csv"
OUTPUT_FILE = r"path/to/output_results.csv"
NEW_DATA_FILE = r"path/to/new_data.xlsx"
PREDICTED_RESULTS_FILE = r"path/to/predicted_results.xlsx"
====================================
Input and output specifications

(1) INPUT_FILE (training data; CSV)
The CSV file must contain:
- all feature columns listed in FEATURES
- the target column: Annual_Los

(2) OUTPUT_FILE (grid search results; CSV)
The output CSV stores one row per hyperparameter combination, including:
- average validation metrics (10 rounds)
- training metrics (fit on the training split)
- test metrics (evaluated on the 30% hold-out set)

(3) NEW_DATA_FILE (new samples for prediction; Excel)
The file must contain:
- the same feature columns as FEATURES
- an identifier column: ID (used to label prediction outputs)

(4) PREDICTED_RESULTS_FILE (prediction outputs; Excel)
The output Excel file will contain:
- ID
- Predicted_Annual_Los

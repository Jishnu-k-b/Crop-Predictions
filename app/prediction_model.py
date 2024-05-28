from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
import xgboost as xg
import pickle
import pandas as pd
import os

# fertilizer model start
classifier_path = os.path.join(os.path.dirname(__file__), "models", "classifier.pkl")
fertilizer_path = os.path.join(os.path.dirname(__file__), "models", "fertilizer.pkl")
crop_data_path = os.path.join(
    os.path.dirname(__file__), "models", "crop_production.csv"
)

try:
    model = pickle.load(open(classifier_path, "rb"))
    ferti = pickle.load(open(fertilizer_path, "rb"))
except FileNotFoundError as e:
    print(f"Error: {e}")


# crop prediction model start
crop_data = pd.read_csv(crop_data_path)


crop_data = crop_data.dropna()


crop_data = pd.get_dummies(crop_data, columns=["Crop", "Season", "State"])


X = crop_data.drop("Yield", axis=1)
y = crop_data["Yield"]


rf_model = RandomForestRegressor(max_features=6, random_state=0)
rf_model.fit(X, y)


params = {
    "n_estimators": 500,
    "max_depth": 3,
    "learning_rate": 0.01,
    "loss": "squared_error",
}
gb_model = GradientBoostingRegressor(**params)
gb_model.fit(X, y)


xgb_model = xg.XGBRegressor(objective="reg:linear", n_estimators=10, seed=123)
xgb_model.fit(X, y)
# end

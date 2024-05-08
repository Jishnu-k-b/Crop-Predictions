from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
import xgboost as xg
import pickle
import pandas as pd

# fertilizer model start
model = pickle.load(open("classifier.pkl", "rb"))
ferti = pickle.load(open("fertilizer.pkl", "rb"))


# crop prediction model start
crop_data = pd.read_csv("crop_production.csv")


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

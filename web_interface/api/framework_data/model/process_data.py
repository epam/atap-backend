import os
import pickle

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, RobustScaler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def transformed_for_model(dataframe: pd.DataFrame, train=True):
    # * page_load_time doesn't affect prediction
    dataframe.drop("page_load_time", axis=1, inplace=True)

    numerical_features = dataframe.columns[dataframe.dtypes.apply(lambda x: x.kind in ["u", "i", "f"])]
    if "run_times" in numerical_features:
        numerical_features = numerical_features.drop("run_times")

    # * otherwise predict for single test record
    if train:
        numerical_features = numerical_features.drop("boxcox_lmbda")

        # * scale features with outliers
        rs = RobustScaler(quantile_range=(25, 95))
        dataframe[numerical_features] = pd.DataFrame(rs.fit_transform(dataframe[numerical_features]))

        # * rewrite intermediate runs stats
        dataframe[["name", "often_tested", "multirun", "boxcox_lmbda"]].to_csv("data/runs_frequency_data.csv")
        dataframe.drop("boxcox_lmbda", axis=1, inplace=True)

        # * cast test names to category
        dataframe.name = dataframe.name.astype("category")
        # * encode categorical
        le = LabelEncoder()
        dataframe.name = le.fit_transform(dataframe.name)

        # * save data transformers
        with open(BASE_DIR + "/data/robust_scaler.pkl", "wb") as rsf:
            pickle.dump(rs, rsf)
        with open(BASE_DIR + "/data/label_encoder.pkl", "wb") as lef:
            pickle.dump(le, lef)
    else:
        dataframe = _process_for_model_prediction(dataframe, numerical_features)

    # * cast types
    dataframe.name = pd.to_numeric(dataframe.name, downcast="unsigned")

    for col in numerical_features:
        dataframe[col] = pd.to_numeric(dataframe[col], downcast="float").round(3)

    numerical_features = dataframe.columns[dataframe.dtypes.apply(lambda x: x.kind in ["u", "i", "f"])]

    return dataframe[numerical_features], numerical_features


def _process_for_model_prediction(one_row_frame, numerical_features):
    test_name = one_row_frame.name.iloc[0]

    dataframe_from_train = pd.read_csv(BASE_DIR + "/data/runs_frequency_data.csv", usecols=[1, 2, 3])
    with open(BASE_DIR + "/data/label_encoder.pkl", "rb") as lef:
        le = pickle.load(lef)
    with open(BASE_DIR + "/data/robust_scaler.pkl", "rb") as rsf:
        rs = pickle.load(rsf)

    # * unknown test for train base
    if dataframe_from_train[dataframe_from_train.name == test_name].shape[0] == 0:
        print("WARNING! Unknown test name. Should retrain model on new test data.")
        test_name = dataframe_from_train.name.any()
    dataframe_from_train = dataframe_from_train[dataframe_from_train.name == test_name]

    one_row_frame["often_tested"] = dataframe_from_train.often_tested.iloc[0]
    one_row_frame["multirun"] = dataframe_from_train.multirun.iloc[0]
    numerical_features = np.concatenate([numerical_features, np.array(["often_tested", "multirun"])])

    one_row_frame[numerical_features] = rs.transform(one_row_frame[numerical_features])
    one_row_frame.name = one_row_frame.name.astype("category")
    one_row_frame.name = le.transform(one_row_frame.name)

    return one_row_frame

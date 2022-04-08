import os

import dill
import numpy as np
from pandas import DataFrame, to_numeric

from web_interface.api.framework_data.estimate_model_helpers.process_data import transformed_for_model

numerical_features = [
    "page_load_time",
    "all_elements_count",
    "a",
    "img",
    "button",
    "input",
    "form",
    "table",
    "div",
    "span",
]
database_columns = ["name", "date_was_run_y_m_d", *numerical_features]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def ensure_data_types(frame):
    if any(dtype.kind not in ["u", "i", "f"] for dtype in frame[numerical_features].dtypes):
        for feat in numerical_features:
            frame[feat] = to_numeric(frame[feat], downcast="float").round(3)

    return frame


def get_prediction(X: list) -> np.ndarray:
    # print("*" * 60)
    # print("GET_PREDICTION")
    # print("*" * 60)
    models = restore_model()

    # print("X", X)

    df = ensure_data_types(
        DataFrame(
            np.array(X)[np.newaxis],
            columns=database_columns,
        )
    )
    # print("DF", df)
    LMBDA = -0.318052439670531
    df, _ = transformed_for_model(df, train=False)
    # print("DF transformed", df)
    prediction = models.predict(df, LMBDA)
    # print("PREDICTION", prediction)
    return prediction


def restore_model():
    with open(BASE_DIR + "/model.sav", "rb") as file:
        return dill.load(file)

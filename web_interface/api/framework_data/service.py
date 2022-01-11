import os

import dill
import numpy as np
from pandas import DataFrame, to_numeric

from .model.process_data import transformed_for_model

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
    if not all(dtype.kind in ["u", "i", "f"] for dtype in frame[numerical_features].dtypes):
        for feat in numerical_features:
            frame[feat] = to_numeric(frame[feat], downcast="float").round(3)

    return frame


def get_prediction(X: list) -> np.ndarray:
    models = restore_model()

    df = ensure_data_types(
        DataFrame(
            np.array(X)[np.newaxis],
            columns=database_columns,
        )
    )
    LMBDA = -0.314
    df, _ = transformed_for_model(df, train=False)
    prediction = models.predict(df, LMBDA)
    return prediction


def restore_model():
    with open(BASE_DIR + "/model.sav", "rb") as file:
        return dill.load(file)

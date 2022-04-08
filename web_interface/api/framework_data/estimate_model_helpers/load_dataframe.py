from json import loads
from io import BytesIO

import pandas as pd
from numpy import unique
import sklearn.model_selection as model_selection


def frame_from_json_row(json_record):
    return pd.DataFrame.from_dict(loads(json_record), orient="index").T


def get_clear_tests_dataframe(http_response_bytes):
    df = pd.read_csv(BytesIO(http_response_bytes)).drop("id", axis=1)
    db_records_amount = df.shape[0]

    try:
        df_from_page_size_data_json = pd.concat(
            [frame_from_json_row(page_data) for page_data in df.page_size_data]
        )
    except ValueError as err:
        print("Dataframe is empty:", err)
        return pd.DataFrame()

    df = df.join(df_from_page_size_data_json.reset_index(drop=True)).drop("page_size_data", axis=1)

    # * format datetime
    df.timestamp = pd.to_datetime(df.timestamp, utc=True).dt.strftime("%y-%m-%d")
    df.rename(columns={"timestamp": "date_was_run_y_m_d"}, inplace=True)

    # * Drop timestamp duplicates - run each time
    # keep last run results for similar elements amount, page_load_time, e.t.c
    # to prevent fitting on fixed tests
    runs_unique = df.drop(["date_was_run_y_m_d", "run_times"], axis=1).drop_duplicates(keep="last")

    df = df.merge(runs_unique.name, left_index=True, right_index=True, how="inner", suffixes=("", "_dup"))
    df.drop("name_dup", axis=1, inplace=True)

    # * Drop not run tests with zero run_times - run each time
    _ = df.shape[0]
    not_run = df.query("run_times <= 0")
    df = df.query("run_times > 0")
    assert df.shape[0] == _ - not_run.shape[0]

    # * Drop suspected of being aborted - run one time on demand
    run_times_thresh, elements_count_thresh = 5, 200

    # mistakes - look at high all_elements_count, impossible or too rare
    abort_suspects = df.query("run_times < @run_times_thresh and all_elements_count > @elements_count_thresh")

    _ = df.shape[0]
    df = df.query("all_elements_count <= @elements_count_thresh or run_times >= @run_times_thresh")
    assert df.shape[0] == _ - abort_suspects.shape[0]
    # * Drop stuck tests - run one time on demand
    run_times_limit, run_times_thresh, elements_count_thresh = 2e4, 8e3, 1000

    # mistakes - tests are highly probable to be stuck
    stuck_suspects = df.query(
        "run_times > @run_times_thresh and all_elements_count < @elements_count_thresh or run_times > @run_times_limit"
    )

    _ = df.shape[0]
    df = df.query(
        "run_times <= @run_times_limit and all_elements_count >= @elements_count_thresh or run_times <= @run_times_thresh"
    )
    assert df.shape[0] == _ - stuck_suspects.shape[0]

    # * Drop tests with extremely low frequencies - run one time on demand
    test_counts = df.name.value_counts()
    rarely_tested_thresh = test_counts.quantile(0.18)

    were_rarely_tested = df.name[df.name.apply(lambda name: test_counts[name] < rarely_tested_thresh)]

    old_test_amount = df.shape[0]
    df = df[df.name.apply(lambda name: name not in were_rarely_tested.values)]
    assert df.shape[0] == old_test_amount - were_rarely_tested.shape[0]

    print(f"Lost {(db_records_amount - df.shape[0]) / db_records_amount * 100: .2f}% of noisy data")
    print(f"Got {unique(df.name).shape[0]} tests data to estimate")

    return df

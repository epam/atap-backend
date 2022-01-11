import sys
import json
from framework.test_system import discover_tests, load_tests_with_dependencies
from framework.test import MIN_FRAMEWORK_VERSION
from framework.main import run_tests
from framework.tools import map_elements_with_pages


def time_test(tests, rewrite=False):
    if len(tests) == 0:
        return

    print("Loading time test data")
    map_elements_with_pages.map_pages()
    with open("framework/time_of_tests/average_pages.json", "r", encoding="utf-8") as file:
        common_pages = json.load(file)
    project_info = {
        "page_infos": list()
    }
    tests_to_run = dict()
    unique_name_counter = 0

    for test in tests:
        print(f">>> LOADING {test}")
        current_loaded_test = discover_tests([test], None)
        if len(current_loaded_test) == 0:
            print(f">>> ERROR: TEST {test} NOT FOUND")
            continue
        else:
            current_loaded_test = current_loaded_test[0]

        if current_loaded_test.framework_version < MIN_FRAMEWORK_VERSION:
            print(f">>> WARNING: TEST {test} OUTDATED, {current_loaded_test.framework_version} < {MIN_FRAMEWORK_VERSION}")
            continue
        try:
            assert isinstance(current_loaded_test.elements_type, str)
        except (AssertionError, AttributeError):
            print(f">>> WARNING: NO ELEMENTS DATA FOR {test}")
            current_loaded_test.elements_type = ""

        print(common_pages[current_loaded_test.elements_type])
        test_page = {
            "page_info": {
                "url": common_pages[current_loaded_test.elements_type],
                "name": f"{common_pages[current_loaded_test.elements_type]}_{unique_name_counter}"
            }
        }
        unique_name_counter += 1
        project_info["page_infos"].append(test_page["page_info"])
        tests_to_run[test_page["page_info"]["name"]] = load_tests_with_dependencies([test], None)

    tests = run_tests(project_info, tests_to_run, run_axe_tests=[], testing=True, do_test_merge=False)
    time_of_tests = dict()
    pattern = r"_\d"
    for page_name, test in tests.items():
        for runned_test in test:
            page_name = re.split(pattern, page_name)[0]
            if runned_test.execution_time:
                time_ = round(runned_test.execution_time, 1)
            else:
                time_ = False

            try:
                time_of_tests[runned_test.name][page_name].append(time_)
            except KeyError:
                time_of_tests[runned_test.name] = {page_name: [time_]}
            print(f"Test {runned_test.name} took {time_}")

    update_average_time(time_of_tests, rewrite=rewrite)
    sys.exit(0)


def update_average_time(calculated_time: dict, rewrite=False):
    path = "framework/time_of_tests/average_time.json"
    try:
        with open(path, "r", encoding="utf-8") as file:
            stored_time = json.load(file)
    except FileNotFoundError:
        stored_time = {}

    for test_name, pages_data in calculated_time.items():
        for url, time_list in pages_data.items():
            try:
                test_time = stored_time[test_name]
            except KeyError:
                test_time = None

            if test_time and not rewrite:
                stored_time[test_name] = round((test_time + sum(time_list)) / (len(time_list) + 1), 1)
            elif test_time is None or rewrite:
                stored_time[test_name] = round(sum(time_list) / len(time_list), 1)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(stored_time, file, ensure_ascii=False, indent=4)


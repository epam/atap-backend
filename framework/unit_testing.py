import logging
import os
import sys
import hashlib
import glob
import json
from framework.test_system import discover_tests, load_tests_with_dependencies
from framework.main import run_tests
from framework.test import MIN_FRAMEWORK_VERSION

logger = logging.getLogger("framework.unit_testing")

TEST_DATA_FILE = "persist_testing_results/past_test_data.json"


def unit_test(tests):
    failed_tests = []
    if len(tests) == 0:
        return

    orig_test_list = tests

    logger.error("Loading unit test data")
    project_info = {
        "page_infos": list(), 
        "enable_content_blocking": True,
        "enable_popup_detection": False
    }
    tests_to_run = dict()
    checks_to_perform = list()

    unique_name_counter = 0

    try:
        with open(TEST_DATA_FILE, mode='r') as test_data_file:
            past_test_data = json.load(test_data_file)
    except FileNotFoundError:
        past_test_data = {}
    new_test_data = {}

    for test in tests:
        logger.info(f">>> CHECKING {test}")
        filename = glob.glob(f"./framework/tests/*/{test}.py")
        if len(filename) == 0:
            logger.error(f">>> TEST {test} NOT FOUND")
            failed_tests.append((test, "Test not found"))
            continue

        if len(filename) >= 2:
            logger.error(f">>> MULTIPLE TESTS FOUND FOR {test}, NOT TESTING")
            failed_tests.append((test, "Multiple tests with the same name"))
            continue

        filename = filename[0]
        # if len(tests) > 1:
        new_hash = get_checksum(filename)
        if test not in past_test_data:
            print(f"_____ => {new_hash}")
            new_test_data[test] = new_hash
        else:
            if new_hash in past_test_data[test]:
                print(f"{new_hash} - no changes")
                logger.info(f">>> TEST {test} NOT CHANGED, NOT TESTING")
                new_test_data[test] = new_hash
                continue
            else:
                print(f"{len(past_test_data[test])} HASHES TESTED BEFORE => {new_hash}")
                new_test_data[test] = new_hash

        logger.info(f">>> LOADING {test}")
        current_loaded_test = discover_tests([test], None)
        if len(current_loaded_test) == 0:
            logger.error(f">>> TEST {test} NOT FOUND")
            failed_tests.append((test, "Test not found"))
            continue
        else:
            current_loaded_test = current_loaded_test[0]

        if current_loaded_test.framework_version < MIN_FRAMEWORK_VERSION:
            logger.warning(f">>> TEST {test} OUTDATED, {current_loaded_test.framework_version} < {MIN_FRAMEWORK_VERSION}")
            failed_tests.append((test, f"Test outdated, {current_loaded_test.framework_version} < {MIN_FRAMEWORK_VERSION}"))
            continue
        if current_loaded_test.test_data is None:
            logger.error(f">>> NO UNIT TEST DATA FOR {test}")
            failed_tests.append((test, "No unit test data"))
            continue
        test_pages = current_loaded_test.test_data

        for test_page in test_pages:
            html_filename = test_page['page_info']['url']
            logger.info(f">>>>> LOADING {test} dependencies to run on {html_filename}")
            test_page['page_info']['url'] = os.path.join(os.getcwd(), "framework/pages_for_test", html_filename)
            if test_page['page_info']['url'].startswith("/"):
                # Unix-like
                test_page['page_info']['url'] = "file://" + test_page['page_info']['url']
            else:
                # Windows
                test_page['page_info']['url'] = "file:///" + test_page['page_info']['url']
            test_page['page_info']["name"] = f"{html_filename}_{unique_name_counter}"
            unique_name_counter += 1
            test_page['page_info'].update({"page_after_login":False})
            project_info["page_infos"].append(test_page['page_info'])
            logger.info(f"!!! Adding {test_page['page_info']['name']} for {current_loaded_test.name}")
            tests_to_run[test_page['page_info']["name"]] = load_tests_with_dependencies([test], None)

            for loaded_test in tests_to_run[test_page['page_info']["name"]]:
                if loaded_test.name == test:
                    test_to_check = loaded_test
                    break
            else:
                logger.critical(f">>>>> {test} did not load the second time for some reason")
                sys.exit(-1)

            checks_to_perform.append({
                "page_name": test_page['page_info']["name"],
                "test": test_to_check,
                "test_page_info": test_page
            })

    for page in project_info["page_infos"]:
        logger.debug(f"{page['name']} ({page['url']})")
    for page, tests in tests_to_run.items():
        logger.debug(f"On page {page} run {[test.name for test in tests]}")

    run_tests(project_info, tests_to_run, run_axe_tests=[], testing=True, do_test_merge=False)

    for check in checks_to_perform:
        current_loaded_test = check["test"]
        test_page = check["test_page_info"]
        page_name = check["page_name"]

        if current_loaded_test.status == "ERROR":
            logger.error(f">>>>> {current_loaded_test.name} CRASHED ON {page_name}")
            failed_tests.append((current_loaded_test.name, f"CRASH ON {page_name}:{current_loaded_test.message}"))
            continue
        if current_loaded_test.status != test_page["expected_status"]:
            logger.error(
                f">>>>> FAIL: {current_loaded_test.name} - expected {test_page['expected_status']} on {page_name}, got {current_loaded_test.status}")
            failed_tests.append((current_loaded_test.name,
                                 f"FAIL: Expected {test_page['expected_status']} on {page_name}, got {current_loaded_test.status}:{current_loaded_test.message}"))
            continue
        if "expected_problem_count" in test_page and len(current_loaded_test.problematic_elements) != test_page[
            "expected_problem_count"]:
            logger.error(
                f">>>>> FAIL: {current_loaded_test.name} - expected {test_page['expected_status']} on {page_name}, got {current_loaded_test.status}")
            failed_tests.append((current_loaded_test.name,
                                 f"FAIL: Expected {test_page['expected_problem_count']} problems on {page_name}, got {len(current_loaded_test.problematic_elements)}"))
            continue
        if "expected_additional_content_length" in test_page:
            for key, expected_length in test_page["expected_additional_content_length"].items():
                if key not in current_loaded_test.result:
                    logger.error(f">>>>> FAIL: {current_loaded_test.name} - {key} not present in test result on {page_name}")
                    failed_tests.append((current_loaded_test.name, f"FAIL: {key} not present in test result on {page_name}"))
                    continue
                if len(current_loaded_test.result[key]) != expected_length:
                    logger.error(
                        f">>>>> FAIL: {current_loaded_test.name} - expected {expected_length} items in {key} on {page_name}, got {len(current_loaded_test.result[key])}")
                    failed_tests.append((current_loaded_test.name,
                                         f"FAIL: Expected {expected_length} items in {key} on {page_name}, got {len(current_loaded_test.result[key])}"))
                    continue

        logger.info(f">>>>> OK {current_loaded_test.name} - {test_page['expected_status']} on {page_name} as expected")

    for failed_test in failed_tests:
        logger.info(f"{failed_test[0]} - {failed_test[1]}")

    # if len(tests) > 1:
    for test in orig_test_list:
        if test not in [failed_test[0] for failed_test in failed_tests]:
            if test not in past_test_data:
                past_test_data[test] = []
            if new_test_data[test] not in past_test_data[test]:
                past_test_data[test].append(new_test_data[test])

    with open(TEST_DATA_FILE, mode='w') as test_data_file:
        json.dump(past_test_data, test_data_file)

    if len(failed_tests) != 0:
        sys.exit(1)
    else:
        logger.info("UNIT TEST OK")
        sys.exit(0)


def get_checksum(file_path):
    h = hashlib.sha256()
    try:
        with open(file_path, 'rb') as file:
            while True:
                chunk = file.read(h.block_size)
                if not chunk:
                    break
                h.update(chunk)
    except FileNotFoundError:
        return None
    return h.hexdigest()

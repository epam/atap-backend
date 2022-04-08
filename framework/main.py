import os
import sys
import time
import json
import logging
import tempfile
import uuid

from framework import request_limiter
from framework import activity
from framework.parallelization import run_tests_in_parallel
from framework import test_system
from framework import webdriver_manager

logger = logging.getLogger("framework.main")


def discover_and_run(
        project_info,
        filter_test=None,
        filter_category=None,
        run_axe_tests=None,
        progress_report_callback=None,
        testing: bool = False,
        cancelled_tests=None,
):
    if cancelled_tests is None:
        cancelled_tests = []
    if progress_report_callback is not None:
        progress_report_callback({
            "overall_progress": "Loading tests"
        })
    tests = dict()

    if len(project_info["page_infos"]) == 0:
        raise ValueError("No pages to test!")

    for page_info in project_info["page_infos"]:
        page_info["name"] += f"_{uuid.uuid4()}"
        # if project_info["enable_popup_detection"]:
        #     logger.info(">Duplicating activities to test the page both with popups and without")
        #
        #     new_activities = list()
        #     if "activities" in page_info:
        #         for old_activity in page_info["activities"]:
        #             new_activities.append({
        #                 "name": old_activity["name"] + "_no_popup",
        #                 "url": old_activity["url"],
        #                 "element_click_order": old_activity["element_click_order"],
        #                 "side_file": old_activity["side_file"]
        #             })
        #             new_activities.append({
        #                 "name": old_activity["name"] + "_with_popup",
        #                 "url": old_activity["url"],
        #                 "element_click_order": old_activity["element_click_order"],
        #                 "side_file": old_activity["side_file"]
        #             })
        #     else:
        #         new_activities.append({
        #             "name": "Main Activity_no_popup",
        #             "url": page_info["url"],
        #             "element_click_order": [],
        #             "side_file": None
        #         })
        #         new_activities.append({
        #             "name": "Main Activity_with_popup",
        #             "url": page_info["url"],
        #             "element_click_order": [],
        #             "side_file": None
        #         })
        #
        #     page_info["activities"] = new_activities

        if "activities" in page_info and len(page_info["activities"]) > 0:
            for activity_dict in page_info["activities"]:
                if project_info["enable_popup_detection"]:
                    tests[page_info["name"] + "_" + activity_dict["name"]+"_no_popup"] = test_system.load_tests_with_dependencies(
                        filter_test, filter_category)
                    tests[page_info["name"] + "_" + activity_dict[
                        "name"] + "_with_popup"] = test_system.load_tests_with_dependencies(
                        filter_test, filter_category)
                else:
                    tests[page_info["name"]+"_"+activity_dict["name"]] = test_system.load_tests_with_dependencies(filter_test, filter_category)
        else:
            if "enable_popup_detection" in project_info and project_info["enable_popup_detection"]:
                tests[page_info["name"] + "_" + "Main Activity_no_popup"] = test_system.load_tests_with_dependencies(filter_test,
                                                                                                            filter_category)
                tests[page_info["name"] + "_" + "Main Activity_with_popup"] = test_system.load_tests_with_dependencies(filter_test,
                                                                                                            filter_category)
            else:
                tests[page_info["name"]+"_"+"Main Activity"] = test_system.load_tests_with_dependencies(filter_test, filter_category)

    return run_tests(
        tests=tests,
        run_axe_tests=run_axe_tests,
        project_info=project_info,
        progress_report_callback=progress_report_callback,
        testing=testing,
        cancelled_tests=cancelled_tests,
    )


def run_tests(
        project_info,
        tests: dict,
        run_axe_tests=None,
        progress_report_callback=None,
        testing: bool = False,
        do_test_merge=True,
        cancelled_tests=None,
):
    if cancelled_tests is None:
        cancelled_tests = []
    if len(tests.values()) == 0:
        logger.info("No tests selected, nothing to test")
        return tests

    if progress_report_callback is not None:
        progress_report_callback({
            "overall_progress": "Preparing for testing"
        })
    time_start = time.time()

    logger.info("Restarting cache")
    with open("/squid_control/restart", mode="w") as f:
        f.write("RESTART")

    time_wait_started = time.time()

    if progress_report_callback is not None:
        progress_report_callback({
            "overall_progress": f"Waiting for cache to restart"
        })

    while os.path.exists("/squid_control/restart"):
        time.sleep(1)
        if time.time() - time_wait_started > 20:
            if progress_report_callback is not None:
                progress_report_callback({
                    "overall_progress": f"No reply from cache for {int(time.time() - time_wait_started)}s, still waiting for restart..."
                })
    else:
        logger.info("Cache restart OK")

    logger.info("Killing old firefox processes")
    os.system("pkill -9 firefox")
    os.system("pkill -9 geckodriver")

    logger.info("Creating WebdriverManager")
    manager = webdriver_manager.WebdriverManager(
        limiter=request_limiter.RequestLimiter(project_info["request_interval"] if "request_interval" in project_info else 0),
        enable_caching="enable_caching" not in project_info or project_info["enable_caching"],
        enable_tracker_blocking=project_info["enable_content_blocking"]
    )

    if not testing:
        logger.info(">Preparing to load activities")

        webdriver_instance = manager.request()

        activities = list()
        for page_info in project_info['page_infos']:
            page_resolution = page_info["page_resolution"]
            if page_info["url"] != "":
                if progress_report_callback is not None:
                    progress_report_callback({
                        "overall_progress": f"Loading activities for {page_info['name']}"
                    })
                if page_resolution:
                    w, h = page_resolution.split("x")
                    webdriver_instance.set_window_size(width=w, height=h)
                webdriver_instance.get(page_info["url"])
            options = page_info["options"] if "options" in page_info else ''

            logger.info(">Loading config")
            if "activities" in page_info:
                page_activities = activity.load_activities(page_info, webdriver_instance)
            else:
                page_activities = [activity.Activity(
                    name="Main Activity",
                    url=page_info["url"],
                    options=options,
                    page_after_login=page_info["page_after_login"],
                    commands=[],
                    page_resolution=page_resolution,
                )]

            if "enable_popup_detection" in project_info and project_info["enable_popup_detection"]:
                new_page_activities = list()
                for page_activity in page_activities:
                    commands_without_popup = list(page_activity.commands)
                    commands_without_popup.append({
                        "target": None,
                        "targets": None,
                        "value": None,
                        "command": "close_popup"
                    })
                    activity_without_popup = activity.Activity(
                        name=page_activity.name+"_no_popup",
                        url=page_activity.url,
                        options=page_activity.options,
                        page_after_login=page_activity.page_after_login,
                        commands=commands_without_popup,
                        page_resolution=page_resolution,
                    )
                    new_page_activities.append(activity_without_popup)

                    commands_with_popup = list(page_activity.commands)
                    commands_with_popup.append({
                        "target": None,
                        "targets": None,
                        "value": None,
                        "command": "wait_for_popup"
                    })
                    activity_with_popup = activity.Activity(
                        name=page_activity.name+"_with_popup",
                        url=page_activity.url,
                        options=page_activity.options,
                        page_after_login=page_activity.page_after_login,
                        commands=commands_with_popup,
                        page_resolution=page_resolution,
                    )
                    new_page_activities.append(activity_with_popup)

                page_activities = new_page_activities

            for act in page_activities:
                act.name = page_info["name"] + "_" + act.name

            activities.extend(page_activities)

        no_parallel_login = 'no_parallel_login' in project_info and project_info['no_parallel_login']
        num_threads = 1 if no_parallel_login else int(os.environ.get("THREAD_COUNT", 4))

        try:
            with open("config.json", "rb") as config_file:
                config = json.load(config_file)
            if "urls" in config:
                for page_info in project_info["page_infos"]:
                    if page_info["url"] in config["urls"]:
                        config["urls"][sys.argv[1]]["url"] = sys.argv[1]
                        activities.extend(activity.load_activities(
                            config["urls"][page_info["url"]],
                            webdriver_instance,
                        ))
            if "num_threads" in config:
                num_threads = config["num_threads"]
        except FileNotFoundError:
            logger.warning("=>Config file not Found")
        manager.release(webdriver_instance)

    else:
        activities = list()
        num_threads = int(os.environ.get("THREAD_COUNT", 4))
        for page_info in project_info["page_infos"]:
            options = page_info["options"] if "options" in page_info else ''
            activities.append(activity.Activity(
                name=page_info["name"],
                url=page_info["url"],
                options=options,
                page_after_login=page_info["page_after_login"],
                commands=[],
            ))

    if len(tests.values()) == 0:
        logger.info("No tests selected, nothing to test")
        return tests

    required_elements = set()
    for test in list(tests.values())[0]:
        required_elements.update(test.locator_required_elements)

    if not os.path.exists("screenshots"):
        os.makedirs("screenshots")

    if num_threads == 0:
        logger.critical("=>Running tests single threaded is no longer supported, please, set num_threads to 1 or above")
        return

    logger.info(f"=>Running tests, {num_threads} threads")
    if progress_report_callback is not None:
        progress_report_callback({
            "overall_progress": f"Starting worker threads",
            "thread_count": num_threads,
        })
    run_tests_in_parallel(
        tests,
        activities,
        num_threads,
        required_elements,
        manager,
        progress_report_callback,
        run_axe_tests=run_axe_tests,
        testing=testing,
        do_test_merge=do_test_merge,
        cancelled_tests=cancelled_tests
    )
    if do_test_merge:
        tests_values_fixed_order = list(tests.values())

        for test in tests_values_fixed_order[0]:
            for activity_tests in tests_values_fixed_order[1:]:
                for secondary_test in activity_tests:
                    if test.name == secondary_test.name:
                        test.merge_other_test(secondary_test)

        tests = tests_values_fixed_order[0]

    if testing:
        logger.info(f"Took {time.time() - time_start}")
        return tests

    logger.info("Taking page screenshots...")
    if progress_report_callback is not None:
        progress_report_callback({
            "overall_progress": f"Taking page screenshots",
            "thread_count": 0
        })

    webdriver_instance = manager.request()
    for activity_id, cur_activity in enumerate(activities):
        if progress_report_callback is not None:
            progress_report_callback({
                "overall_progress": f"Taking page screenshot {activity_id+1}/{len(project_info['page_infos'])}",
                "thread_count": 0
            })
        webdriver_instance.maximize_window()
        if cur_activity.page_resolution:
            webdriver_instance.set_window_size(*cur_activity.page_resolution)
        cur_activity.get(webdriver_instance)
        time.sleep(5)

        filename = f"{tempfile.gettempdir()}/page_screenshot.jpg"
        webdriver_instance.save_screenshot(filename)
        if progress_report_callback is not None:
            with open(filename, "rb") as img_file:
                progress_report_callback({
                    "page_screenshot": {
                        "url": cur_activity.url,
                        "image": img_file.read(),
                    }
                })
    manager.release(webdriver_instance)

    logger.info("Finalizing dev report")
    if progress_report_callback is not None:
        progress_report_callback({
            "overall_progress": f"Generating dev report",
            "thread_count": 0
        })

    tests_passed = 0
    tests_notrun = 0
    tests_errored = 0
    tests_failed = 0

    for test in tests:
        if test.status == "PASS":
            tests_passed += 1
        elif test.status == "FAIL":
            tests_failed += 1
        elif test.status == "NOTRUN":
            tests_notrun += 1
        elif test.status == "ERROR":
            tests_errored += 1

    logger.info(">>>   REPORT   <<<")
    logger.info(f">Out of {len(tests)} selected tests:")
    if tests_passed == len(tests):
        logger.info(">ALL have PASSED")
    else:
        logger.info(f">   {tests_passed} tests passed")
        if tests_failed > 0:
            logger.info(f">   {tests_failed} tests failed")
        if tests_notrun > 0:
            logger.info(f">   {tests_notrun} tests were skipped")
        if tests_errored > 0:
            logger.info(f">   {tests_errored} tests crashed")
    if tests_passed < len(tests):
        logger.info(">Unsuccessful tests:")
        for test in tests:
            if test.status not in ["PASS", "NOELEMENTS"]:
                if test.message is not None:
                    logger.info(f">   {test.status}:{test.human_name}:{test.message}")
                else:
                    logger.info(f">   {test.status}:{test.human_name}")
                if len(test.problematic_elements) > 0:
                    for problematic_element in test.problematic_elements:
                        if "element" in problematic_element:
                            logger.info(f">   > problem: '{problematic_element['problem']}', source:'{problematic_element['element'].source[:100] if len(problematic_element['element'].source) > 100 else problematic_element['element'].source}'")
                        else:
                            logger.info(f">   > problem: '{problematic_element['problem']}', source:'{problematic_element['source'][:100] if len(problematic_element['source']) > 100 else problematic_element['source']}'")

    logger.info(f"Took {time.time() - time_start}")
    return tests


def main():
    if len(sys.argv) <= 1:
        logger.error(">Error: no url specified. Usage: main.py <url> name-project [test selection]")
        sys.exit(-1)

    project_info = {
        "page_infos": [{"url": sys.argv[1], "name": "Main Page", "page_after_login": False}],
        "name": "Test project",
        "comment": "Test comment",
        "date_created": "Test date created",
        "version": "v1.33.7",
        "contact": "nobody@example.com",
        "company": "TestCompany Inc",
        "audit_reports": [{"Report name":"AUDIT-1", "Legal Disclaimer":"rtrt", "Notes":"rt", "VPAT Heading Information":"test", "Type":"Internal", "WCAG":"2.0", "Notes From Project Manager ":"test"}],
        "vpat_reports": [{"Report name":"VPAT-1","Notes":"1","Legal Disclaimer":"1","VPAT Heading Information":"1","Evaluation Methods Used":"Private EPAM Methodology","Conformance Level":"A","Notes From Project Manager":"1"}],
        "task_id": 1,
        "enable_content_blocking": True
    }

    if len(sys.argv) > 2:
        if sys.argv[2] != "--full":
            if sys.argv[2] != "axe":
                discover_and_run(
                    project_info=project_info,
                    filter_category=None if sys.argv[2].startswith("test_") else sys.argv[2],
                    filter_test=sys.argv[2] if sys.argv[2].startswith("test_") else None,
                    run_axe_tests=[]
                )
            else:
                discover_and_run(
                    project_info=project_info,
                    filter_category="nothingshouldmatchthis",
                    filter_test="nothingshouldmatchthis",
                )

        elif len(sys.argv) > 3:
            if sys.argv[3] != "axe":
                discover_and_run(
                    project_info=project_info,
                    filter_category=None if sys.argv[3].startswith("test_") else sys.argv[3],
                    filter_test=sys.argv[3] if sys.argv[3].startswith("test_") else None,
                    run_axe_tests=[]
                )
            else:
                discover_and_run(
                    project_info=project_info,
                    filter_category="nothingshouldmatchthis",
                    filter_test="nothingshouldmatchthis",
                )
        else:
            discover_and_run(project_info=project_info)
    else:
        discover_and_run(project_info=project_info)


if __name__ == "__main__":
    main()

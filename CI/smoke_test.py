from framework import main
import sys

SMOKE_TEST_PAGES = ["https://google.com", "https://epam.com"]


def main_func():
    fails = list()
    print("LOADING AVAILABLE TESTS")
    test_list = [test["name"] for test in main.get_available_tests()]
    for test_page_url in SMOKE_TEST_PAGES:
        print(f"RUNNING SMOKE TEST ON {test_page_url}")
        project_info = {
            "page_infos": [{"url": test_page_url, "name": "Main Page"}],
            "name": "Test project",
            "comment": "Test comment",
            "date_created": "Test date created",
            "version": "v1.33.7",
            "contact": "nobody@example.com",
            "company": "TestCompany Inc",
            "audit_reports": [{"Report name": "AUDIT-1", "Legal Disclaimer": "rtrt", "Notes": "rt",
                               "VPAT Heading Information": "test", "Type": "Internal", "WCAG": "2.0",
                               "Notes From Project Manager ": "test"}],
            "vpat_reports": [
                {"Report name": "VPAT-1", "Notes": "1", "Legal Disclaimer": "1", "VPAT Heading Information": "1",
                 "Evaluation Methods Used": "Private EPAM Methodology", "Conformance Level": "A",
                 "Notes From Project Manager": "1"}],
            "task_id": 1
        }
        tests = main.discover_and_run(
            project_info,
            filter_test=test_list,
            filter_category=None,
            run_axe_tests=[],
            testing=False
        )
        for test in tests:
            if test.status in ["ERROR", "READY"]:
                message = f"{test_page_url} - {test.name} CRASHED (status:{test.status})"
                fails.append(message)
            else:
                message = f"{test_page_url} - {test.name} OK (status:{test.status})"
            print(message)

    if len(fails) == 0:
        print("SMOKE TEST OK")
        sys.exit(0)
    else:
        print("SMOKE TEST COMPLETE, SMOKE IS LEAKING:")
        for message in fails:
            print(message)
        sys.exit(-1)
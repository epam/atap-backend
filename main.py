import sys
import logging
import multiprocessing

from framework import main, unit_testing, test_system, time_testing
from CI import run_changed_tests, smoke_test


root_logger = logging.getLogger("framework")
root_logger.setLevel(logging.DEBUG)
root_logger.propagate = False

console_out = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] (%(threadName)s) %(name)s/%(levelname)s:%(message)s')
console_out.setFormatter(formatter)
root_logger.addHandler(console_out)

if len(sys.argv) >= 2 and sys.argv[1] == "test_multipage":
    main.discover_and_run(
        {
            "page_infos": [
                {
                    "url": "https://pythonworld.ru/web/django-ubuntu1604.html",
                    "name": "Pythonworld"
                },
                {
                    "url": "https://atlassian.com",
                    "name": "Atlassian"
                }
            ]
        },
        ["test_fake_links"],
        report_file_name="repppp.pdf",
        run_axe_tests=[]
    )
elif len(sys.argv) >= 2 and sys.argv[1] == "unittest":
    if len(sys.argv) >= 3:
        def unit_test_target():
            unit_testing.unit_test(sys.argv[2:])
    else:
        def unit_test_target():
            unit_testing.unit_test([test['name'] for test in test_system.get_available_tests()])

    unit_testing_process = multiprocessing.Process(target=unit_test_target)
    unit_testing_process.start()
    unit_testing_process.join()
    sys.exit(unit_testing_process.exitcode)

elif len(sys.argv) >= 2 and sys.argv[1] == "timetest":
    if len(sys.argv) == 2:
        time_testing.time_test([test['name'] for test in test_system.get_available_tests()])
    elif len(sys.argv) == 3 and sys.argv[-1] == "rewrite":
        time_testing.time_test([test['name'] for test in test_system.get_available_tests()], rewrite=True)
    elif len(sys.argv) == 3 and sys.argv[-1].startswith("test_"):
        main.time_test([sys.argv[2]])
    elif len(sys.argv) == 4 and sys.argv[-1] == "rewrite":
        main.time_test([sys.argv[2]], rewrite=True)
    else:
        print(f">>> ERROR: command {r''.join(str(argv) + ' ' for argv in sys.argv[1::])}not found")
elif len(sys.argv) >= 2 and sys.argv[1] == "unittest_changed":
    run_changed_tests.main_func()
elif len(sys.argv) >= 2 and sys.argv[1] == "smoketest":
    smoke_test.main_func()
else:
    main_testing_process = multiprocessing.Process(target=main.main)
    main_testing_process.start()
    main_testing_process.join()
    sys.exit(main_testing_process.exitcode)

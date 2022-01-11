import git
import os
import sys
from framework import main


def main_func():
    try:
        if len(sys.argv) < 3:
            diff = git.Repo(os.getcwd()).head.commit.diff(None)
        else:
            with open(sys.argv[2], "r") as hashfile:
                last_hash = hashfile.readline()
            print(f"COMPARING WITH {last_hash}")
            repo = git.Repo(os.getcwd())
            diff = repo.head.commit.diff(repo.commit(last_hash))
    except (FileNotFoundError, git.exc.BadName, IsADirectoryError) as e:
        print("NO LAST TESTED STATE FOUND, RUNNING ALL TESTS")
        main.unit_test([test['name'] for test in main.get_available_tests()])
        return

    tests_changed = list()
    pages_changed = list()
    other_changed = list()
    categories_changed = list()

    for diffobj in diff:
        if diffobj.b_path.startswith("web_"):
            continue
        if diffobj.b_path.startswith("framework/tests"):
            category_name = os.path.split(os.path.split(diffobj.b_path)[0])[1]
            test_name = os.path.split(diffobj.b_path)[1]
            if test_name.startswith("test_"):
                tests_changed.append(test_name[:-3])
            else:
                categories_changed.append(category_name)
        elif diffobj.b_path.startswith("framework/pages_for_test"):
            page_name = diffobj.b_path[len("framework/pages_for_test/"):]
            pages_changed.append(page_name)
        else:
            other_changed.append(diffobj.b_path)

    test_page_mapping = main.get_page_to_test_mapping()

    tests_to_run = set()

    print([diffobj.b_path for diffobj in diff])
    if len(tests_changed) > 0:
        print(f"{len(tests_changed)} TESTS CHANGED:")
        for name in tests_changed:
            print(name)
            tests_to_run.add(name)
    if len(categories_changed) > 0:
        print(f"{len(categories_changed)} CATEGORIES HAVE NON-TEST CHANGED FILES:")
        for name in categories_changed:
            print(name)
    if len(pages_changed) > 0:
        print(f"{len(pages_changed)} TEST PAGES CHANGED:")
        for name in pages_changed:
            if name in test_page_mapping:
                print(f"{name} - {test_page_mapping[name]}")
                tests_to_run.update(test_page_mapping[name])
    if len(other_changed) > 0:
        print(f"{len(other_changed)} OTHER FRAMEWORK FILES CHANGED:")
        for name in other_changed:
            print(name)

    if len(other_changed) > 0:
        print("NON-TEST FRAMEWORK FILES CHANGED, RUNNING ALL TESTS")
        main.unit_test([test['name'] for test in main.get_available_tests()])
        return

    print("--- WILL RUN THE FOLLOWING TESTS: ---")
    for test in tests_to_run:
        print(test)

    main.unit_test(tests_to_run)


if __name__ == "__main__":
    main_func()

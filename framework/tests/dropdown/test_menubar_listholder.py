""" All test_menubar_* test files was added for future menubar feature but was not released at creating phase"""

__all__ = []

framework_version = 0
WCAG = "4.1.2"
name = "Ensure that menubar listholders have correct role"
depends = ["test_dropdown_detector"]
elements_type = "menubar"
test_data = [
    {
        "page_info": {"url": r""},
        "expected_status": "PASS"
    },
    {
        "page_info": {"url": r""},
        "expected_status": "FAIL"
    },
]

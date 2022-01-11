""" All test_menubar_* test files was added for future menubar feature but was not released at creating phase"""

__all__ = []

framework_version = 0
WCAG = "2.1.1"  # TODO set
name = "Ensure that menubar have correct navigation mechanism"
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

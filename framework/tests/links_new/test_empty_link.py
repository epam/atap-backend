framework_version = 5
# 2.4.4 и 4.1.2
WCAG = '2.4.3'
name = "Ensures that empty visually hidden links do not receive focus (2.4.3, 2.4.4, 4.1.2)"
elements_type = "link"
depends = ["test_base_link"]
webdriver_restart_required = False
test_data = [
    {
        "page_info": {
            "url": "links_new/page_good_test_empty_link.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links_new/page_good_test_empty_link_2.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links_new/page_bug_test_empty_link.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 1
        }
    }
]


"""
Проверить, что нет пустых ссылок. 

Пример бага: <a class="include" href="#author"></a>

Фейл 2.4.4 и 4.1.2. 
"""


def test(webdriver_instance, activity, element_locator, dependencies):
    base_test_result = dependencies['test_base_link']
    if not base_test_result['checked_elements']:
        return {'status': "NOELEMENTS",
                'message': 'There are no links for testing.',
                'elements': [],
                'checked_elements': []}
    elif not base_test_result['test_empty_link']:
        return {'status': "PASS",
                'message': 'No empty links were found.',
                'elements': base_test_result['test_empty_link'],
                'checked_elements': base_test_result['checked_elements']}
    else:
        return {'status': "FAIL",
                'message': 'Empty links found!',
                'elements': base_test_result['test_empty_link'],
                'checked_elements': base_test_result['checked_elements']}

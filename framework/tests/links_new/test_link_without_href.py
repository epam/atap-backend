framework_version = 5
# + 4.1.1
WCAG = '2.1.1'
name = "Ensures that all links have the href attribute"
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
            "url": "links_new/page_bug_test_link_without_href.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 1
        }
    }
]


"""
проверять наличие href атрибута у ссылок (фейл пунктов 2.1.1 и 4.1.1). 
Если у ссылок проставлена другая роль (напр, role=button), отсутствие href атрибута не будет являться нарушением. 

Пример, когда не использован href атрибут, но это не является багом, поскольку указана role=”button”: 
https://www.w3.org/TR/wai-aria-practices-1.1/examples/button/button.html  

Пример бага: https://stackoverflow.com/ в футере ссылка Mobile 
"""


def test(webdriver_instance, activity, element_locator, dependencies):
    """
    false negative result EXAMPLE:
    link: https://stackoverflow.com/
    element: this is a button -> skip
    <a class="s-btn s-btn__muted s-btn__icon js-notice-close" aria-label="notice-dismiss">
                    <svg aria-hidden="true" class="svg-icon iconClear" width="18" height="18" viewBox="0 0 18 18">
                    <path d="M15 4.41L13.59 3 9 7.59 4.41 3 3 4.41 7.59 9 3 13.59 4.41 15 9 10.41 13.59 15 15 13.59 10.41 9 15 4.41z"></path>
                    </svg>
                </a>


    :param webdriver_instance:
    :param activity:
    :param element_locator:
    :param dependencies:
    :return:
    """
    base_test_result = dependencies['test_base_link']

    if not base_test_result['checked_elements']:
        return {'status': "NOELEMENTS",
                'message': 'There are no links for testing.',
                'elements': [],
                'checked_elements': []}
    elif not base_test_result['test_link_without_href']:
        return {'status': "PASS",
                'message': 'No links were found without href.',
                'elements': base_test_result['test_link_without_href'],
                'checked_elements': base_test_result['checked_elements']}
    else:
        return {'status': "FAIL",
                'message': 'Links without the href attribute were found.',
                'elements': base_test_result['test_link_without_href'],
                'checked_elements': base_test_result['checked_elements']}

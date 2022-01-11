from .spacing_scripts import spacing_tools_script, criterion_checker_script,\
    element_collection_script, computed_style_observer_script, element_intersection_script,\
    jquery_check_script, execute_on_promise_script, main_js
from framework.js_conductor import CompoundJavascriptEngager, eval_js
from framework.element import Element
from framework.libs.hide_cookie_popup import hide_cookie_popup


framework_version = 5
WCAG = '1.4.12'
name = '''Ensures that text spacing rules are successfully applied for elements and there are no collisions after that'''
depends = []
webdriver_restart_required = True
elements_type = "text"
test_data = [
    {
        "page_info": {
            "url": "spacing/page_good_spacing.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "spacing/page_bug_spacing.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 7
    }
]


def test(webdriver_instance, activity, element_locator):
    """
    result = {
            'status': <'FAIL', 'PASS' or 'NOTRUN'>,
            'message': <string>,
            'elements': [],
            'checked_elements': []
        } 
    """
    return TextSpacingTest(webdriver_instance, activity, element_locator).result


def error2message(err):
    return {
        "TextContentCollision": "Text content is cropped or has intersection with other element",
        "RulesNotApplied": "All of text spacing rules were ignored",
        "SomeRulesNotApplied": "Some text spacing rules were ignored",
        "OtherStyleChanges": "Text spacing rules were followed by unwanted style changes",
    }.get(err)


class TextSpacingTest(CompoundJavascriptEngager):
    def __init__(self, webdriver_instance, activity, element_locator, timeout=10):
        scripts = [computed_style_observer_script, spacing_tools_script, criterion_checker_script,
                    element_collection_script, element_intersection_script,
                    jquery_check_script, execute_on_promise_script]
        script_names = ["computedObserver", "spacing", "criterionChecker",
                        "collection", "intersection", "jQuery", "onPromise"]
        super().__init__(webdriver_instance, activity, element_locator,
                            scripts=scripts, script_names=script_names, timeout=timeout)
        self._main()
        
    def _main(self):
        self.activity.get(self.driver)
        self.register_js(self.register_script, self.onpage_scripts)
        hide_cookie_popup(self.driver, self.activity,
            target_element=self.driver.execute_script('return document.body;'))
        self.js_execution_scheduler()
        self.report_result()

    def js_execution_scheduler(self):
        """
            Some sort of "main" function for javascript run. All steps one by one.
            Connection of libraries, test scripts.
            Initialization of global variables, script activations with async waits.
            Checked elements and bugs return
        """
        js_async_wrap = 'window.Timeout(arguments[0], `{}`, `{}`, {});'

        eval_js("onPromise", "jQuery",
            recorder=self.fetch_script_source,
            evaluator=self.execute_script_eval,
            eval_confirm_async=map(self.driver.execute_async_script, [js_async_wrap.format("window.withJQuery()", "jQuery(document.body)", "50")])
        )

        eval_js("collection", "computedObserver", "spacing", "intersection", "criterionChecker",
            recorder=self.fetch_script_source,
            evaluator=self.execute_script_eval,
            eval_confirm_async=map(self.driver.execute_async_script, [
                js_async_wrap.format("window.ComputedStyleObserver !== undefined && window.computedStyleAttributes !== undefined",
                    "new ComputedStyleObserver()", "20")     
                ])
        )

        main_timeouts = [
            ["true", "true", "1000"],
            ["window.collidedTextNodes !== undefined", "true", "100"],
            ["window.textNodes !== undefined && window.spacingRulesCounts.length > 0", "window.spacingRulesCounts[0]", "30"],
            ["window.spacingReported.length === window.spacingRulesCounts.length", "true", "20"],
            ["window.collector.encountered", "true", "300"],
            ["window.collidedTextNodes.length > 0 && window.collidedTextNodes[0].assoc === undefined", "true", "25"],
        ]

        main_timeouts = list(map(lambda t: js_async_wrap.format(*t), main_timeouts))
        for _, t in zip(main_js.split('**************************************************************'), main_timeouts):
            self.driver.execute_script(_)
            self.driver.execute_async_script(t)

        self.text_elements = [Element(elem, self.driver) for elem in
            self.driver.execute_script('return window.textNodes')]
        self.bug_text_elements = [{
            'element': Element(elem.get('element'), self.driver),
            'message': error2message(elem.get('error')),
            'error_id': elem.get('error'),
            'severity': "FAIL",
            } for elem in
            self.driver.execute_script('return window.nastyTextNodes')]

    def report_result(self):
        self.result = {'status': "PASS", 'message': "Text spacing rules work fine", 'elements': [], 'checked_elements': []}
        if not self.bug_text_elements:
            body_base = Element(self.driver.execute_script('return document.body;'), self.driver)
            body_base = {
                "element": Element(self.driver.execute_script('return document.body;'), self.driver),
                "problem": "Screenshot body",
                }
            self.result['elements'].append(body_base)
            return
        
        self.result['status'] = "FAIL"
        self.result['message'] = "There are violations after text spacing rules application"
        self.result['elements'] = self.bug_text_elements
        self.result['checked_elements'] = self.text_elements


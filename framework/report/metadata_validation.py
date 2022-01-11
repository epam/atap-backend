# metadata example

# for Conformance Table
"""
wcag_table_info = {"1.1.1":
                       {"reference": "1.1.1 Non-text Content (Level A): All non-text content that is presented to the "
                                     "user has a text alternative that serves the equivalent purpose, except for the "
                                     "situations listed below: - Controls, Input: If non-text content is a control or "
                                     "accepts user input, then it has a name that describes its purpose",

                        "web": "All images, form image buttons, and image map hot spots have appropriate, equivalent "
                               "alternative text. Images that do not convey content, are decorative, or contain content"
                               " that is already conveyed in text are given null alt text (alt="") or implemented as "
                               "CSS backgrounds. All linked images have descriptive alternative text.",


                        "level": "A"

                        "link_2.1": "https://www.w3.org/WAI/WCAG21/Understanding/non-text-content.html",
                        "link_2.0": ""},
                   }
"""

"""
references = [
    {"name": "WCAG 2.1 Guidelines:", "link": "https://www.w3.org/TR/WCAG21/",},
    {"name": "WAI-ARIA 1.1 specification:", "link": "https://www.w3.org/TR/wai-aria-1.1/"}
]
"""

"""
sr_versions = [
    {"name": "JAWS", "version": "2020", "browser": {"name": "Chrome", "version": "81"}},
    {"name": "NVDA", "version": "2019", "browser": {"name": "Firefox", "version": "75"}}
]
"""

"""
test_info = {
    "area-alt": {
        "issue_type": "WCAG 1.1.1 - Ensures <area> elements of image maps have alternate text",
        "issue_title": "Ensures <area> elements of image maps have alternate text",
        "intro": "The non-text content such as images or other visual content makes information easier to understand for "
                 "many people. Luckily, there is a way to provide the same experience for visually impaired people as well."
                 " Providing text alternatives allows the content to be presented in an appropriate way for a variety of "
                 "assistive technologies.  ",
        "expected_result": "The key images that are essential for understanding context have alternative text or in case "
                           "these are decorative ones they should be hidden from scren reader users: <area> elements of "
                           "image maps have alternative text.",
        "actual_result": "mmm",
        "type_of_disability": "",
        "techniques": "",
        "recommendations": "",
        "priority": "Blocker",
        "wcag": "1.1.1",
    }
}
"""


def references_validation(references) -> bool:
    return all("name" in d and "link" in d for d in references)


def test_info_validation(test_info) -> bool:
    return all('issue_type' in d and 'issue_title' in d and 'intro' in d and 'expected_result' in d
               and 'actual_result' in d and 'type_of_disability' in d and 'techniques' in d and 'recommendations' in d
               and 'priority' in d for d in test_info.values())


def sr_versions_validation(sr_versions) -> bool:
    return all('version' in d and 'name' in d and 'browser'in d and 'name' in d['browser'] and 'version' in d['browser']
               for d in sr_versions)


def wcag_table_info_validation(wcag_table_info) -> bool:
    return all('reference' in d and 'web' in d and 'level' in d and 'link_2.1' in d for d in wcag_table_info.values())


def metadata_validation(references, wcag_table_info, test_info, sr_versions) -> bool:
    return references_validation(references) and test_info_validation(test_info) and \
           sr_versions_validation(sr_versions) and wcag_table_info_validation(wcag_table_info)

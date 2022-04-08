import xlrd
import re
from collections import defaultdict


def load_metadata():
    workbook = xlrd.open_workbook("framework/Metadata.xlsx")

    sr_sheet = workbook.sheet_by_name("SR Versions and Combinations")
    rows = sr_sheet.get_rows()
    header = True
    sr_versions = list()

    for row in rows:
        if header:
            header = False
            continue
        sr_versions.append(
            {"name": row[0].value, "version": row[1].value, "browser": {"name": row[2].value, "version": row[3].value}})

    references = list()
    for row in workbook.sheet_by_name("References").get_rows():
        references.append({"name": row[0].value, "link": row[1].value})

    # "1.1.1":
    # {
    #     "reference": "1.1.1 Non-text Content (Level A): All non-text content that is presented to the "
    #                  "user has a text alternative that serves the equivalent purpose, except for the "
    #                  "situations listed below: - Controls, Input: If non-text content is a control or "
    #                  "accepts user input, then it has a name that describes its purpose",
    #
    #     "web": "All images, form image buttons, and image map hot spots have appropriate, equivalent "
    #            "alternative text. Images that do not convey content, are decorative, or contain content"
    #            " that is already conveyed in text are given null alt text (alt="") or implemented as "
    #            "CSS backgrounds. All linked images have descriptive alternative text.",
    #
    #     "level": "A",
    #
    #     "link_2.1": "https://www.w3.org/WAI/WCAG21/Understanding/non-text-content.html",
    #     "link_2.0": ""}

    wcag_table_info = dict()
    header = True

    for row in workbook.sheet_by_name("Reference to standards").get_rows():
        if header:
            header = False
            continue
        wcag_table_info[row[0].value] = {
            "reference": row[1].value,
            "link_2.1": row[2].value,
            "link_2.0": row[3].value,
            "name": row[4].value
        }

    header = True

    for row in workbook.sheet_by_name("Conformance Level -Web").get_rows():
        if header:
            header = False
            continue
        wcag_table_info[row[0].value]["web"] = row[1].value

    header = True

    for row in workbook.sheet_by_name("WCAG 2.1 Conformance").get_rows():
        if header:
            header = False
            continue
        wcag_table_info[row[0].value]["level"] = row[2].value

    problem_type_data = {}
    """
        problem_type_data = {
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
                "groups": ["Fast Run", "Major", "A"],
                "labels": ["Other Issues", "ARIA"],
            }
        }
        """

    header = True

    for row in workbook.sheet_by_name("Intro").get_rows():
        if header:
            header = False
            continue
        if row[0].value == "":
            continue
        problem_type_data[row[0].value] = {
            "intro": row[2].value.replace('_x000D_', '<br/>')
        }

    header = True

    for row in workbook.sheet_by_name("Expected result").get_rows():
        if header:
            header = False
            continue
        if row[0].value == "":
            continue
        problem_type_data[row[0].value]["expected_result"] = row[2].value

    header = True

    for row in workbook.sheet_by_name("Actual result").get_rows():
        if header:
            header = False
            continue
        if row[0].value == "":
            continue
        problem_type_data[row[0].value]["actual_result"] = row[2].value

    header = True

    for row in workbook.sheet_by_name("Type of disability affected").get_rows():
        if header:
            header = False
            continue
        if row[0].value == "":
            continue
        problem_type_data[row[0].value]["type_of_disability"] = row[2].value

    header = True

    for row in workbook.sheet_by_name("Techniques").get_rows():
        if header:
            header = False
            continue
        if row[0].value == "":
            continue
        problem_type_data[row[0].value]["techniques"] = row[2].value
        problem_type_data[row[0].value]["techniques_2_0"] = row[3].value

    header = True

    for row in workbook.sheet_by_name("Recommendations").get_rows():
        if header:
            header = False
            continue
        if row[0].value == "":
            continue
        problem_type_data[row[0].value]["recommendations"] = row[2].value

    header = True

    for row in workbook.sheet_by_name("Priority").get_rows():
        if header:
            header = False
            continue
        if row[0].value == "":
            continue
        problem_type_data[row[0].value]["priority"] = row[2].value

    header = True

    for row in workbook.sheet_by_name("Issues Titles").get_rows():
        if header:
            header = False
            continue
        if row[0].value == "":
            continue
        problem_type_data[row[0].value]["issue_type"] = row[1].value
        problem_type_data[row[0].value]["issue_title"] = row[2].value
        problem_type_data[row[0].value]["WCAG-BP"] = "BP" if row[3].value.split(",")[0] == "BP" else "WCAG"
        WCAG = []
        paragraphs = row[3].value.split(",")
        for paragraph in paragraphs:
            if len(paragraph) > 4:
                WCAG.append(paragraph.strip())
        if len(WCAG) == 0:
            print("Could not parse WCAG value from", row[3].value.split(","))
            WCAG = ['1.3.1']
        problem_type_data[row[0].value]["WCAG"] = ', '.join(WCAG)
        problem_type_data_groups = list(filter(bool, row[9].value.split(', ')))
        problem_type_data[row[0].value]["groups"] = problem_type_data_groups
        problem_type_data_labels = list(filter(bool, row[5].value.split(', ')))
        problem_type_data[row[0].value]["labels"] = problem_type_data_labels

    header = True
    wcag_test_matching = defaultdict(dict)

    def match(s):
        re.match(r'\d+\.\d+\.\d+', s)

    def findall(s):
        tmp = re.findall(r'\d+', s)
        return tmp if tmp is not None else ''

    for row in workbook.sheet_by_name("Priority and Conformance").get_rows():
        if header:
            header = False
            continue
        wcag = row[0].value if match(row[0].value) is not None else ".".join(findall(row[0].value))
        wcag_test_matching[wcag][row[1].value] = {
            'priority': row[3].value,
            'conformance_level': row[4].value,
            'percent': int(row[5].value) if row[5].value else 0,
            'weight': float(row[6].value) if row[6].value else 0,
            'test': row[7].value if row[7].value[0:4] == 'test_' else ''
        }

    chapters_508 = {"3": {"name": "Functional Performance Criteria (FPC)", "criteria": dict()},
                    "4": {"name": "Hardware", "criteria": dict()},
                    "5": {"name": "Software", "criteria": dict()},
                    "6": {"name": "Support Documentation and Services", "criteria": dict()}}

    chpters_en = {"4": {"name": "Functional Performance Statements (FPS)", "criteria": dict()},
                  "5": {"name": "Generic Requirements", "criteria": dict()},
                  "6": {"name": "ICT with Two-Way Voice Communication", "criteria": dict()},
                  "7": {"name": "ICT with Video Capabilities", "criteria": dict()},
                  "8": {"name": "Hardware", "criteria": dict()},
                  "9": {"name": "Web", "criteria": dict()},
                  "10": {"name": "Non-Web Software", "criteria": dict()},
                  "11": {"name": "Sortware", "criteria": dict()},
                  "12": {"name": "Documentation and Support Services", "criteria": dict()},
                  "13": {"name": "ICT Providing Relay or Emergency Service Access", "criteria": dict()}}

    vpat_data = {"wcag": dict(), "508": chapters_508, "EN": chpters_en}

    product_types_wcag = ['Web', 'Electronic Docs', 'Software', 'Authoring Tool', 'Closed']
    product_types_508 = ['Web', 'Electronic Docs', 'Software', 'Authoring Tool', 'Closed', 'no product type needed']
    levels = ['Supports', 'Partially Supports', 'Does Not Support', 'Not Applicable']

    header_counter = 0
    for row in workbook.sheet_by_name("WCAG 2.1 Conformance VPAT WCAG").get_rows():
        if header_counter < 2:
            header_counter += 1
            continue
        collumn_counter = 1
        for product in product_types_wcag:
            title = row[0].value
            paragraph = title.split(' ')[0]
            for num, level in enumerate(levels):
                if paragraph not in vpat_data["wcag"]:
                    vpat_data["wcag"][paragraph] = dict()
                if "title" not in vpat_data["wcag"]:
                    vpat_data["wcag"][paragraph]["title"] = title
                if product not in vpat_data["wcag"][paragraph]:
                    vpat_data["wcag"][paragraph][product] = dict()
                vpat_data["wcag"][paragraph][product][level] = row[collumn_counter + num].value
            collumn_counter += 4

    header_counter = 0
    for row in workbook.sheet_by_name("WCAG 2.1 Conformance VPAT 508").get_rows():
        if header_counter < 2:
            header_counter += 1
            continue
        collumn_counter = 1
        for product in product_types_508:
            for num, level in enumerate(levels):
                title = row[0].value
                if (product != 'no product type needed' and title[0] == '3') or (
                        product == 'no product type needed' and title[0] != '3'):
                    if title not in vpat_data["508"][title[0]]['criteria']:
                        vpat_data["508"][title[0]]['criteria'][row[0].value] = dict()
                    if product not in vpat_data["508"][title[0]]['criteria'][row[0].value]:
                        vpat_data["508"][title[0]]['criteria'][row[0].value][product] = dict()
                    vpat_data["508"][title[0]]['criteria'][row[0].value][product][level] = row[
                        collumn_counter + num].value
            collumn_counter += 4

    header_counter = 0
    for row in workbook.sheet_by_name("WCAG 2.1 Conformance VPAT EN").get_rows():
        if header_counter < 2:
            header_counter += 1
            continue
        collumn_counter = 1
        for product in product_types_508:
            for num, level in enumerate(levels):
                title = row[0].value
                if (product != 'no product type needed' and title[0] == '4') or (
                        product == 'no product type needed' and title[0] != '4'):
                    if title not in vpat_data["EN"][title[0]]['criteria']:
                        vpat_data["EN"][title[0]]['criteria'][row[0].value] = dict()
                    if product not in vpat_data["EN"][title[0]]['criteria'][row[0].value]:
                        vpat_data["EN"][title[0]]['criteria'][row[0].value][product] = dict()
                    vpat_data["EN"][title[0]]['criteria'][row[0].value][product][level] = row[
                        collumn_counter + num].value
            collumn_counter += 4

    test_groups = []
    for row in workbook.sheet_by_name('Groups').get_rows():
        test_groups.append({'name': row[0].value, 'status': row[1].value})

    return references, wcag_table_info, problem_type_data, sr_versions, vpat_data, wcag_test_matching, test_groups


(
    cached_references,
    cached_wcag_table_info,
    cached_problem_type_data,
    cached_sr_versions,
    cached_vpat_data,
    cached_wcag_test_matching,
    cached_test_groups
) = load_metadata()


def get_data_for_issue(issue_name):
    if issue_name in cached_problem_type_data:
        return cached_problem_type_data[issue_name]
    else:
        issue_data = {
            'WCAG-BP': 'BP',
            'priority': 'Minor',
            'WCAG': '1.3.1'
        }
        for parameter in (
                'issue_title',
                'issue_type',
                'recommendations',
                'techniques',
                'type_of_disability',
                'actual_result',
                'expected_result',
                'intro'
        ):
            issue_data[parameter] = f'#{issue_name}:{parameter}'
        issue_data['groups'] = []
        issue_data['labels'] = []
        return issue_data

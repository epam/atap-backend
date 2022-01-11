import json


with open("framework/mappings.json", "r", encoding="utf-8") as f:
    VPAT_MAPPING = json.load(f)

VPAT_SUPPORT_LEVELS = ["NA", "SUP", "DNS"]


def map_error_id(WCAG, err_id):
    if WCAG not in VPAT_MAPPING:
        return "ERROR: UNKNOWN WCAG"
    if err_id not in VPAT_MAPPING[WCAG]["DNS"]:
        return "ERROR: UNKNOWN ERROR ID"
    return VPAT_MAPPING[WCAG]["DNS"][err_id]


def to_vpat_format(tests):
    vpat = {}
    for test in tests:
        if test.status not in ["PASS", "WARN", "FAIL", "NOELEMENTS"]:
            print(f"WARNING: {test.name} has status '{test.status}'")
            continue
        if test.WCAG is None:
            print(f"=>WARNING: test {test.name} has no WCAG attribute")
            continue
        if test.WCAG not in VPAT_MAPPING:
            print(f"=>ERROR: test {test.name} has unknown WCAG attribute '{test.WCAG}'")
            continue
        if test.WCAG not in vpat:
            vpat[test.WCAG] = {
                "name": VPAT_MAPPING[test.WCAG]["Name"],
                "level": VPAT_MAPPING[test.WCAG]["Level"],
                "status": "NA",
                "error_ids": set(),
                "WCAG": test.WCAG,
                "checked_elements": set(),
                "problematic_elements": set()
            }

        if test.framework_version >= 3:
            vpat[test.WCAG]["problematic_elements"].update([entry["element"] for entry in test.problematic_elements])
            vpat[test.WCAG]["checked_elements"].update(test.checked_elements)

        if test.status == "NOELEMENTS":
            status = "NA"
        elif test.status in ["PASS", "WARN"]:
            status = "SUP"
        else:
            status = "DNS"

        if VPAT_SUPPORT_LEVELS.index(status) > VPAT_SUPPORT_LEVELS.index(vpat[test.WCAG]["status"]):
            vpat[test.WCAG]["status"] = status

        if status == "DNS":
            if len(test.problematic_elements) == 0:
                vpat[test.WCAG]["error_ids"].add(list(VPAT_MAPPING[test.WCAG]["DNS"].keys())[0])
            else:
                for element in test.problematic_elements:
                    vpat[test.WCAG]["error_ids"].add(element["error_id"])

    for wcag_info in vpat.values():
        if len(wcag_info["checked_elements"]) != 0:
            wcag_info["conformance_percent"] = int(100 - len(wcag_info["problematic_elements"])/len(wcag_info["checked_elements"])*100)
        else:
            if wcag_info["status"] == "SUP":
                wcag_info["conformance_percent"] = 100
            else:
                wcag_info["conformance_percent"] = 0

    print(vpat)
    return vpat

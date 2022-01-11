import json

ELEMENTS = [
    "link",
    "image",
    "button",
    "menu button",
    "toggle button",
    "spin button",
    "tooltip",
    "menubar",
    "selector",
    "edit field",
    "combobox",
    "tabpanel",
    "slider",
    "modal window",
    "dialog window",
    "radio",
    "checkbox",
    "tabpanel",
    "drag and drop",
    "table",
    "carousel",
    "accordion",
    "slider",
    "video",
    "audio",
    "form",
    "captcha",
    "list",
    "countdown",
    "text",
]

common_pages = {
        "https://www.epam.com/careers": [
            "slider",
            "link",
            "menu button",
            "button",
            "menubar",
            "selector",
            "tabpanel",
            "image",
            "slider",
            "tooltip",
            "combobox"
        ],
        "https://www.epam.com/": [

        ],
        "https://www.epam.com/about": [
            "video"
        ],

        r"https://www.nsw.gov.au/your-government/ministers/"
        r"deputy-premier-minister-for-regional-new-south-wales-industry-and-trade/": [
            "form",
            "captcha",
            "checkbox",
            "edit field"
        ],

        r"https://www.atlassian.com/licensing/purchase-licensing#pricing-discounts":[
            "accordion"
        ],

        r"https://online-timer.ru/tochnoe-moskovskoe-vremya/": [
            "countdown"
        ],

        r"https://www.atlassian.com/software/confluence": [
            "carousel"
        ],

        r"https://www.w3.org/TR/wai-aria-practices/examples/spinbutton/datepicker-spinbuttons.html": [
            "spin button",
            "table"
        ],

        r"https://www.nytimes.com/": [
            "text",
            "list"
        ],

        r"https://mdbootstrap.com/docs/jquery/forms/switch/": [
            "toggle button"
        ],

        "https://mdbootstrap.com/plugins/jquery/draggable/": [
            "drag and drop"
        ],

        "https://webaim.org/techniques/forms/controls": [
            "radio"
        ],

        "http://web-accessibility.carnegiemuseums.org/code/dialogs/": [
            "modal window",
            "dialog window"
        ],

        "https://music.yandex.ru/artist/168851": [
            "audio"
        ]
    }


def map_pages(pages=common_pages):
    mapping = dict()
    for page, page_elements in pages.items():
        if len(page_elements) == 0:
            mapping[""] = page
            continue
        else:
            for element in page_elements:
                mapping[element] = page

    for element in ELEMENTS:
        if element not in mapping.keys():
            mapping[element] = mapping[""]

    with open("framework/time_of_tests/average_pages.json", "w", encoding="utf-8") as file:
        json.dump(mapping, file, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    map_pages(common_pages)
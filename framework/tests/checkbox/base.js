const { diff } = require('semver');

class CheckboxBase {
    constructor() {
        this.buttons = {
            possibleButtons: [],
            buttons: [],
            links: [],
            nonIntractable: [],
        };
        this.sorted_types = {
            input: [],
            other: [],
        };

        this.possibleKeywords = 'checkbox|check';
        this.possibleCheckboxes = {};
        this.main();
    }

    main() {
        var locatorElements = this.collectButtons();
        this._filter(locatorElements);
        if (!this.buttons['buttons']) {
            this.result['status'] = 'NOELEMENTS';
            this.result['message'] = 'No checkbox elements';
            this.result['elements'] = [];
        } else {
            this.set_pass_status();
            this.sortInput();
            this.possibleCheckboxes = new Set(this.buttons.buttons.map((btn) => [btn]));
            Element.safe_foreach(this.sorted_types['input'], this._mark_native_inputs);
            Element.safe_foreach(this.sorted_types['other'], this.detect_possible_checkbox);
            this._push_dependency();
        }
    }

    collectButtons() {}

    _filter() {}

    sortInput() {}
}

/*
var click_sort = function(element, data) {
    var action;

    if (element.tagName === "A") {
        var href = element.getAttribute("href");
        if (href && /^\w+|\/\w+/.test(href)) { console.log('href!', element); return false; }
    }

    action = element.click(self.driver)["action"];



    if action == "NONINTERACTABLE":  # check overlapping
        self.activity.get(self.driver)
        try:
            action = element.click(self.driver)["action"]
        except UnexpectedAlertPresentException:
            try:
                alert = self.driver.switch_to.alert
                alert.dismiss()
            except NoAlertPresentException:
                pass
    if action == "NONE":
        # tricky use later in style_diff (after remove)
        self.buttons["possible_buttons"].append(element)
    elif action != "NONINTERACTABLE":
        self.buttons["links"].append(element)
        self.activity.get(self.driver)
    else:
        self.buttons["non_intractable"].append(element)
};
*/

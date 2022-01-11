autologin_tool_script = """
    (function () {
    "use strict";

    class AutoLoginHelper {
        constructor(allowedLoginType = "email") {
        this.allowedLoginType = allowedLoginType;
        this.formObjects = this.loginFormInit;
        this.submitForms();
        this.formValues = this.loginInputFields;
        }

        get loginFormInit() {
        let loginForms = [...document.forms].filter((form) => isVisible(form));

        if (loginForms.length > 1) {
            loginForms = loginForms.filter(
            (form) => UIEditElements(form).length > 2
            );
        }
        
        else if (!loginForms.length) {
            loginForms = [document.body];
        }

        const formObjects = new Map(loginForms.map((form) => [form, {}]));

        formObjects.forEach((obj, elem) => {
            const [fields, submitBtn] = new Array(2).fill(undefined);
            const data = {
            fields,
            submitBtn,
            };
            formObjects.set(elem, data);
        });

        return formObjects;
        }

        submitForms() {
        this.formObjects.forEach((obj, elem) => {
            Object.assign(obj, actionLogin(elem));
        });
        }

        get loginInputFields() {
        const inputData = { submit: [], login: [], password: [] };
        // * by the way, drops non-login forms
        this.formObjects.forEach((obj, elem) => {
            // * must be a login form: log in button or password at least
            // * cause of allowedLoginType won't trigger any error on submit
            const loginArray = obj.fields.filter(
            (node) =>
                ["text", this.allowedLoginType].includes(node.type) ||
                node.tagName === "TEXTAREA"
            );
            const passwordArray = obj.fields.filter(
            (node) => node.type === "password"
            );

            if (!obj.submitBtn) {
            if (passwordArray.length) {
                inputData.login.push(...loginArray);
                inputData.password.push(...passwordArray);
            }
            return;
            }
            inputData.submit.push(obj.submitBtn);
            inputData.login.push(...loginArray);
            inputData.password.push(...passwordArray);
        });

        return inputData;
        }
    }

    var actionLogin = function (form) {
        const fetched = { submitBtn: undefined, fields: undefined };

        fetched.fields = UIEditElements(form);
        fetched.submitBtn = loginButton(form, fetched.fields);

        return fetched;
    };

    var isVisible = function (node) {
        const style = window.getComputedStyle(node);
        const physical =
        node.tagName === "BODY" ||
        (node.offsetParent &&
            node.offsetWidth > 10 &&
            node.offsetHeight > 10 &&
            node.getBoundingClientRect().width > 10 &&
            node.getBoundingClientRect().height > 10);
        const solid =
        style.visibility !== "hidden" &&
        style.display !== "none" &&
        style.opacity > 0.1;

        return physical && solid;
    };

    var formAdjacentBodyElements = function () {
        const bodyFields = [];

        const path = `//body/descendant::*[not(ancestor::form)]`;
        const query = document.evaluate(
        path,
        document,
        null,
        XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
        null
        );

        for (let i = 0, length = query.snapshotLength; i < length; ++i) {
        bodyFields.push(query.snapshotItem(i));
        }

        return bodyFields;
    };

    var realFormElement = function (node) {
        return (
        node.offsetParent instanceof Element &&
        node.offsetHeight * node.offsetWidth > 50 &&
        (typeof node.value === "string" ||
            Array.from(node.children, (opt) => opt.tagName === "OPTION").length ||
            node.disabled !== undefined ||
            node.onclick !== null)
        );
    };

    var UIEditElements = function (form) {
        const textTypes = ["text", "tel", "email", "password", "submit"];
        let editFields =
        form.tagName == "FORM" ? form.elements : formAdjacentBodyElements();
        const allowedTags = ["INPUT", "TEXTAREA", "BUTTON"];

        editFields = [...editFields].filter(
        (field) => allowedTags.includes(field.tagName) && realFormElement(field)
        );

        // * others can be disabled on condition
        const textFields = editFields.filter(
        (field) =>
            field.tagName === "TEXTAREA" ||
            (field.tagName === "INPUT" && textTypes.includes(field.type))
        );

        textFields.forEach((box) => {
        const boxValue = editFields[editFields.indexOf(box)].value;

        editFields[editFields.indexOf(box)].value = boxValue || "Value Test";
        });

        editFields = editFields.filter(
        (field) =>
            !["INPUT", "TEXTAREA"].includes(field.tagName) ||
            field.tagName === "TEXTAREA" ||
            (field.tagName === "INPUT" &&
            (!textTypes.includes(field.type) || field.value !== ""))
        );

        editFields
        .filter((field) => ["INPUT", "TEXTAREA"].includes(field.tagName))
        .forEach((box) => {
            if (box.type) {
            if (textTypes.includes(box.type)) {
                // * to not to empty fulfilled values
                box.value = box.value == "Value Test" ? "" : box.value;
            }
            }
        });

        return editFields;
    };

    var verifyLoginButton = function (btn, form) {
        if ([true, false].includes(btn.checked) && btn.type !== "submit") {
        return null;
        }

        const bottomButton = moveOrientation(btn, form) === "top";
        if (!bottomButton) {
        return null;
        }

        const keyWordArray = [...btn.attributes]
        .map((attr) => attr.value)
        .concat([btn.textContent]);
        const matchArray = keyWordArray
        .join(" ")
        .toLowerCase()
        .replace(/[\W_]+/g, " ")
        .match(
            /(continue)|(next)|(login)|(log in)|(register)|(signin)|(sign in)|(signup)|(sign up)/
        );

        return matchArray && matchArray.filter(Boolean) ? btn : null;
    };

    var loginButton = function (form, submitCandidates) {
        const lastInput = submitCandidates
        .filter((elem) => ["INPUT", "TEXTAREA"].includes(elem.tagName))
        .slice(-1)[0];

        const theButtons = submitCandidates.filter((btn) =>
        verifyLoginButton(btn, form)
        );

        // sort ascending distance to last input
        theButtons.sort(
        (btn, submit) =>
            minDistBetween(btn, lastInput) - minDistBetween(submit, lastInput)
        );

        return theButtons[0];
    };

    var minDistBetween = function (origin, elem) {
        /* calculate closest distance (from 9 perspectives) between elements */
        origin = new NodePoints(origin);
        elem = new NodePoints(elem);

        return (
        NodePoints.minAbscissa(origin, elem) +
        NodePoints.minOrdinates(origin, elem)
        );
    };

    var moveOrientation = function (origin, elem) {
        origin = new NodePoints(origin);
        elem = new NodePoints(elem);

        return NodePoints.fourSideDirection(origin, elem);
    };

    window.AutoLoginHelper = AutoLoginHelper;
    })();

    class NodePoints {
    constructor(node) {
        this.rect = node.getBoundingClientRect();
        this.top = this.rect.top;
        this.left = this.rect.left;
        this.leftX = node.getBoundingClientRect().left + window.scrollX;
        this.rightX = this.leftX + node.offsetWidth;
        this.centerX = (this.leftX + this.rightX) / 2;
        this.topY = node.getBoundingClientRect().top + window.scrollY;
        this.bottomY = this.topY + node.offsetHeight;
        this.centerY = (this.topY + this.bottomY) / 2;
    }

    static fourSideDirection(actual, opposite) {
        let direction =
        Math.abs(actual.top - opposite.top) >
        Math.abs(actual.left - opposite.left)
            ? -2
            : -1;
        direction =
        direction === -2
            ? direction * Math.sign(actual.top - opposite.top) + 2
            : direction * Math.sign(actual.left - opposite.left) + 2;

        return new Object({ 0: "top", 1: "left", 4: "bottom", 3: "right" })[
        direction
        ];
    }

    static minAbscissa(actual, opposite) {
        const abscissa = [
        actual.centerX - opposite.centerX,
        actual.leftX - opposite.centerX,
        actual.rightX - opposite.centerX,
        actual.centerX - opposite.leftX,
        actual.leftX - opposite.leftX,
        actual.rightX - opposite.leftX,
        actual.centerX - opposite.rightX,
        actual.leftX - opposite.rightX,
        actual.rightX - opposite.rightX,
        ];

        abscissa.forEach((val, idx, arr) => {
        arr[idx] = val ** 2;
        });
        return Math.min.apply(Math, abscissa);
    }

    static minOrdinates(actual, opposite) {
        const ordinates = [
        actual.centerY - opposite.centerY,
        actual.topY - opposite.centerY,
        actual.bottomY - opposite.centerY,
        actual.centerY - opposite.topY,
        actual.topY - opposite.topY,
        actual.bottomY - opposite.topY,
        actual.centerY - opposite.bottomY,
        actual.topY - opposite.bottomY,
        actual.bottomY - opposite.bottomY,
        ];

        ordinates.forEach((val, idx, arr) => {
        arr[idx] = val ** 2;
        });
        return Math.min.apply(Math, ordinates);
    }
    }
"""

login_info_js = """
    window.loginTool = new AutoLoginHelper(arguments[0]);
    return window.loginTool.formValues;
"""

execute_on_promise_script = """
    !function(){var timeout=function(callback,stopCondition,callbackValue,ms){setTimeout(promise=>{if(console.log(`${ms}`),window.onPromise=!1,window.maxTries=200,window.tryNum=window.tryNum||1,promise=new Promise((resolve,reject)=>{eval(stopCondition)?(window.onPromise=!0,resolve(window.prom)):reject()}),promise.then(o=>{},o=>{}),!(0==window.onPromise&&window.tryNum<window.maxTries))return window.tryNum=0,callback(eval(callbackValue)),!1;window.tryNum++,timeout(callback,stopCondition,callbackValue,ms)},ms)};window.Timeout=timeout}();
"""

computed_style_observer_script = """
    !function(){"use strict";let e=0,t=new Map;const r=(r,s)=>{let o=t.get(r);return o||(o={styles:{},observers:[]},t.set(r,o)),!o.observers.includes(s)&&(o.observers.push(s),1!==e&&(e=1,n()),!0)},s=(r,s)=>{let o=t.get(r);if(!o)return!1;let l=o.observers.indexOf(s);return-1!==l&&(o.observers.splice(l,1),0===o.observers.length&&t.delete(r),0===t.size&&(e=0),!0)},o=e=>{t.forEach((t,r)=>{t.observers.includes(e)&&s(r,e)})},l=(e,t)=>{let r=getComputedStyle(e),s={};t.observers.forEach(o=>{let l=[];o.properties.forEach(o=>{let n=r[o],i=t.styles[o];n!==i&&i&&l.push(new ComputedStyleObserverEntry(e,o,n,i)),s[o]=n}),l.length&&o.callback(l)}),t.styles=s},n=()=>{1===e&&(requestAnimationFrame(n),t.forEach((e,t)=>{l(t,e)}))};let i=new WeakMap;window.ComputedStyleObserver=class{constructor(e,t=null){Array.isArray(t)&&(t=[...t]),i.set(this,{callback:e,properties:t})}disconnect(){o(i.get(this))}observe(e){return r(e,i.get(this))}unobserve(e){return s(e,i.get(this))}},window.ComputedStyleObserverEntry=class{constructor(e,t,r,s){this.target=e,this.property=t,this.value=r,this.previousValue=s}}}();
"""

form_drafting_script = """
    !function(){"use strict";var e=function(e){const t=e.action||document.URL;let s=e,n=!1;const l=Object.fromEntries(["action","submitBtn","fields","fieldValues"].map(e=>[e,void 0]));for(e.addEventListener("submit",e=>{n=!0,e.preventDefault(),e.stopPropagation()});"HTML"!==s.tagName;){const e=r(s).filter(e=>!1===e.disabled||null!==e.onclick);for(const t of e.reverse())if(t.click(),n){l.submitBtn=t;break}s=s.parentElement}return n||(l.submitBtn=null),l.fields=r(e),l.fieldValues=l.fields.map(e=>[e,e.value]),l.action=t,l},t=function(e){const t=window.getComputedStyle(e),s="BODY"===e.tagName||e.offsetParent&&e.offsetWidth>10&&e.offsetHeight>10&&e.getBoundingClientRect().width>10&&e.getBoundingClientRect().height>10,r="hidden"!==t.visibility&&"none"!==t.display&&t.opacity>.1;return s&&r},s=function(e){return!!t(e)||function e(s){const r=[...s.parentElement.children].filter(e=>(!1===e.disabled||null!==e.onclick)&&t(e)).filter(e=>![...document.links].includes(e)),n=[...document.getElementsByTagName("a")].filter(e=>(function(e){const t=e.getAttribute("href");return t&&t.length&&!/^(?:\w+|\/.*)/.test(t)})(e));return r.forEach(e=>e.click()),n.forEach(e=>e.click()),s.offsetParent instanceof Element||e(s.parentElement),[...s.parentElement.parentElement.children].filter(e=>(!1===e.disabled||null!==e.onclick)&&t(e)).forEach(e=>e.click()),t(s)}(e)},r=function(e){const t=["text","tel","email","password","number","url","textarea","submit"];let s="FORM"==e.tagName?e.elements:function(){const e=[],t=document.evaluate("//body/descendant::*[not(ancestor::form)]",document,null,XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,null);for(let s=0,r=t.snapshotLength;s<r;++s)e.push(t.snapshotItem(s));return e}();const r=["INPUT","TEXTAREA","SELECT","BUTTON"],n=(s=[...s].filter(e=>r.includes(e.tagName)&&function(e){return e.offsetParent instanceof Element&&e.offsetHeight*e.offsetWidth>50&&("string"==typeof e.value||Array.from(e.children,e=>"OPTION"===e.tagName).length||void 0!==e.disabled||null!==e.onclick)}(e))).filter(e=>"TEXTAREA"===e.tagName||"INPUT"===e.tagName&&t.includes(e.type));return s="BODY"===e.tagName?n:s,n.forEach(e=>{const t=s[s.indexOf(e)].value;s[s.indexOf(e)].value=t||"Value Test"}),(s=s.filter(e=>!["INPUT","TEXTAREA"].includes(e.tagName)||"TEXTAREA"===e.tagName||"INPUT"===e.tagName&&(!t.includes(e.type)||""!==e.value))).filter(e=>["INPUT","TEXTAREA"].includes(e.tagName)).forEach(e=>{e.type&&t.includes(e.type)&&(e.value="Value Test"==e.value?"":e.value)}),s};window.AlertRegulator=class{constructor(e,t=!0){this.elements=e,this.formObjects=this.formInit,this.completeObjects(),t&&(this.setAlertsSentry(),this.formAlerts=this.alertsShell,this.completeAlerts()),this.formData=this.browserFormData}get formInit(){const e=new Map(this.elements.map(e=>[e,{}]));return e.forEach((t,s)=>{const[r,n,l,i,o]=new Array(5).fill(void 0),a={visible:r,fields:n,fieldValues:l,submitBtn:i,response:o};e.set(s,a),"BODY"===s.tagName&&(t.alert=[])}),e}get browserFormData(){const e=[];return this.formObjects.forEach((t,s)=>{if("BODY"===s.tagName)return;const r=new FormData(s),n=new Map(r.entries());e.push(n)}),e}get alertsShell(){return Array(this.formObjects.size).fill({alertElements:[],globalAlerts:[]})}completeObjects(){this.verifyVisible(),this.submitForms()}setAlertsSentry(){this.observeStyles(),this.observeMutations()}completeAlerts(){this.clickForms(),this.prepareAlerts(),this.updatePresentAlerts()}verifyVisible(){this.formObjects.forEach((e,t)=>{e.visible=s(t)})}submitForms(){this.formObjects.forEach((t,s)=>{Object.assign(t,e(s))})}clickForms(){this.formObjects.forEach((e,t)=>{e.submitBtn&&e.submitBtn.click()})}observeStyles(){this.formObjects.forEach((e,t)=>{Object.assign(e,window.recordStyles(t,e))})}fireAlertsForBody(){const e=[...this.formObjects].map(e=>e[1].submitBtn);this.formObjects.get(document.body).alertElements=window.recordMutations(document.body),this.formObjects.get(document.body).fields.filter(t=>!e.includes(t)).forEach(e=>e.click())}observeMutations(){window.alert=function(){},window.prompt=function(){},window.confirm=function(){},this.formObjects.forEach((e,t)=>{e.alertElements=[],e.globalAlerts=[],e.submitBtn instanceof Element&&(e.alertElements=window.recordMutations(t),e.globalAlerts=window.recordMutations(document.body))}),this.fireAlertsForBody()}correctGlobalAlerts(){this.formObjects.forEach((e,t)=>{const s=[];this.formObjects.forEach((e,r)=>{"BODY"!==r.tagName&&r!==t&&s.push(...e.alertElements)}),e.globalAlerts="BODY"===t.tagName?e.globalAlerts:e.globalAlerts.filter(e=>!s.includes(e))})}prepareAlerts(){const e=[];this.correctGlobalAlerts(),this.formObjects.forEach(t=>{Object.assign(t,window.preparedObjectAlerts(t,e))})}updatePresentAlerts(){this.formObjects.forEach((e,t)=>{const s=e=>e.map(e=>document.querySelector(e)).filter(e=>e&&e.isConnected),[r,n]=[s(e.alertElements),s(e.globalAlerts)],l=[...this.formObjects.keys()].indexOf(t);this.formAlerts.splice(l,1,{alertElements:r,globalAlerts:n})})}updateFieldValues(){this.formObjects.forEach((e,t)=>{e.fields=window.UIEditElements(t);const s=e.fields.map(e=>[e,e.value]);e.fieldValues=s})}},window.visibleOpen=s,window.UIEditElements=r}();
"""

styled_alerts_script = """
    !function(){"use strict";var e=function(e){const t=[];for(;e.nodeType===Node.ELEMENT_NODE;){let n=e.nodeName.toLowerCase();if(e.id){n+="#"+e.id,t.unshift(n);break}{let t=e,r=1;for(;t=t.previousElementSibling;)t.nodeName.toLowerCase()==n&&r++;n+=":nth-of-type("+r+")"}t.unshift(n),e=e.parentNode}return t.join(" > ")},t=function(e){function t(e,t){let n=0;return t.forEach(t=>{n+=e.includes(t)}),1===n}Element.prototype.getStyleObject=function(){const e={};if(window.getComputedStyle){const t=(e,t)=>t.toUpperCase(),n=window.getComputedStyle(this,null);for(const r of n){const o=r.replace(/\-([a-z])/g,t),s=n.getPropertyValue(r);e[o]=s}return e}if(this.currentStyle){const t=this.currentStyle;for(const n in t)e[n]=t[n];return e}return this.css()};const n=[],[r,o]=[window.getComputedStyle(e),window.getComputedStyle(e.parentElement)],s=Object.keys(document.body.getStyleObject()).filter(function(e){return t(e,Array("color","border","shadow","content","appearance","opacity","animation"))}).filter(e=>!t(e,["size","caret","scroll"]));for(const e of s)r[e]&&o[e]!==r[e]&&n.push(e);return n};window.selectorCSS=e,window.formOuterInstances=function(e){return e.filter(e=>![...document.forms].map(e=>[...e.getElementsByTagName("*")]).some(t=>t.includes(e)))},window.alertSensibleStyles=t,window.recordStyles=function(n,r){r.styledAlerts=[],r.styleReference=new Set;const o=function(e,t=[]){const n=[...e.getElementsByTagName("*")].filter(e=>!t.includes(e));return"BODY"===e.tagName?window.formOuterInstances(n):n}(n,[...document.links,...document.getElementsByTagName("option"),r.submitBtn]);return o.forEach(e=>{r.styleReference=new Set([...r.styleReference,...t(e)])}),r.styledAlertsObserver=new ComputedStyleObserver(t=>{try{const n=e(t[0].target);r.styledAlerts.includes(n)||r.styledAlerts.push(n)}catch(e){}},[...r.styleReference]),o.forEach(e=>{r.styledAlertsObserver.observe(e)}),r}}();
"""

record_alerts_script = """
    !function(){"use strict";const e=function(e,t){if(!e||1!==e.nodeType)return;const n=new window.MutationObserver(t);return n.observe(e,{childList:!0,CharacterData:!0,subtree:!0,attributes:!0,attributeFilter:["class"]}),n};var t=function(e){return[...e].map(e=>window.selectorCSS(e))};window.observeDOMChanges=e,window.recordMutations=function(e){const n=[];return window.observeDOMChanges(e,function(e){let r=[],s=[],o=[];e.forEach(e=>e.addedNodes.length&&r.push(...e.addedNodes)||e.removedNodes.length&&o.push(...e.removedNodes)||s.push(e.target)),s.push(...t(o.filter(e=>r.includes(e)))),o=o.filter(e=>e.isConnected&&(e instanceof Element||!s.map(e=>e.textContent).filter(e=>e).some(t=>t===e.textContent))),[r,s,o]=[r,s,o].map(e=>t(e.map(e=>3===e.nodeType&&e.parentNode||e))),n.push(...Array.from(new Set([...r,...s,...o]))),this.disconnect()}),n},window.preparedObjectAlerts=function(e,n){const r=t(e.fields.filter(e=>e.required)),s=e.alertElements.concat(e.styledAlerts).concat(r),o=n.concat(e.globalAlerts),l=t=>!!e.hasOwnProperty(t)&&delete e[t];return l("styledAlerts"),l("styleReference"),e.styledAlertsObserver&&e.styledAlertsObserver.disconnect(),l("styledAlertsObserver"),e.alertElements=[...new Set(s)],e.globalAlerts=[...new Set(o)].filter(t=>!e.alertElements.includes(t)),e}}();
"""

# TODO remove me
submit_obvious_script = """
    !function(){"use strict";window.alert=function(){},window.formObjects.forEach(n=>{const t=n[1].submitBtn;t instanceof Element&&t.click()})}();
"""

# ? how to use smart Promise
form_init_js = """
    var callback = arguments[1];

    window.setTimeout(() => {
        window.browserAssistant = new AlertRegulator(arguments[0]);
        callback(true);
    }, 5000);
"""

form_init_js = """window.browserAssistant = new AlertRegulator(arguments[0]);"""

set_dialog_alert_js = """
    const bodyProps = window.browserAssistant.formObjects.get(document.body);

    bodyProps.alert = arguments[0];
    window.browserAssistant.formObjects.set(document.body, bodyProps);
"""

observe_alerts_js = """window.browserAssistant.setAlertsSentry();"""

complete_alerts_js = """window.browserAssistant.completeAlerts();"""

form_objects_js = """
    return [[...window.browserAssistant.formObjects.keys()], [...window.browserAssistant.formObjects.values()]];
"""

browser_form_data_js = """
    const id = [...window.browserAssistant.formObjects.keys()].indexOf(arguments[0]);
    const dataMap = window.browserAssistant.formData[id];

    return [[...dataMap.keys()], [...dataMap.values()]];
"""

updated_alerts_js = """
    window.browserAssistant.updatePresentAlerts();

    return window.browserAssistant.formAlerts;
"""

# TODO avoid me
set_forms_data_js = """
    window.formObjects = arguments[0].map((form, formID) => [
        form, arguments[1][formID]
    ]);
"""

# ? TODO refactor me: setAlertsSentry; completeAlerts;
prepare_alerts_js = """
    window.formObjects.forEach((formProp) => {
        window.prepareAlerts(formProp[1]);
    });
"""

# TODO avoid me
style_mutation_wait_js = """
    // async
    var callback = arguments[0];

    window.setTimeout(() => {
        callback(true);
    }, 1000);
"""

# TODO avoid me
alerts_wait_js = """
    // async
    var callback = arguments[0];

    window.setTimeout(() => {
        callback(true);
    }, 4000);
"""

set_value_js = """
    arguments[0].value = arguments[1];
    arguments[0].setAttribute('value', arguments[1]);
"""

click_js = """
    arguments[0].click(); arguments[1];
"""

has_focus_js = """
    return document.activeElement === arguments[0];
"""

# TODO refactor me
enter_sent_js = """
    const enteredElements = [];

    window.browserAssistant.formObjects.forEach((obj, elem) => {
        const response = obj.response;
        const entered = response && response.withEnter;
        if (entered) {
            enteredElements.push(elem);
        }
    });

    return enteredElements;
"""

# TODO disable me
field_mutations_init_js = """
    let fieldSequence = arguments[0];
    window.queueNumber = arguments[1];

    if (window.queueNumber == 0) {
        window.fieldMutations = fieldSequence.map(() => null);
        window.fieldStyles = fieldSequence.map(() => null);
        window.mutatedAlerts = [];
    }

    window.fieldMutations[window.queueNumber] = window.recordMutations(document.body);
"""

# TODO disable me
mutated_count_js = """
    const formStyledAlerts = [];

    window.formObjects.forEach((formProp) => {
        const styledAlerts = formProp[1].styledAlerts || [];

        formStyledAlerts.push(...styledAlerts);
        formProp[1].styledAlerts = [];
    });

    window.fieldStyles[window.queueNumber] = formStyledAlerts;

    window.fieldMutations[window.queueNumber] = [
        ...new Set([
            ...window.fieldMutations[window.queueNumber],
            ...window.fieldStyles[window.queueNumber],
        ]),
    ];

    window.fieldMutations[window.queueNumber].forEach((mut) => {
        let countValue = 1;
        let mutatedAlerts = [...window.mutatedAlerts];

        window.mutatedAlerts.forEach((alert, pos) => {
            if (alert[1] == mut) {
                countValue = parseInt(alert[0]) + 1;
                mutatedAlerts.splice(pos, 1);
            }
        });
        mutatedAlerts.push([countValue, mut]);
        window.mutatedAlerts = mutatedAlerts;
    });
"""

# TODO disable me
field_mutations_js = """
    const dropout = (formObj, prop) =>
        formObj.hasOwnProperty(prop) ? delete formObj[prop] : false;
    const globalAlerts = Array.from(
        window.mutatedAlerts.filter((ma) => ma[0] > 1),
        (obj) => obj[1]
    );

    window.formObjects.forEach((formProp) => {
        dropout(formProp[1], `styledAlerts`);
        dropout(formProp[1], `styleRefs`);
        dropout(formProp[1], `styledAlertsObserver`);
    });

    window.fieldMutations.forEach((mut, idx) => {
        const globalMessages = mut instanceof Array ? mut.filter((fm) => globalAlerts.includes(fm)) : [];
        const boundMessages = mut instanceof Array ? mut.filter((fm) => !globalAlerts.includes(fm)) : [];

        window.fieldMutations[idx] = {
            bound: boundMessages,
            global: globalMessages,
        };
    });
"""

edit_fields_js = """
    const fields = window.UIEditElements(arguments[0]).filter(field => field !== arguments[1]);

    return fields;
"""

date_input_js = """
    var wickedInput = arguments[0];

    return (function (corrupted) {
        var date = new Date();

        if (corrupted == true) {
            date.setHours();
            date.setDate();
        }

        return date;
    })(wickedInput);
"""

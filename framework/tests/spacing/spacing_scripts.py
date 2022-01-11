computed_style_observer_script = """
    !function(){"use strict";let e=0,t=new Map;const r=(r,s)=>{let o=t.get(r);return o||(o={styles:{},observers:[]},t.set(r,o)),!o.observers.includes(s)&&(o.observers.push(s),1!==e&&(e=1,n()),!0)},s=(r,s)=>{let o=t.get(r);if(!o)return!1;let l=o.observers.indexOf(s);return-1!==l&&(o.observers.splice(l,1),0===o.observers.length&&t.delete(r),0===t.size&&(e=0),!0)},o=e=>{t.forEach((t,r)=>{t.observers.includes(e)&&s(r,e)})},l=(e,t)=>{let r=getComputedStyle(e),s={};t.observers.forEach(o=>{let l=[];o.properties.forEach(o=>{let n=r[o],i=t.styles[o];n!==i&&i&&l.push(new ComputedStyleObserverEntry(e,o,n,i)),s[o]=n}),l.length&&o.callback(l)}),t.styles=s},n=()=>{1===e&&(requestAnimationFrame(n),t.forEach((e,t)=>{l(t,e)}))};let i=new WeakMap;window.ComputedStyleObserver=class{constructor(e,t=null){Array.isArray(t)&&(t=[...t]),i.set(this,{callback:e,properties:t})}disconnect(){o(i.get(this))}observe(e){return r(e,i.get(this))}unobserve(e){return s(e,i.get(this))}},window.ComputedStyleObserverEntry=class{constructor(e,t,r,s){this.target=e,this.property=t,this.value=r,this.previousValue=s}}}();
"""

execute_on_promise_script = """
    !function(){var timeout=function(callback,stopCondition,callbackValue,ms){setTimeout(promise=>{if(console.log(`${ms}`),window.onPromise=!1,window.maxTries=200,window.tryNum=window.tryNum||1,promise=new Promise((resolve,reject)=>{eval(stopCondition)?(window.onPromise=!0,resolve(window.prom)):reject()}),promise.then(o=>{},o=>{}),!(0==window.onPromise&&window.tryNum<window.maxTries))return window.tryNum=0,callback(eval(callbackValue)),!1;window.tryNum++,timeout(callback,stopCondition,callbackValue,ms)},ms)};window.Timeout=timeout}();
"""

jquery_check_script = """
    !function(){var e=function(){try{return jQuery,!0}catch(e){return!1}};e()||(document.head.appendChild(document.createElement("script")).src="https://code.jquery.com/jquery-3.6.0.min.js");window.withJQuery=e}();
"""

element_collection_script = """
    !function(){"use strict";jQuery.fn.getStyleObject=function(){var e,t=this.get(0),n={};if(window.getComputedStyle){var r=function(e,t){return t.toUpperCase()};e=window.getComputedStyle(t,null);for(var i=0;i<e.length;i++){var o=(a=e[i]).replace(/\-([a-z])/g,r),s=e.getPropertyValue(a);n[o]=s}return n}if(t.currentStyle){for(var a in e=t.currentStyle)n[a]=e[a];return n}return this.css()};window.isVisible=function(e){return void 0!==e.offsetParent?e.offsetWidth>3&&e.offsetHeight>3&&null!==e.offsetParent:e.getBoundingClientRect().width>3&&e.getBoundingClientRect().height>3},window.unwrapSpanText=function(e){return e.getAttribute("message")&&e.getAttribute("message").startsWith("this span")?e.parentElement:e},window.collectText=function(e=!1){var t=function(e){for(var t,n=[],r=document.createTreeWalker(e,NodeFilter.SHOW_ELEMENT,null,!1);t=r.nextNode();)n.push(t);return n}(document.body),n=[];return t=(t=t.filter(e=>!window.prohibited.has(e))).filter(e=>!function(e){var t=e.innerHTML.replace(new RegExp(/[&$][a-z]+;/g),"").trim();return!t||0===t.length||/^\s*$/.test(t)}(e)&&!function(e){var t=e.innerHTML.trim();return new RegExp(/^<[a-z]/g).test(t)&&new RegExp(/<?[a-z0-9]>$/g).test(t)}(e)&&window.isVisible(e)),t=Array.from(t.filter(e=>e instanceof Element),e=>e.childNodes.length?function(e){var t=[],r=[...e.childNodes].filter(e=>e.nodeValue),i=null;for(let e of r)if(e.nodeValue.trim()){i=i||e;var o=document.createElement("span");e.parentNode.insertBefore(o,e),o.appendChild(e),o.setAttribute("message","this span is an element developer used to get accurate values of text rectangle"),t.push(o)}return i?(t.length>1&&(n=[...n,...t]),t[0]):e}(e):e),t=(t=[...t,...n]).filter(e=>!function(e){var t=[...e.children],n="IMG"===e.tagName||t.some(e=>"IMG"===e.tagName),r=!t.some(e=>"SPAN"===e.tagName&&e.getAttribute("message")&&e.getAttribute("message").startsWith("this span"));return n&&r}(e)&&"DIV"!==e.tagName)},window.collectInteractive=function(){var e=[],t=[...document.images,...document.forms,...document.links],n=document.evaluate('//*[self::audio or self::video or self::input or self::button or\n                self::select or self::textarea or self::menu or\n                name()="svg" or self::span or self::iframe]',document,null,XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,null);for(let t=0,r=n.snapshotLength;t<r;++t)e.push(n.snapshotItem(t));return t=[...t,...e].filter(e=>window.isVisible(e))}}();
"""

element_intersection_script = """
    !function(){"use strict";window.intersectionsCollector=class{constructor(t,e){this.targets=t,this.options=e,this.observationData=[],this.encountered=new Set,this.weirdTags=["OPTION"],this.skipWeirdTexts()}respondToVisibility(t,e){var o={root:document.documentElement},i=[],n=this.options;n=n.filter(e=>e!==t&&t!==window.unwrapSpanText(e)&&this.minDistBetween(t,e)<=2*(this.contentBox(t).slice(-1)[0]+this.contentBox(e).slice(-1)[0])),new IntersectionObserver((t,o)=>{t.forEach(t=>{e(t.intersectionRation<.97)})},o).observe(t);for(var r=0;r<n.length;++r){var s={root:null,coll:!1};i[r]=new IntersectionObserver((t,o)=>{t.forEach(t=>{s.root=o.root,s.coll=this.areColliding(o.root,t.target)||t.intersectionRation>.03,e(s)})},{root:n[r]}),i[r].observe(t)}}resetStateCollided(){this.encountered=new Set,this.observationData=[]}contentBox(t){var e,o,i,n=t.getBoundingClientRect(),r=window.getComputedStyle(t),s=["top","left","bottom","right"].map(t=>n[t]),a=[r.paddingTop,r.paddingLeft,r.paddingBottom,r.paddingRight].map(parseFloat),h=[r.marginTop,r.marginLeft,r.marginBottom,r.marginRight].map(parseFloat);a.slice(2).map((t,e)=>{a[e+2]=-a[e+2]}),h.slice(2).map((t,e)=>{h[e+2]=-h[e+2]});var c=h.map((t,e)=>t+a[e]);for(let t of s.map((t,e)=>[t,c[e]]))s.push(t[0]+t[1]);return e=Math.abs(s[7]-s[5]),o=Math.abs(s[6]-s[4]),i=Math.abs((s[3]-s[1])*(s[2]-s[0])),[e,o,...s.slice(4),i]}areColliding(t,e,o=3){let i;var[n,r,s,a,...h]=this.contentBox(t),[c,l,p,d,...h]=this.contentBox(e),m=o/100*Math.abs(Math.min(c,l,n,r));return c-=m,i=!(p+(l-=m)<s||p>s+r-m||d+c<a||d>a+n-m)}minDistBetween(t,e){class o{constructor(t){this.leftX=$(t).offset().left,this.rightX=this.leftX+t.offsetWidth,this.centerX=(this.leftX+this.rightX)/2,this.topY=$(t).offset().top,this.bottomY=this.topY+t.offsetHeight,this.centerY=(this.topY+this.bottomY)/2}static minAbscissa(t,e){var o=[t.centerX-e.centerX,t.leftX-e.centerX,t.rightX-e.centerX,t.centerX-e.leftX,t.leftX-e.leftX,t.rightX-e.leftX,t.centerX-e.rightX,t.leftX-e.rightX,t.rightX-e.rightX];return o.forEach((t,e,o)=>{o[e]=t**2}),Math.min.apply(Math,o)}static minOrdinates(t,e){var o=[t.centerY-e.centerY,t.topY-e.centerY,t.bottomY-e.centerY,t.centerY-e.topY,t.topY-e.topY,t.bottomY-e.topY,t.centerY-e.bottomY,t.topY-e.bottomY,t.bottomY-e.bottomY];return o.forEach((t,e,o)=>{o[e]=t**2}),Math.min.apply(Math,o)}}return t=new o(t),e=new o(e),o.minAbscissa(t,e)+o.minOrdinates(t,e)}skipWeirdTexts(){this.targets=this.targets.filter(t=>!this.weirdTags.includes(t.tagName)),this.options=this.options.filter(t=>!this.weirdTags.includes(t.tagName))}get collection(){return this.targets.forEach(t=>{this.respondToVisibility(t,e=>{e.coll&&!this.encountered.has(e.root)&&(t=window.unwrapSpanText(t),e.root=window.unwrapSpanText(e.root),t===e.root||[t,e.root].some(t=>this.weirdTags.includes(t.tagName))||this.encountered.has(t)||(this.encountered.add(t),this.encountered.add(e.root),this.observationData.push({element:t,error:"TextContentCollision",assoc:e.root})))})}),this.observationData}}}();
"""

spacing_tools_script = """
    !function(){"use strict";window.spacingTestAttributes=["lineHeight","letterSpacing","wordSpacing","marginBottom"],window.auxillaryTestAttributesOK=["blockSize","height","inlineSize","width","marginBlockEnd","perspectiveOrigin","transformOrigin"],window.computedStyleAttributes=Object.keys($(document.body).getStyleObject()).filter(t=>!Array.prototype.concat(spacingTestAttributes,auxillaryTestAttributesOK).includes(t)),window.toggleSpacing=function(){var t,e="WCAG 2.1 1.4.12 bookmarklet";void 0!==window[e]?(document.head.removeChild(window[e].instance),delete window[e]):(t=document.createElement("style"),window[e]={},window[e].instance=t,document.head.appendChild(t),["*{line-height:1.5em!important;}","*{letter-spacing:0.12em!important;}","*{word-spacing:0.16em!important;}","*{margin-bottom:2em!important;}"].forEach(e=>t.sheet.insertRule(e)))}}();
"""

criterion_checker_script = """
    !function(){"use strict";window.criterionChecker=function(e){window.spacingReported=function(e){var n=[];for(let t of e)n.push(t.element);return n}(window.spacingRulesCounts);for(let n of e)window.spacingReported.includes(n)||window.nastyTextNodes.push({element:n,error:"RulesNotApplied"});for(let e of window.spacingRulesCounts)e.count!==spacingTestAttributes.length&&window.nastyTextNodes.push({element:e.element,error:"SomeRulesNotApplied"});for(let e of window.junkRulesCounts)window.nastyTextNodes.push({element:e.element,error:"OtherStyleChanges"});window.criterionChecker.finish=!0}}();
"""

main_js = """
    window.prohibited = new Set();
    window.spacingRulesCounts = [];
    window.junkRulesCounts = [];
    window.nastyTextNodes = [];
    window.textNodes = window.collectText();
    window.textNodes.forEach((text) => { window.prohibited.add(text); });
    window.collectInteractive().forEach((elem) => { window.prohibited.add(elem); });
    window.prohibited = [...window.prohibited];

    window.successObserver = new ComputedStyleObserver((styles) => {
        var element = styles[0].target;
        window.spacingRulesCounts.push({element: element, count: styles.length});
    }, spacingTestAttributes);
    window.junkyChangeObserver = new ComputedStyleObserver((styles) => {
        var element = styles[0].target;
        window.junkRulesCounts.push({element: element, count: styles.length});
        }, computedStyleAttributes);

    window.unwrappedTextNodes = window.textNodes;
    window.unwrappedTextNodes.forEach((node, pos) => {
        window.unwrappedTextNodes[pos] = window.unwrapSpanText(node);
    });
    window.unwrappedTextNodes = [...new Set(window.unwrappedTextNodes)];

    window.unwrappedTextNodes.forEach((node) => {
        window.successObserver.observe(node);
        window.junkyChangeObserver.observe(node)
    });
    **************************************************************
    window.collector = new window.intersectionsCollector(window.prohibited, window.prohibited);
    window.collidedTextNodes = window.collector.collection
    **************************************************************
    window.toggleSpacing();
    **************************************************************
    window.criterionChecker(window.textNodes);
    **************************************************************
    window.collector.resetStateCollided();
    window.interimCollisions = {elements: [], associates: []};
    window.interimCollisions.elements = Array.from(window.collidedTextNodes, coll => coll.element);
    window.interimCollisions.associates = Array.from(window.collidedTextNodes, coll => coll.assoc);
    window.collidedTextNodes = window.collector.collection;
    **************************************************************
    window.collidedTextNodes = window.collidedTextNodes.filter(coll => !(
        window.interimCollisions.elements.includes(coll.element) &&
        window.interimCollisions.associates.includes(coll.assoc))
    );
    window.interimCollisions.elements = Array.from(window.collidedTextNodes, coll => coll.element);
    window.interimCollisions.elements.push(...Array.from(window.collidedTextNodes, coll => coll.assoc));
    window.interimCollisions.elements.forEach((coll, idx, arr) => { arr[idx] =
        {element: coll, error: "TextContentCollision"} });
    window.collidedTextNodes = window.interimCollisions.elements.filter(node =>
        window.textNodes.includes(node.element));
    window.nastyTextNodes.push(...window.collidedTextNodes);
    window.nastyTextNodes = window.nastyTextNodes.filter(elem => elem.element instanceof Element);
    window.junkyChangeObserver.disconnect();
    window.successObserver.disconnect();
    window.toggleSpacing();
"""

script_onID_creator = """
    var script = arguments[0];
    var id = arguments[1];
    var customScriptID = document.head.appendChild(document.createElement('script'));
    var encodedID;

    String.prototype.hexEncode = function() {
        var hex, i;

        var result = "";
        for (i=0; i<this.length; i++) {
            hex = this.charCodeAt(i).toString(16);
            result += ("000"+hex).slice(-4);
        }

        return result;
    };

    function randomId(arrInt) {
        const uint32 = window.crypto.getRandomValues(new Uint32Array(arrInt))[0];
        return uint32.toString(16);
    }

    encodedID = ("" + id.hexEncode()).split("");
    encodedID.forEach((n, i, arr) => { arr[i] = parseInt(n); });
    encodedID = randomId(encodedID);
    customScriptID.setAttribute("id", encodedID);
    customScriptID.innerText = `${arguments[0]}`;

    return encodedID;
"""


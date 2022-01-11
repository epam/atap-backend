execute_on_promise_script = """
    !function(){var timeout=function(callback,stopCondition,callbackValue,ms){setTimeout(promise=>{if(console.log(`${ms}`),window.onPromise=!1,window.maxTries=200,window.tryNum=window.tryNum||1,promise=new Promise((resolve,reject)=>{eval(stopCondition)?(window.onPromise=!0,resolve(window.prom)):reject()}),promise.then(o=>{},o=>{}),!(0==window.onPromise&&window.tryNum<window.maxTries))return window.tryNum=0,callback(eval(callbackValue)),!1;window.tryNum++,timeout(callback,stopCondition,callbackValue,ms)},ms)};window.Timeout=timeout}();
"""

content_preselection_script = """
    !function(){"use strict";class t{constructor(t){this.node=t,this.rect=t.getBoundingClientRect(),this.style=window.getComputedStyle(t),this.color=this.style.getPropertyValue("color"),this.visible=!1,this.disclosed=!1,this.reason=[]}static get invisibleCSSpoints(){return Object({display:"none",visibility:"hidden","font-size":"3",opacity:"0.1",height:"3",width:"3","max-height":"3","max-width":"3"})}static get disclosedCSSpoints(){return Object({display:"block",visibility:"visible","font-size":"20",opacity:"1",position:"relative",height:"auto",width:"auto","max-height":"none","max-width":"none"})}get contrastColorOptions(){return Object({"background-color":this.style.getPropertyValue("background-color"),fill:this.style.getPropertyValue("fill"),"border-color":this.style.getPropertyValue("border-color"),"outline-color":this.style.getPropertyValue("outline-color"),"box-shadow":this.style.getPropertyValue("box-shadow").split(")")[0]+")","column-rule-color":this.style.getPropertyValue("column-rule-color"),"text-decoration-color":this.style.getPropertyValue("text-decoration-color")})}colorToRGBToHex(t,e="rgb"){let o=t.indexOf(",")>-1?",":" ";const n=t.substr(4).split(")")[0].split(o).map(t=>parseInt(t)).filter(Number.isInteger);if("hex"===e){let t=(+n[0]).toString(16),e=(+n[1]).toString(16),o=(+n[2]).toString(16);return 1==t.length&&(t="0"+t),1==e.length&&(e="0"+e),1==o.length&&(o="0"+o),"#"+t+e+o}return n}rgb2lab(t){let e,o,n,i=t[0]/255,s=t[1]/255,r=t[2]/255;return o=(.2126*(i=i>.04045?Math.pow((i+.055)/1.055,2.4):i/12.92)+.7152*(s=s>.04045?Math.pow((s+.055)/1.055,2.4):s/12.92)+.0722*(r=r>.04045?Math.pow((r+.055)/1.055,2.4):r/12.92))/1,n=(.0193*i+.1192*s+.9505*r)/1.08883,e=(e=(.4124*i+.3576*s+.1805*r)/.95047)>.008856?Math.pow(e,1/3):7.787*e+16/116,[116*(o=o>.008856?Math.pow(o,1/3):7.787*o+16/116)-16,500*(e-o),200*(o-(n=n>.008856?Math.pow(n,1/3):7.787*n+16/116))]}deltaE(t,e){let o=this.rgb2lab(t),n=this.rgb2lab(e),i=o[0]-n[0],s=o[1]-n[1],r=o[2]-n[2],l=Math.sqrt(o[1]*o[1]+o[2]*o[2]),a=l-Math.sqrt(n[1]*n[1]+n[2]*n[2]),c=s*s+r*r-a*a,d=i/1,h=a/(1+.045*l),u=(c=c<0?0:Math.sqrt(c))/(1+.015*l),p=d*d+h*h+u*u;return p<0?0:Math.sqrt(p)}checkVisible(){const t=void 0!==this.node.offsetParent&&"BODY"!==this.node.tagName&&this.node.offsetWidth>3&&this.node.offsetHeight>3&&null!==this.node.offsetParent,e=window.textNodes.includes(this.node)&&this.deltaE(this.colorToRGBToHex(this.color),this.colorToRGBToHex(window.getComputedStyle(document.body).getPropertyValue("background-color")))>5||Array.from(Object.values(this.contrastColorOptions),t=>this.deltaE(this.colorToRGBToHex(this.color),this.colorToRGBToHex(t))).some(t=>t>5);if(t||this.reason.push(["not physical",!0]),e||this.reason.push(["not color resolvable",!0]),this.visible=t&&e,this.visible){for(let t of Object.keys(this.constructor.invisibleCSSpoints)){(parseInt(this.style.getPropertyValue(t))?parseInt(this.style.getPropertyValue(t))<=this.constructor.invisibleCSSpoints[t]:this.style.getPropertyValue(t)==this.constructor.invisibleCSSpoints[t])&&this.reason.push([t,this.style.getPropertyValue(t)])}this.visible=!this.reason.length}}discloseHidden(){for(let t of Object.keys(this.constructor.disclosedCSSpoints))this.node.style.border="3px solid red",this.node.style.boxShadow="red 0 0 3px 3px",this.node.style.setProperty("min-height","20px"),this.node.style.setProperty("min-width","20px"),this.node.style.setProperty("color","black"),this.node.style.setProperty("background-color","white"),this.node.style.setProperty(t,this.constructor.disclosedCSSpoints[t]);this.disclosed=!0}static checkVisibleTree(e,o=new Set,n=!1){const i=[];for(let s of e.children){const e=new t(s);n&&e.discloseHidden(),e.checkVisible(),e.visible?(i.push(s),o.add(s)):e.reason.length-1||"not color resolvable"!==e.reason[0][0]||i.push(s)}for(let t of i)this.checkVisibleTree(t,o,n);return[...o]}}window.VisualDiscloser=t,window.hasOneInside=function(t,e,o=!1){const n=[...t.querySelectorAll("*")],i=o?window.contentNotToCross.decorative:new Set;let s=n.filter(t=>e.has(t)&&!(t.getAttribute("message")&&t.getAttribute("message").startsWith("this span is for dev")));return s=0!==s.length&&(1===s.length||s.every(t=>1===[...t.parentElement.children].filter(t=>!i.has(t)).length)),!(!n.length||!s)},window.rollbackSpanTexts=function(){[...document.getElementsByTagName("SPAN")].filter(t=>t.getAttribute("message")&&t.getAttribute("message").startsWith("this span is for dev")).forEach(t=>{t.replaceWith(t.textContent)})},window.collectText=function(t=document.body,e=!1){let o=function(t){let e;const o=[],n=document.createTreeWalker(t,NodeFilter.SHOW_ELEMENT,null,!1);for(;e=n.nextNode();)s(e)&&o.push(e);return o}(t);const n=o.length;function i(t){return t.replace(/[&$][a-z]+;/gi,"").replace(/<iframe.+<\/iframe>/gis,"").replace(/<script.+<\/script>/gis,"").trim()}function s(t){let e=t.innerHTML;return e=(e=i(e)).replace(/(<([^>]+)>)/gi,"").replace(/.+>$/gi,""),/.+/.test(e.trim())}return(o=1==e&&s(t)?o.concat([t]):o).forEach(t=>{const e=function(t){let e;const o=[],n=[...t.childNodes].filter(t=>t.nodeType===Node.TEXT_NODE&&i(t.textContent));let s;if(!n.length)return null;for(const t of n)(s=t.parentElement.getAttribute("message"))&&s.startsWith("this span is for dev")?o.push(t.parentElement):(e=document.createElement("span"),t.parentNode.insertBefore(e,t),e.appendChild(t),e.setAttribute("message","this span is for dev to wrap the text node"),o.push(e));return o}(t);e&&o.push(...e)}),o=o.slice(n)},window.PIPCollector=function(){let t=[...document.body.getElementsByTagName("*")];return t=t.filter(t=>(function(t){const e=window.getComputedStyle(t),o=window.getComputedStyle(t.parentElement);if("BODY"===t.tagName)return!1;function n(t,e){let o=0;return e.forEach(e=>{o+=t.includes(e)}),1===o}const i=Object.values(o).filter(function(t){return n(t,Array("color","content","appearance","opacity","animation"))}).filter(t=>!n(t,["background","border","size","caret","scroll"]));for(const n of i)if(e[n]&&o[n]!==e[n]){if(n.includes("color")&&("BODY"===t.parentElement.tagName||"rgb(255, 255, 255) rgb(0, 0, 0)".includes(e[n])&&"rgb(255, 255, 255) rgb(0, 0, 0)".includes(o[n])))continue;if("justify-content"===n&&["DIV","ARTICLE","NAV","SECTION","ASIDE","HEADER","FOOTER"].includes(t.tagName))continue;return!0}return!1})(t)),(t=new Set(t)).forEach(e=>{window.hasOneInside(e,new Set([...window.contentNotToCross.functional,...window.contentNotToCross.decorative]))&&t.delete(e),e.children.length&&[...e.children].every(t=>t.getAttribute("message")&&t.getAttribute("message").startsWith("this span"))&&t.delete(e)}),[...t]},window.collectInteractive=function(){const t={critical:[],optional:[]},e=[...document.images,...document.links],o=document.evaluate("//*[self::audio or self::video or self::input or self::button or\n                    self::select or self::textarea or self::menu or self::iframe]",document,null,XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,null),n=document.evaluate('//*[name()="svg" or self::span]',document,null,XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,null);for(let e=0,n=o.snapshotLength;e<n;++e)t.critical.push(o.snapshotItem(e));for(let e=0,o=n.snapshotLength;e<o;++e)t.optional.push(n.snapshotItem(e));return t.critical=[...e,...t.critical].filter(t=>!window.hasOneInside(t,window.contentNotToCross.functional)),t.optional=t.optional.filter(e=>!t.critical.some(t=>e===t)&&!window.hasOneInside(e,window.contentNotToCross.decorative)),t},window.animatedNodes=new Set,window.collectAnimated=function(t){const e=new Set;let o=[];[...document.body.getElementsByTagName("*")].forEach(t=>{o.push(t.getAnimations({subtree:!0}))}),o=Array.from(o.filter(t=>t.length),t=>new Set(Array.from(t,t=>t.effect.target)));for(const t of o)for(const o of t)e.add(o);return e.forEach(e=>{t.add(e)}),e.size},window.runEvery=function(t,e,o,n=12e4){let i=0;window.animationsEnded=!1,window.animationsTimeout=setTimeout(()=>{console.log("timeout"),window.animationsEnded=!0,clearInterval(window.intervalRunner)},n),window.intervalRunner=setInterval(()=>{const o=t.apply(t,e);console.log("collectedNew",o),console.log("collected",i),o===i&&(clearInterval(window.intervalRunner),window.animationsEnded=!0,console.log("awesome!")),i=o>i?o:i},o)}}();
"""

collisions_runaways_script = """
    !function(){"use strict";const t={SPAN:.3,P:.25,H1:.25,H2:.25,H3:.25,H4:.3,H5:.3,H6:.3,CODE:.3,PRE:.3,MARK:.3,INS:.3,DEL:.3,SUP:.4,SUB:.4,SMALL:.4,I:.3,B:.3,A:.2};var e=function(e){const o=t[e.tagName]||0,i=e.getBoundingClientRect(),n=window.getComputedStyle(e),s=["top","left","bottom","right"].map(t=>i[t]),r=[n.paddingTop,n.paddingLeft,n.paddingBottom,n.paddingRight].map(parseFloat);let a,h,c=[n.marginTop,n.marginLeft,n.marginBottom,n.marginRight].map(parseFloat);r.slice(2).map((t,e)=>{r[e+2]=-r[e+2]}),c.slice(2).map((t,e)=>{c[e+2]=-c[e+2]}),c=c.map((t,e)=>t+r[e]);for(const t of s.map((t,e)=>[t,c[e]]))s.push(t[0]+t[1]);return[a=(s[7]-s[5])*(1-o),h=(s[6]-s[4])*(1-o),...s.slice(4)]};window.hideFixed=function(){[...document.body.getElementsByTagName("*")].filter(t=>["fixed","sticky"].includes(window.getComputedStyle(t).position)).forEach(t=>t.style.display="none")},window.contentify=e,window.areaContains=function(t,e){const o=t.getBoundingClientRect(),i=e.getBoundingClientRect();return o.top<=i.top+1&&o.left<=i.left+1&&o.bottom>=i.bottom-1&&o.right>=i.right-1},window.unwrapSpanText=function(t){return t.getAttribute("message")&&t.getAttribute("message").startsWith("this span is for dev")?t.parentElement:t},window.RunawaysObserver=class{constructor(t){this.targets=t,this.zoomValue=100,this.options={root:document.documentElement},this.rootObserver=null,this.viewport={width:1/0,height:1/0},this.escapedData=[],this.extinctedData=[]}recordDims(){let t;const e={width:null,height:null};if("100"==this.zoomValue){const[o,i]=function(){const t=[...document.body.getElementsByTagName("*")];let{bottom:e,right:o}=document.documentElement.getBoundingClientRect();for(const i of t){const t=i.getBoundingClientRect(),[n,s]=[t.bottom,t.right];e=n>e?n:e,o=o>s?o:s}return[e,o]}();e.width=Math.max(window.screen.width,i,this.options.root.scrollWidth),e.height=Math.max(window.screen.height,o,this.options.root.scrollHeight),console.log("rootDimensions",e),t=e.height>window.screen.height?e.width<=window.screen.width?"width":e.width-window.screen.width<e.height-window.screen.height?"width":"height":e.width>window.screen.width?"height":"width-height"}else t=Object.keys(this.viewport).filter(t=>Number.isFinite(this.viewport[t])).join("-");t.split("-").forEach(t=>{this.viewport[t]=window.screen[t]/this.zoomValue*100}),console.log("viewport",this.viewport)}ViewportIntersectionRatio(t){const[o,i,n,s,r,a]=e(t),h={width:1,height:1};var c=function(t){const e="width"===t?o:i,[h,c]="width"===t?[s,a]:[n,r],l=t=>t<0?0:t;return l(1-(l((e=>e-this.viewport[t])(c))+l((t=>0-t)(h)))/e)}.bind(this);return Object.keys(this.viewport).filter(t=>Number.isFinite(this.viewport[t])).forEach(t=>{h[t]=c(t)}),Math.min(...Object.values(h))}respondToVisibility(t,e){this.rootObserver=new IntersectionObserver((t,o)=>{t.forEach(t=>{o.unobserve(t.target),e(this.ViewportIntersectionRatio(t.target))})},this.options),this.rootObserver.observe(t)}get collection(){return this.escapedData=[],this.extinctedData=[],this.targets.forEach(t=>{this.respondToVisibility(t,e=>{e<.95&&(e>.03?this.escapedData.push({element:window.unwrapSpanText(t),problem:`This element crossed screen area on ${this.zoomValue}% zoom.`}):this.extinctedData.push({element:window.unwrapSpanText(t),problem:`This element vanished at ${this.zoomValue}% zoom and has no content alternative.`}))})}),{escaped:this.escapedData,extincted:this.extinctedData}}},window.collectCollisions=function(t,e){let o,i;class n{constructor(t){this.top=t.offsetTop,this.left=t.offsetLeft,this.leftX=t.getBoundingClientRect().left+window.scrollX,this.rightX=this.leftX+t.offsetWidth,this.centerX=(this.leftX+this.rightX)/2,this.topY=t.getBoundingClientRect().top+window.scrollY,this.bottomY=this.topY+t.offsetHeight,this.centerY=(this.topY+this.bottomY)/2}static fourSideDirection(t,e){let o=Math.abs(t.top-e.top)>Math.abs(t.left-e.left)?-2:-1;return o=-2===o?o*Math.sign(t.top-e.top)+2:o*Math.sign(t.left-e.left)+2,new Object({0:"top",1:"left",4:"bottom",3:"right"})[o]}static minAbscissa(t,e){const o=[t.centerX-e.centerX,t.leftX-e.centerX,t.rightX-e.centerX,t.centerX-e.leftX,t.leftX-e.leftX,t.rightX-e.leftX,t.centerX-e.rightX,t.leftX-e.rightX,t.rightX-e.rightX];return o.forEach((t,e,o)=>{o[e]=t**2}),Math.min.apply(Math,o)}static minOrdinates(t,e){const o=[t.centerY-e.centerY,t.topY-e.centerY,t.bottomY-e.centerY,t.centerY-e.topY,t.topY-e.topY,t.bottomY-e.topY,t.centerY-e.bottomY,t.topY-e.bottomY,t.bottomY-e.bottomY];return o.forEach((t,e,o)=>{o[e]=t**2}),Math.min.apply(Math,o)}}function s(o,i,n){let s,a=new Set;const[h,c,l,d]=window.contentify(i);let w,u=o.parentElement?Array.from([...o.parentElement.querySelectorAll("*")]):[];return window.textNodes.includes(i)&&!["fixed","sticky","absolute"].includes(window.getComputedStyle(i).getPropertyValue("position"))?[]:((u=function(t,e,o=1/0){let i,n=[];return e.forEach(e=>{i=r(t,e),n.push({node:e,dist:i})}),n.sort((t,e)=>t.dist<e.dist?-1:t.dist>=e.dist?1:void 0),n=Array.from(n,t=>t.node).filter(function(t,e){return(i=this[e])<=o},Array.from(n,t=>t.dist))}(o,u=u.filter(t=>n.some(e=>t===e)),w=Math.max(o.offsetHeight,o.offsetWidth)+Math.max.apply(Math,Array.from(u,t=>Math.max(t.offsetHeight,t.offsetWidth)).filter(t=>t))**2)).forEach(o=>{if(o===i)return;let[n,r,w,u]=window.contentify(o);const f=e/100*Math.min(n,r,h,c)*(t/100);n-=f,r-=f,(s=!(window.textNodes.includes(o)&&!["fixed","sticky","absolute"].includes(window.getComputedStyle(o).getPropertyValue("position"))||w+r<l||w>l+c-f||u+n<d||u>d+h-f))&&a.add(o)}),[...a])}var r=function(t,e){return t=new n(t),e=new n(e),n.minAbscissa(t,e)+n.minOrdinates(t,e)};function a(t){const e=[];let o=function(t,e){const o=[];return function i(n,s){return n.length===e?(o.push(n),!1):!(s+1>t.length)&&(i(n.concat(t[s]),s+1),void i(n,s+1))}([],0),o}(t,2);return(o=o.filter(t=>2*r(t[0],t[1])<=(Math.max(t[0].offsetWidth,t[0].offsetHeight)+Math.max(t[1].offsetWidth,t[1].offsetHeight))**2)).forEach(i=>{let n;const r=s(i[0],i[1],t),a=s(i[1],i[0],t);r.forEach(t=>{n=!!window.areaContains(t,i[1])||window.areaContains(i[1],t),[t,i[1]]=[t,i[1]].map(t=>window.unwrapSpanText(t)),t===i[1]||n||(console.log("push",t,i[1]),e.push([t,i[1]]))}),o=o.filter(t=>!r.includes(t[0])),a.forEach(t=>{n=!!window.areaContains(i[0],t)||window.areaContains(t,i[0]),[t,i[0]]=[t,i[0]].map(t=>window.unwrapSpanText(t)),t===i[0]||n||(console.log("rpush",t,i[0]),e.push([i[0],t]))}),o=o.filter(t=>!r.includes(t[1]))},o),e}function h(e){let{lefts:o,rights:i,collisionsResult:n}={lefts:[],rights:[],collisionsResult:[]};for(const s of e)o.includes(s[0])&&i.includes(s[1])||o.includes(s[1])&&i.includes(s[0])||n.push({elements:s,problem:`Collision between these elements detected on ${t}% zoom.`}),o.push(s[0]),i.push(s[1]);return n}return[o,i]=[h(a(window.scaleFollowedContent[window.zoom].functional.concat(window.scaleFollowedContent[100].functional))),h(a(window.scaleFollowedContent[window.zoom].decorative.concat(window.scaleFollowedContent[100].decorative)))],{functional:o,decorative:i}}}();
"""

element_sensible_attributes_script = """
    !function(){"use strict";window.sensibleAttrs=function(t){var e={};let r=[];for(let e in t)r.push(e);for(let r=0;r<t.attributes.length;++r)e[t.attributes[r].name]=t.attributes[r].value;return e=Object.keys(e).filter(t=>!r.includes(t)).reduce((t,r)=>(t[r]=e[r],t),{}),Object.values(e)}}();
"""

# window.zoomList = ['100', '200', '400'];
preselection_js = """
    window.runEvery(window.collectAnimated, [window.animatedNodes, ], 3000);
    window.scrollTo(document.body.scrollWidth, 0);
    window.scrollTo(0, document.body.scrollHeight);
    **************************************************************
    window.scaleFollowedContent = Object.fromEntries(
        window.zoomList.map((zoom) => [zoom, { functional: [], decorative: [] }])
    );
    window.contentNotToCross = {functional: new Set(), decorative: new Set()};
    window.animatedNodes.forEach((anim) => { window.contentNotToCross.functional.add(anim); });
    **************************************************************
    window.collisionsResult = [];
    window.escapesResult = [];
    window.extinctionsResult = [];
    window.warningsResult = {collisions: [], escapes: [], extinctions: []};
"""

# window.zoom = '100';
content_recording_js = """
    window.textNodes = window.collectText();
    window.textNodes.forEach((text) => { window.contentNotToCross.functional.add(text); });
    **************************************************************
    window.interactiveContent = window.collectInteractive();
    window.interactiveContent.critical.forEach((content) => {
        window.contentNotToCross.functional.add(content);
    });
    window.interactiveContent.optional.forEach((content) => {
        window.contentNotToCross.decorative.add(content);
    });
    **************************************************************
    window.visibleElements = window.VisualDiscloser.checkVisibleTree(document.body);

    window.contentNotToCross.functional = new Set(
        window.visibleElements.filter((vis) =>
            window.contentNotToCross.functional.has(vis)
        )
    );
    window.contentNotToCross.decorative = new Set(
        window.visibleElements.filter((vis) =>
            window.contentNotToCross.decorative.has(vis)
        )
    );
    **************************************************************
    window.stylesProhibited = window.PIPCollector();
    window.stylesProhibited.forEach((elem) => { window.contentNotToCross.decorative.add(elem); });

    window.contentNotToCross.functional = [
        ...window.contentNotToCross.functional,
    ].filter(
        (inst) => !window.hasOneInside(inst, window.contentNotToCross.functional, true)
    );
    window.contentNotToCross.decorative = [
        ...window.contentNotToCross.decorative,
    ].filter(
        (inst) => !window.hasOneInside(inst, window.contentNotToCross.decorative)
    );

    window.contentNotToCross.decorative = window.contentNotToCross.decorative.filter(
        (decor) =>
            !window.contentNotToCross.functional.some((func) =>
                [...decor.querySelectorAll('*')].concat(decor).includes(func)
            )
    );
    **************************************************************
    if (window.zoom === '100') {
        window.scaleFollowedContent[window.zoom].functional = window.contentNotToCross.functional;
        window.scaleFollowedContent[window.zoom].decorative = window.contentNotToCross.decorative;
    }
    else {
        window.scaleFollowedContent[window.zoom].functional = window.contentNotToCross.functional.filter(
            (content) => !window.scaleFollowedContent[100].functional.includes(content)
        );
        window.scaleFollowedContent[window.zoom].decorative = window.contentNotToCross.decorative.filter(
            (content) => !window.scaleFollowedContent[100].decorative.includes(content)
        );
    }

    window.contentNotToCross.functional = new Set(window.contentNotToCross.functional);
    window.contentNotToCross.decorative = new Set(window.contentNotToCross.decorative);
"""

content_violations_js = """
    window.scrollTo(document.body.scrollWidth, 0);
    window.scrollTo(0, document.body.scrollHeight);
    **************************************************************
    window.collisionsCollected = false;
    window.collisionsResultFoot = window.collectCollisions(window.zoom, 0);  // 15
    window.collisionsCollected = true;
    **************************************************************
    window.scrollTo(0, 0);
    **************************************************************
    window.collisionsCollected = false;
    window.collisionsResultHead = window.collectCollisions(window.zoom, 0);  // 15
    window.collisionsCollected = true;
    **************************************************************
    window.collisionsCollected = false;
    window.collisionsResult.push(...window.collisionsResultHead.functional.filter(
        collPair => window.collisionsResultFoot.functional.some(pair =>
            pair.elements[0] === collPair.elements[0] && pair.elements[1] === collPair.elements[1])));
    window.warningsResult.collisions.push(...window.collisionsResultHead.decorative.filter(
        collPair => window.collisionsResultFoot.decorative.some(pair =>
            pair.elements[0] === collPair.elements[0] && pair.elements[1] === collPair.elements[1])));
    window.collisionsCollected = true;
    **************************************************************
    window.runawaysOfZoomPicker = window.runawaysOfZoomPicker ||
        new window.RunawaysObserver(targets=[]);
    window.runawaysOfZoomPickerDecorative = window.runawaysOfZoomPickerDecorative ||
        new window.RunawaysObserver(targets=[]);
    **************************************************************
    window.runawaysOfZoomPicker.zoomValue = window.zoom;
    window.runawaysOfZoomPickerDecorative.zoomValue = window.zoom;
    window.runawaysOfZoomPicker.recordDims();
    window.runawaysOfZoomPickerDecorative.recordDims();
    window.runawaysOfZoomPicker.targets.push(...window.scaleFollowedContent[window.zoom].functional);
    window.runawaysOfZoomPickerDecorative.targets.push(...window.scaleFollowedContent[window.zoom].decorative);
    **************************************************************
    window.runaways = window.runawaysOfZoomPicker.collection;
    window.warningRunaways = window.runawaysOfZoomPickerDecorative.collection;
    **************************************************************
    window.escapesResult.push(...window.runaways.escaped);
    window.extinctionsResult.push(...window.runaways.extincted);

    window.warningsResult.escapes.push(...window.warningRunaways.escaped);
    window.warningsResult.extinctions.push(...window.warningRunaways.extincted);
"""

cleanup_js = """
    window.collisionsResult = [...new Set(window.collisionsResult)];
    window.escapesResult = [...new Set(window.escapesResult)];
    window.extinctionsResult = [...new Set(window.extinctionsResult)];
    Object.keys(window.warningsResult).forEach((res) => {
        window.warningsResult[res] = [...new Set(window.warningsResult[res])];
    });

    window.rollbackSpanTexts();
"""

warning_escapes_js = """
    window.warningsEncountered = 0;
    arguments[0].forEach((data) => {
        data.element.style.boxShadow = '0 0 0 3px rgba(255,0,0,1.0)';
        data.element.style.border = 'solid red 3px';
        window.warningsEncountered += 1;
    });
"""

warning_extinctions_js = """
    arguments[0].forEach((data) => {
        data.element.style.boxShadow = '0 0 0 3px rgba(255,0,0,1.0)';
        data.element.style.border = 'solid red 3px';
        window.warningsEncountered += 1;
    });
"""

warning_collisions_js = """
    arguments[0].forEach((data) => {
        data.elements[0].style.boxShadow = '0 0 0 3px rgba(255,0,0,1.0)';
        data.elements[1].style.boxShadow = '0 0 0 3px rgba(255,0,0,1.0)';
        data.elements[0].style.border = 'solid red 3px';
        data.elements[1].style.border = 'solid red 3px';

        window.warningsEncountered += 1;
    });
"""

heights_script = """
    var heights = [];

    for (let i=0; i < arguments.length; i++) {
        heights.push(arguments[i].offsetHeight);
    }

    return heights;
"""

boundaries_script = """
    var nodes = arguments[0];
    var boundaries = [];

    for (let i=0; i < nodes.length; i++) {
        let cont = nodes[i];
        let rect = cont.getBoundingClientRect();
        boundaries.push(Math.floor(rect.x) + ' ' + Math.floor((rect.x + rect.width)));
    }

    return boundaries
"""

scroll_script = """
    let scroll = window.scrollMaxX;
    const toBool = (value) => value ? true : false;

    scroll = scroll || Math.max(document.documentElement.getBoundingClientRect().width,
    document.documentElement.scrollWidth, document.documentElement.offsetWidth) > arguments[0];

    return toBool(scroll);
"""

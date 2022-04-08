visual_discloser_tool_script = """
    (function () {
        'use strict';

        class VisualDiscloser {
            /* Doesn't account absolute position outside of reachable page */
            constructor(node) {
                this.node = node;
                this.rect = node.getBoundingClientRect();
                this.style = window.getComputedStyle(node);
                this.color = this.style.getPropertyValue('color');
                this.visible = false;
                this.disclosed = false;
                this.reason = [];
            }

            static get invisibleCSSpoints() {
                return Object({
                    display: 'none',
                    visibility: 'hidden',
                    'font-size': '3',
                    opacity: '0.1',
                    height: '3',
                    width: '3',
                    'max-height': '3',
                    'max-width': '3',
                });
            }

            static get disclosedCSSpoints() {
                return Object({
                    display: 'block',
                    visibility: 'visible',
                    'font-size': '20',
                    opacity: '1',
                    position: 'relative',
                    height: 'auto',
                    width: 'auto',
                    'max-height': 'none',
                    'max-width': 'none',
                });
            }

            get contrastColorOptions() {
                return Object({
                    'background-color':
                        this.style.getPropertyValue('background-color'),
                    fill: this.style.getPropertyValue('fill'),
                    'border-color': this.style.getPropertyValue('border-color'),
                    'outline-color': this.style.getPropertyValue('outline-color'),
                    'box-shadow':
                        this.style.getPropertyValue('box-shadow').split(')')[0] +
                        ')',
                    'column-rule-color':
                        this.style.getPropertyValue('column-rule-color'),
                    'text-decoration-color': this.style.getPropertyValue(
                        'text-decoration-color'
                    ),
                });
            }

            colorToRGBToHex(prop, format = 'rgb') {
                const sep = prop.indexOf(',') > -1 ? ',' : ' ';
                let rgb = prop
                    .replace(/[^\(\)]+/, '')
                    .slice(1, -1)
                    .split(sep)
                    .map((val) => parseFloat(val));

                const transparencyValue = (rgb.length === 4 && 1 - rgb[3]) || 0;

                rgb = [rgb[0], rgb[1], rgb[2]].map((channel) =>
                    Math.min(parseInt(channel + transparencyValue * 255), 255)
                );

                if (format === 'hex') {
                    let r = (+rgb[0]).toString(16),
                        g = (+rgb[1]).toString(16),
                        b = (+rgb[2]).toString(16);

                    if (r.length == 1) r = '0' + r;
                    if (g.length == 1) g = '0' + g;
                    if (b.length == 1) b = '0' + b;

                    return '#' + r + g + b;
                }

                return rgb;
            }

            rgb2lab(rgb) {
                let r = rgb[0] / 255,
                    g = rgb[1] / 255,
                    b = rgb[2] / 255,
                    x,
                    y,
                    z;
                r = r > 0.04045 ? Math.pow((r + 0.055) / 1.055, 2.4) : r / 12.92;
                g = g > 0.04045 ? Math.pow((g + 0.055) / 1.055, 2.4) : g / 12.92;
                b = b > 0.04045 ? Math.pow((b + 0.055) / 1.055, 2.4) : b / 12.92;
                x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047;
                y = (r * 0.2126 + g * 0.7152 + b * 0.0722) / 1.0;
                z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883;
                x = x > 0.008856 ? Math.pow(x, 1 / 3) : 7.787 * x + 16 / 116;
                y = y > 0.008856 ? Math.pow(y, 1 / 3) : 7.787 * y + 16 / 116;
                z = z > 0.008856 ? Math.pow(z, 1 / 3) : 7.787 * z + 16 / 116;
                return [116 * y - 16, 500 * (x - y), 200 * (y - z)];
            }

            deltaE(rgbA, rgbB) {
                let labA = this.rgb2lab(rgbA);
                let labB = this.rgb2lab(rgbB);
                let deltaL = labA[0] - labB[0];
                let deltaA = labA[1] - labB[1];
                let deltaB = labA[2] - labB[2];
                let c1 = Math.sqrt(labA[1] * labA[1] + labA[2] * labA[2]);
                let c2 = Math.sqrt(labB[1] * labB[1] + labB[2] * labB[2]);
                let deltaC = c1 - c2;
                let deltaH = deltaA * deltaA + deltaB * deltaB - deltaC * deltaC;
                deltaH = deltaH < 0 ? 0 : Math.sqrt(deltaH);
                let sc = 1.0 + 0.045 * c1;
                let sh = 1.0 + 0.015 * c1;
                let deltaLKlsl = deltaL / 1.0;
                let deltaCkcsc = deltaC / sc;
                let deltaHkhsh = deltaH / sh;
                let i =
                    deltaLKlsl * deltaLKlsl +
                    deltaCkcsc * deltaCkcsc +
                    deltaHkhsh * deltaHkhsh;
                return i < 0 ? 0 : Math.sqrt(i);
            }

            checkVisible(sizeMatters = true) {
                const distinguishable =
                    this.node.offsetWidth > 8 && this.node.offsetHeight > 8;
                const inheritable =
                    this.node.offsetParent !== undefined &&
                    this.node.tagName !== 'BODY' &&
                    this.node.offsetParent !== null;

                const physical = sizeMatters
                    ? distinguishable && inheritable
                    : inheritable;

                window.textNodes = window.textNodes || window.collectText();

                const resolvable =
                    (window.textNodes.includes(this.node) &&
                        this.deltaE(
                            this.colorToRGBToHex(this.color),
                            this.colorToRGBToHex(
                                window
                                    .getComputedStyle(document.body)
                                    .getPropertyValue('background-color')
                            )
                        ) > 5) ||
                    Array.from(Object.values(this.contrastColorOptions), (option) =>
                        this.deltaE(
                            this.colorToRGBToHex(this.color),
                            this.colorToRGBToHex(option)
                        )
                    ).some((delta) => delta > 5);

                if (!physical) {
                    this.reason.push(['not physical', true]);
                }
                if (!resolvable) {
                    this.reason.push(['not color resolvable', true]);
                }
                this.visible = physical && resolvable;

                if (this.visible) {
                    for (let key of Object.keys(
                        this.constructor.invisibleCSSpoints
                    )) {
                        const violation = parseInt(this.style.getPropertyValue(key))
                            ? parseInt(this.style.getPropertyValue(key)) <=
                            this.constructor.invisibleCSSpoints[key]
                            : this.style.getPropertyValue(key) ==
                            this.constructor.invisibleCSSpoints[key];

                        if (violation) {
                            this.reason.push([
                                key,
                                this.style.getPropertyValue(key),
                            ]);
                        }
                    }
                    this.visible = !this.reason.length;
                }
            }

            discloseHidden() {
                for (let key of Object.keys(this.constructor.disclosedCSSpoints)) {
                    this.node.style.border = '3px solid red';
                    this.node.style.boxShadow = 'red 0 0 3px 3px';
                    this.node.style.setProperty('min-height', '20px');
                    this.node.style.setProperty('min-width', '20px');
                    this.node.style.setProperty('color', 'black');
                    this.node.style.setProperty('background-color', 'white');
                    this.node.style.setProperty(
                        key,
                        this.constructor.disclosedCSSpoints[key]
                    );
                }
                this.disclosed = true;
            }

            static checkVisibleTree(
                parent,
                sizeMatters = true,
                discloseAction = false,
                visibleCollection = new Set()
            ) {
                const collection = [];

                for (let child of parent.children) {
                    const instance = new VisualDiscloser(child);

                    if (discloseAction) {
                        instance.discloseHidden();
                    }

                    instance.checkVisible(sizeMatters);
                    if (instance.visible) {
                        collection.push(child);
                        visibleCollection.add(child);
                    } else if (
                        !(instance.reason.length - 1) &&
                        instance.reason[0][0] === 'not color resolvable'
                    ) {
                        collection.push(child);
                    }
                }

                for (let child of collection) {
                    this.checkVisibleTree(
                        child,
                        sizeMatters,
                        discloseAction,
                        visibleCollection
                    );
                }

                window.rollbackSpanTexts();

                return [...visibleCollection];
            }
        }

        var collectText = function collectText(
            root = document.body,
            includeItself = false
        ) {
            /* Collect everything that is Element and stores text in it */
            let textElements = textLabelsUnder(root);
            const initLength = textElements.length;

            textElements =
                includeItself == true && hasTextInside(root)
                    ? textElements.concat([root])
                    : textElements;

            /**
            * @description no space, no whitespace, no codes like <,> etc
            * @param {string} html
            *
            * @returns {string} edited string
            */
            function removeWhitespaceSpecial(html) {
                return html
                    .replace(/[&$][a-z]+;/gi, '')
                    .replace(/<iframe.+<\/iframe>/gis, '')
                    .replace(/<script.+<\/script>/gis, '')
                    .trim();
            }

            /**
            * @description replace: find <>, within it find beginning from > and not ending with >
            * @param {string} html
            *
            * @returns {string} edited string
            */
            function extractText(html) {
                return html.replace(/(<([^>]+)>)/gi, '').replace(/.+>$/gi, '');
            }

            function hasTextInside(elem) {
                let inner = elem.innerHTML;

                inner = removeWhitespaceSpecial(inner);
                inner = extractText(inner);

                return /.+/.test(inner.trim());
            }

            function textLabelsUnder(el) {
                let node;
                const elements = [];
                const walk = document.createTreeWalker(
                    el,
                    NodeFilter.SHOW_ELEMENT,
                    null,
                    false
                );

                while ((node = walk.nextNode())) {
                    if (hasTextInside(node)) {
                        elements.push(node);
                    }
                }

                return elements;
            }

            function shrinkClientRectToText(elem) {
                let span;
                const spanCreated = [];
                const texts = [...elem.childNodes].filter(
                    (node) =>
                        node.nodeType === Node.TEXT_NODE &&
                        removeWhitespaceSpecial(node.textContent)
                );
                let spanMessage;

                if (!texts.length) {
                    return null;
                }

                for (const text of texts) {
                    spanMessage = text.parentElement.getAttribute('message');
                    if (
                        spanMessage &&
                        spanMessage.startsWith('this span is for dev')
                    ) {
                        spanCreated.push(text.parentElement);
                        continue;
                    }
                    span = document.createElement('span');
                    text.parentNode.insertBefore(span, text);
                    span.appendChild(text);
                    span.setAttribute(
                        'message',
                        'this span is for dev to wrap the text node'
                    );
                    spanCreated.push(span);
                }

                return spanCreated;
            }
            textElements.forEach((elem) => {
                const textSpanArray = shrinkClientRectToText(elem);
                if (textSpanArray) {
                    textElements.push(...textSpanArray);
                }
            });
            textElements = textElements.slice(initLength);

            return textElements;
        };

        var rollbackSpanTexts = function () {
            const spanTexts = [...document.getElementsByTagName('SPAN')].filter(
                (span) =>
                    span.getAttribute('message') &&
                    span.getAttribute('message').startsWith('this span is for dev')
            );

            spanTexts.forEach((span) => {
                span.replaceWith(span.textContent);
            });
        };

        window.VisualDiscloser = VisualDiscloser;
        window.collectText = collectText;
        window.rollbackSpanTexts = rollbackSpanTexts;
    })();
"""

amount_of_loaded_visual_elements_of_any_size = """
    return VisualDiscloser.checkVisibleTree(arguments[0], false).length;
"""

/*!
 * cg-slider v0.1.8 - Accessible Slider Component
 * 
 * (c) 2015-2018 Competentum Group | http://competentum.com
 * Released under the MIT license
 * https://opensource.org/licenses/mit-license.php
 */
(function webpackUniversalModuleDefinition(root, factory) {
	if(typeof exports === 'object' && typeof module === 'object')
		module.exports = factory();
	else if(typeof define === 'function' && define.amd)
		define([], factory);
	else if(typeof exports === 'object')
		exports["CgSlider"] = factory();
	else
		root["CgSlider"] = factory();
})(this, function() {
return /******/ (function(modules) { // webpackBootstrap
/******/ 	// The module cache
/******/ 	var installedModules = {};

/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {

/******/ 		// Check if module is in cache
/******/ 		if(installedModules[moduleId])
/******/ 			return installedModules[moduleId].exports;

/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = installedModules[moduleId] = {
/******/ 			exports: {},
/******/ 			id: moduleId,
/******/ 			loaded: false
/******/ 		};

/******/ 		// Execute the module function
/******/ 		modules[moduleId].call(module.exports, module, module.exports, __webpack_require__);

/******/ 		// Flag the module as loaded
/******/ 		module.loaded = true;

/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}


/******/ 	// expose the modules object (__webpack_modules__)
/******/ 	__webpack_require__.m = modules;

/******/ 	// expose the module cache
/******/ 	__webpack_require__.c = installedModules;

/******/ 	// __webpack_public_path__
/******/ 	__webpack_require__.p = "";

/******/ 	// Load entry module and return exports
/******/ 	return __webpack_require__(0);
/******/ })
/************************************************************************/
/******/ ([
/* 0 */
/***/ (function(module, exports, __webpack_require__) {

	module.exports = __webpack_require__(1);


/***/ }),
/* 1 */
/***/ (function(module, exports, __webpack_require__) {

	'use strict';

	var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

	__webpack_require__(2);

	var _events = __webpack_require__(6);

	var _events2 = _interopRequireDefault(_events);

	var _keycode = __webpack_require__(7);

	var _keycode2 = _interopRequireDefault(_keycode);

	var _merge = __webpack_require__(8);

	var _merge2 = _interopRequireDefault(_merge);

	var _cgComponentUtils = __webpack_require__(10);

	var _cgComponentUtils2 = _interopRequireDefault(_cgComponentUtils);

	var _helpFuncs = __webpack_require__(12);

	var _helpFuncs2 = _interopRequireDefault(_helpFuncs);

	function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

	function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

	function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

	function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

	/**
	 * Slider's customizing settings
	 * @typedef {Object} SliderSettings
	 * @property {Element|string} container - DOM Element or element id in which slider instance should be rendered.
	 *                                        This property can be omitted. In this case new DOM element will be created and can be accessed via `sliderInstance.container`
	 * @property {number|number[]} initialValue - Value which will be set on initialization.
	 * @property {boolean} disabled - Disables the slider if set to true.
	 * @property {boolean} isRange - Whether the slider represents a range.
	 *                               If set to true, the slider will detect if you have two handles and create a styleable range element between these two.
	 * @property {number} min - The minimum value of the slider.
	 * @property {number} max - The maximum value of the slider.
	 * @property {number} step - Determines the size or amount of each interval or step the slider takes between the min and max.
	 *                           The full specified value range of the slider (max - min) should be evenly divisible by the step.
	 * @property {boolean|function(Element, number, number):boolean} ticks - Controls slider value ticks. You can configure (or skip) every tick by setting this option as a formatter function.
	 *                          The formatter function receives:
	 *                          `tick` DOM Element, `currentStep` number value, calculated `offsetPercent` percent number from the left side of a tick parent.
	 *                          Return falsy value from the formatter to skip the tick creation.
	 * @property {number|number[]} tabindex - Tabindex of handle element. It can be array of two numbers for the range slider.
	 * @property {string|string[]} ariaLabel - String that labels the current slider for screen readers. It can be array of two strings the for range slider.
	 *                                         For more info see [WAI-ARIA specification/#aria-label]{@link https://www.w3.org/TR/wai-aria-1.1/#aria-label}.
	 * @property {string|string[]} ariaLabelledBy - Id of the element that labels the current slider. It can be array of two strings for the range slider.
	 *                                             This property has higher priority than `ariaLabel`.
	 *                                             For more info see [WAI-ARIA specification/#aria-labelledby]{@link https://www.w3.org/TR/wai-aria-1.1/#aria-labelledby}.
	 * @property {string|string[]} ariaDescribedBy - Id of the element that describes the current slider. It can be array of two strings for the range slider.
	 *                                               This property has higher priority than `ariaLabel` and `ariaLabelledBy`.
	 *                                               For more info see [WAI-ARIA specification/#aria-describedby]{@link https://www.w3.org/TR/wai-aria-1.1/#aria-describedby}.
	 * @property {function(number):string} ariaValueTextFormatter - Label formatter callback. It receives value as a parameter and should return corresponding label.
	 *                                                              For more info see [WAI-ARIA specification/#aria-valuetext]{@link https://www.w3.org/TR/wai-aria-1.1/#aria-valuetext}.
	 */

	var SLIDER_CLASS = 'cg-slider';
	var RANGE_CLASS = SLIDER_CLASS + '-range';
	var SLIDER_BG = SLIDER_CLASS + '-bg';
	var PROGRESS_CLASS = SLIDER_CLASS + '-progress';
	var HANDLE_CLASS = SLIDER_CLASS + '-handle';
	var MIN_HANDLE_CLASS = SLIDER_CLASS + '-handle-min';
	var MAX_HANDLE_CLASS = SLIDER_CLASS + '-handle-max';
	var TICKS_CLASS = SLIDER_CLASS + '-ticks';
	var TICKS_ITEM_CLASS = SLIDER_CLASS + '-tick';

	var LARGE_CHANGE_MULTIPLIER = 10;

	var CgSlider = function (_EventEmitter) {
	  _inherits(CgSlider, _EventEmitter);

	  _createClass(CgSlider, null, [{
	    key: '_fixSetting',


	    /**
	     * Default instance settings.
	     * @type SliderSettings
	     */
	    value: function _fixSetting(name, setting) {
	      var constructor = this; // without this declaration IDE will highlight static variables as error

	      switch (name) {
	        case 'disabled':
	          setting = !!setting;
	          break;
	        case 'tabindex':
	          if (typeof setting === 'number') {
	            setting = [setting, setting];
	          } else if (Array.isArray(setting)) {
	            if (setting.length > 2) {
	              setting.length = 2;
	            } else {
	              while (setting.length < 2) {
	                setting.push(setting[0] || constructor.DEFAULT_SETTINGS.tabindex[0]);
	              }
	            }
	          } else {
	            throw new Error(this.name + ' error: type of passed setting \'' + name + '\' is not supported.');
	          }
	          break;

	        case 'ariaLabel':
	        case 'ariaLabelledBy':
	        case 'ariaDescribedBy':
	          if (typeof setting === 'string') {
	            setting = [setting, setting];
	          } else if (Array.isArray(setting)) {
	            if (setting.length > 2) {
	              setting.length = 2;
	            } else {
	              while (setting.length < 2) {
	                setting.push(setting[0] || constructor.DEFAULT_SETTINGS[name]);
	              }
	            }
	          } else {
	            throw new Error(this.name + ' error: type of passed setting \'' + name + '\' is not supported.');
	          }
	          break;

	        case 'ariaValueTextFormatter':
	          if (typeof setting !== 'function') {
	            throw new Error(this.name + ' error: type of passed setting \'' + name + '\' must be a function.');
	          }
	          break;

	        default:
	          break;
	      }
	      return setting;
	    }

	    /**
	     * Fixes settings object.
	     * @param {SliderSettings} settings
	     * @returns {SliderSettings}
	     * @private
	     */


	    /**
	     * Events which can be emitted.
	     * @type {{CHANGE: string, START_CHANGE: string, STOP_CHANGE: string}}
	     */

	  }, {
	    key: '_fixSettings',
	    value: function _fixSettings(settings) {
	      for (var name in settings) {
	        if (settings.hasOwnProperty(name)) {
	          settings[name] = this._fixSetting(name, settings[name]);
	        }
	      }

	      if (settings.initialValue === null) {
	        settings.initialValue = settings.isRange ? [settings.min, settings.min + settings.step] : settings.min;
	      }

	      return settings;
	    }

	    /**
	     * Returns true if two passed slider value are equal.
	     * @param {number[]|undefined} val_1 - slider value. Can be array of 2 numbers or undefined.
	     * @param {number[]|undefined} val_2 - same as val_1
	     * @return {boolean}
	     * @private
	     */

	  }, {
	    key: '_valuesAreEqual',
	    value: function _valuesAreEqual(val_1, val_2) {
	      // both of values are undefined
	      if (val_1 === val_2) return true;

	      // one of values is undefined
	      if (typeof val_1 === 'undefined' || typeof val_2 === 'undefined') {
	        return false;
	      }

	      if (!Array.isArray(val_1) || !Array.isArray(val_2)) throw new Error(this.name + ' error: type of passed value is not supported. It must be array of two numbers.');

	      return val_1[0] === val_2[0] && val_1[1] === val_2[1];
	    }

	    /**
	     *
	     * @param {SliderSettings} settings
	     */

	  }]);

	  function CgSlider(settings) {
	    _classCallCheck(this, CgSlider);

	    var _this = _possibleConstructorReturn(this, (CgSlider.__proto__ || Object.getPrototypeOf(CgSlider)).call(this));

	    _this._applySettings(settings);
	    _this._render();
	    _this._addListeners();
	    _this._setValue(_this.initialValue, true);
	    return _this;
	  }

	  /**
	   *
	   * @returns {string|string[]}
	   */


	  _createClass(CgSlider, [{
	    key: 'getSetting',


	    /**
	     * Returns value of the specified setting.
	     * @param {string} name - setting name.
	     * @returns {*}
	     */
	    value: function getSetting(name) {
	      switch (name) {
	        case 'disabled':
	        case 'min':
	        case 'max':
	        case 'step':
	        case 'isRange':
	        case 'ticks':
	        case 'ariaValueTextFormatter':
	          return this._settings[name];

	        case 'tabindex':
	        case 'ariaLabel':
	        case 'ariaLabelledBy':
	        case 'ariaDescribedBy':
	          return this.isRange ? this._settings[name] : this._settings[name][1];

	        default:
	          throw new Error(this.constructor.name + ' getSetting error: passed setting \'' + name + '\' is not supported.');
	      }
	    }

	    /**
	     *
	     * @param {string} name
	     * @param {*} val
	     */

	  }, {
	    key: 'setSetting',
	    value: function setSetting(name, val) {
	      val = this.constructor._fixSetting(name, val);

	      switch (name) {
	        case 'disabled':
	          this._settings.disabled = val;
	          this._updateDisabled();
	          break;

	        case 'min':
	        case 'max':
	        case 'step':
	          this._settings[name] = val;

	          if (this._value) {
	            // reset value to apply it with new limits and step
	            this._setValue(this.value, true);
	          }

	          this._updateAriaLimits();
	          this._updateTicks();
	          break;

	        case 'ticks':
	          this._settings[name] = val;
	          this._updateTicks();
	          break;

	        //todo: remove this setting from this method to make it readable only.
	        case 'isRange':
	          this._settings.isRange = !!val;
	          //todo: redraw handles
	          break;

	        case 'tabindex':
	          this._settings.tabindex = val;
	          if (this._minHandleElement) {
	            this._minHandleElement.setAttribute('tabindex', this._settings.tabindex[0]);
	          }
	          if (this._maxHandleElement) {
	            this._maxHandleElement.setAttribute('tabindex', this._settings.tabindex[1]);
	          }
	          break;

	        case 'ariaLabel':
	        case 'ariaLabelledBy':
	        case 'ariaDescribedBy':
	          this._settings[name] = val;

	          this._updateAriaLabels();
	          break;

	        case 'ariaValueTextFormatter':
	          this._settings[name] = val;
	          if (typeof this._value !== 'undefined') {
	            this._updateAriaValueTexts(this._value[0], this._value[1]);
	          }
	          break;

	        default:
	          throw new Error(this.constructor.name + ' setSetting error: passed setting \'' + name + '\' is not supported.');
	      }
	    }

	    /**
	     * Move slider `stepCount` steps back or forward
	     * @param {number|number[]} stepCount Positive or negative integer
	     */

	  }, {
	    key: 'move',
	    value: function move(stepCount) {
	      var _this2 = this;

	      if (Array.isArray(stepCount)) {
	        this.value = stepCount.map(function (count, index) {
	          return _this2._value[index] + _this2.step * count;
	        });
	      } else if (typeof stepCount === 'number') {
	        this.value = this._value[1] + this.step * stepCount;
	      }
	    }

	    /**
	     * @private
	     */

	  }, {
	    key: '_addListeners',
	    value: function _addListeners() {
	      this._makeDraggable();
	      this._addKeyboardListeners();
	    }

	    /**
	     * Adds interactivity by keyboard.
	     * @private
	     */

	  }, {
	    key: '_addKeyboardListeners',
	    value: function _addKeyboardListeners() {
	      var self = this;
	      var eventsData = {
	        startValue: null,
	        startChangeEmitted: null
	      };

	      this._minHandleElement.addEventListener('keydown', onKeyDown);
	      this._maxHandleElement.addEventListener('keydown', onKeyDown);

	      function onKeyDown(e) {
	        if (self.disabled) return;

	        var currentHandle = this;
	        var isMaxHandle = _cgComponentUtils2.default.hasClass(currentHandle, MAX_HANDLE_CLASS);
	        var newVal = void 0;
	        var change = void 0;

	        if (eventsData.startValue === null) {
	          eventsData.startValue = self._value;
	        }

	        switch ((0, _keycode2.default)(e)) {
	          // min value
	          case 'home':
	            newVal = isMaxHandle ? self.min : [self.min, self._value[1]];
	            break;

	          // max value
	          case 'end':
	            newVal = isMaxHandle ? self.max : [self.max, self._value[1]];
	            break;

	          // increase
	          case 'up':
	          case 'right':
	            newVal = isMaxHandle ? self._value[1] + self.step : [self._value[0] + self.step, self._value[1]];
	            break;

	          // decrease
	          case 'down':
	          case 'left':
	            newVal = isMaxHandle ? self._value[1] - self.step : [self._value[0] - self.step, self._value[1]];
	            break;

	          // Large increase
	          case 'page up':
	            change = LARGE_CHANGE_MULTIPLIER * self.step;
	            newVal = isMaxHandle ? self._value[1] + change : [self._value[0] + change, self._value[1]];
	            break;

	          // Large decrease
	          case 'page down':
	            change = LARGE_CHANGE_MULTIPLIER * self.step;
	            newVal = isMaxHandle ? self._value[1] - change : [self._value[0] - change, self._value[1]];
	            break;

	          default:
	            // not supported keys
	            return;
	        }
	        if (typeof newVal === 'undefined' || isNaN(newVal) && (isNaN(newVal[0]) || isNaN(newVal[1]))) {
	          return;
	        }

	        // emit start change event if value will be changed
	        if (!eventsData.startChangeEmitted && !self.constructor._valuesAreEqual(eventsData.startValue, self._prepareValueToSet(newVal))) {
	          eventsData.startChangeEmitted = true;
	          self.emit(self.constructor.EVENTS.START_CHANGE, self.value);
	          currentHandle.addEventListener('keyup', onKeyboardChangeStop);
	          currentHandle.addEventListener('blur', onKeyboardChangeStop);
	        }

	        self._setValue(newVal);

	        e.preventDefault();
	        e.stopPropagation();
	      }

	      function onKeyboardChangeStop() {
	        this.removeEventListener('keyup', onKeyboardChangeStop);
	        this.removeEventListener('blur', onKeyboardChangeStop);

	        if (eventsData.startChangeEmitted) {
	          self.emit(self.constructor.EVENTS.STOP_CHANGE, self.value);
	        }

	        // clear eventsData
	        for (var key in eventsData) {
	          if (eventsData.hasOwnProperty(key)) {
	            eventsData[key] = null;
	          }
	        }
	      }
	    }

	    /**
	     * Makes slider handles draggable.
	     * @private
	     */

	  }, {
	    key: '_makeDraggable',
	    value: function _makeDraggable() {
	      var self = this;
	      this._minHandleElement.addEventListener('mousedown', onMouseDown);
	      this._minHandleElement.addEventListener('touchstart', onMouseDown);
	      this._maxHandleElement.addEventListener('mousedown', onMouseDown);
	      this._maxHandleElement.addEventListener('touchstart', onMouseDown);

	      var dragData = {
	        startValue: null,
	        startHandlePos: null,
	        startMousePos: null,
	        dragHandle: null,
	        containerWidth: null,
	        startChangeEmitted: null
	      };

	      //todo: move handlers to prototype
	      function onMouseDown(e) {
	        if (self.disabled) return;

	        _cgComponentUtils2.default.extendEventObject(e);

	        dragData.startValue = self._value;
	        dragData.dragHandle = this;
	        dragData.isMaxHandle = _cgComponentUtils2.default.hasClass(dragData.dragHandle, MAX_HANDLE_CLASS);
	        dragData.containerWidth = self._handlesContainer.getBoundingClientRect().width;
	        dragData.startHandlePos = _helpFuncs2.default.getHandlePosition(dragData.dragHandle, self._handlesContainer);
	        dragData.startMousePos = {
	          x: e.px,
	          y: e.py
	        };

	        document.addEventListener('mousemove', onMouseMove);
	        document.addEventListener('touchmove', onMouseMove);
	        document.addEventListener('mouseup', onMouseUp);
	        document.addEventListener('touchend', onMouseUp);
	      }

	      function onMouseMove(e) {
	        _cgComponentUtils2.default.extendEventObject(e);

	        var percent = _helpFuncs2.default.getPercent(dragData.startHandlePos.x + e.px - dragData.startMousePos.x, dragData.containerWidth);
	        var value = _helpFuncs2.default.calcValueByPercent(percent, self.max, self.min);

	        value = dragData.isMaxHandle ? value : [value, self._value[1]];

	        // emit start change event if value will be changed
	        if (!dragData.startChangeEmitted && !self.constructor._valuesAreEqual(dragData.startValue, self._prepareValueToSet(value))) {
	          dragData.startChangeEmitted = true;
	          self.emit(self.constructor.EVENTS.START_CHANGE, self.value);
	        }

	        self._setValue(value);

	        // prevent surrounding element selection in Safari
	        if (document.selection) {
	          document.selection.empty();
	        } else {
	          window.getSelection().removeAllRanges();
	        }

	        e.preventDefault();
	      }

	      function onMouseUp(e) {
	        _cgComponentUtils2.default.extendEventObject(e);
	        document.removeEventListener('mousemove', onMouseMove);
	        document.removeEventListener('touchmove', onMouseMove);
	        document.removeEventListener('mouseup', onMouseUp);
	        document.removeEventListener('touchend', onMouseUp);

	        if (dragData.startChangeEmitted) {
	          self.emit(self.constructor.EVENTS.STOP_CHANGE, self.value);
	        }

	        // clear dragData
	        for (var key in dragData) {
	          if (dragData.hasOwnProperty(key)) {
	            dragData[key] = null;
	          }
	        }

	        e.preventDefault();
	      }
	    }

	    /**
	     * Fixes and sets settings on initialization.
	     * @param {SliderSettings} settings
	     * @private
	     */

	  }, {
	    key: '_applySettings',
	    value: function _applySettings(settings) {
	      var DEFAULT_SETTINGS = this.constructor.DEFAULT_SETTINGS;

	      settings = (0, _merge2.default)({}, DEFAULT_SETTINGS, settings);
	      this.constructor._fixSettings(settings);

	      /** @type SliderSettings */
	      this._settings = {};

	      //
	      if (settings.container instanceof Element) {
	        this._container = settings.container;
	      } else if (typeof settings.container === 'string') {
	        this._container = document.getElementById(settings.container);
	        if (!this.container) {
	          throw new Error(this.constructor.name + ' initialization error: can not find element with id "' + settings.container + '".');
	        }
	      } else if (typeof settings.container === 'undefined') {
	        //todo: create container
	        this._container = document.createElement('div');
	      } else {
	        throw new Error(this.constructor.name + ' initialization error: type of "settings.container" property is unsupported.');
	      }
	      delete settings.container;

	      // call setters for settings which defined in DEFAULT_SETTINGS only
	      for (var key in DEFAULT_SETTINGS) {
	        if (DEFAULT_SETTINGS.hasOwnProperty(key)) {
	          this[key] = settings[key];
	        }
	      }
	    }

	    /**
	     * @private
	     */

	  }, {
	    key: '_render',
	    value: function _render() {
	      var rootClasses = [SLIDER_CLASS];

	      if (this.isRange) {
	        rootClasses.push(RANGE_CLASS);
	      }

	      var elementHTML = '\n      <div class="' + rootClasses.join(' ') + '">\n        <div class="' + SLIDER_BG + '">\n          <div class="' + PROGRESS_CLASS + '"></div>\n          <div class="' + HANDLE_CLASS + ' ' + MIN_HANDLE_CLASS + '" tabindex="' + this._settings.tabindex[0] + '" role="slider" aria-orientation="horizontal"></div>\n          <div class="' + HANDLE_CLASS + ' ' + MAX_HANDLE_CLASS + '" tabindex="' + this._settings.tabindex[1] + '" role="slider" aria-orientation="horizontal"></div>\n        </div>\n        <div class="' + TICKS_CLASS + '" aria-hidden="true"></div>\n      </div>\n    ';

	      this._rootElement = _cgComponentUtils2.default.createHTML(elementHTML);
	      this._ticksElement = this._rootElement.querySelector('.' + TICKS_CLASS);
	      this._progressElement = this._rootElement.querySelector('.' + PROGRESS_CLASS);
	      this._handlesContainer = this._rootElement.querySelector('.' + SLIDER_BG);
	      this._minHandleElement = this._handlesContainer.querySelector('.' + MIN_HANDLE_CLASS);
	      this._maxHandleElement = this._handlesContainer.querySelector('.' + MAX_HANDLE_CLASS);

	      this._updateAriaLimits();
	      this._updateAriaLabels();
	      this._updateDisabled();
	      this._updateTicks();

	      this.container.appendChild(this._rootElement);
	    }

	    /**
	     * Get percentage offset & add ticks
	     * @private
	     */

	  }, {
	    key: '_updateTicks',
	    value: function _updateTicks() {
	      var ticks = this._settings.ticks;


	      if (!this._ticksElement) return;

	      _helpFuncs2.default.removeChildElements(this._ticksElement);

	      if (!ticks) return;

	      var tickFrag = document.createDocumentFragment();

	      var currentStep = this.min;
	      while (_helpFuncs2.default.roundValue(currentStep) <= this.max) {
	        var offsetPercent = _helpFuncs2.default.getPercent(currentStep, this.max, this.min);
	        var tick = document.createElement('div');
	        tick.classList.add(TICKS_ITEM_CLASS);
	        tick.style['left'] = offsetPercent + '%';

	        var formatterResult = typeof ticks === 'function' ? ticks.call(this, tick, currentStep, offsetPercent) : undefined;

	        if (typeof formatterResult === 'undefined' || formatterResult) {
	          tickFrag.appendChild(tick);
	        }

	        tick = null;
	        currentStep += this.step;
	      }

	      this._ticksElement.appendChild(tickFrag);
	    }
	  }, {
	    key: '_updateAriaLabels',
	    value: function _updateAriaLabels() {
	      var settings = this._settings;
	      var minHandle = this._minHandleElement;
	      var maxHandle = this._maxHandleElement;

	      if (!minHandle || !maxHandle) return;

	      _helpFuncs2.default.setAttributeOrRemoveIfEmpty(minHandle, 'aria-label', settings.ariaLabel[0]);
	      _helpFuncs2.default.setAttributeOrRemoveIfEmpty(maxHandle, 'aria-label', settings.ariaLabel[1]);

	      _helpFuncs2.default.setAttributeOrRemoveIfEmpty(minHandle, 'aria-labelledby', settings.ariaLabelledBy[0]);
	      _helpFuncs2.default.setAttributeOrRemoveIfEmpty(maxHandle, 'aria-labelledby', settings.ariaLabelledBy[1]);

	      _helpFuncs2.default.setAttributeOrRemoveIfEmpty(minHandle, 'aria-describedby', settings.ariaDescribedBy[0]);
	      _helpFuncs2.default.setAttributeOrRemoveIfEmpty(maxHandle, 'aria-describedby', settings.ariaDescribedBy[1]);
	    }

	    /**
	     * Updates aria-valuemin/aria-valuemax attributes for handles.
	     * @private
	     */

	  }, {
	    key: '_updateAriaLimits',
	    value: function _updateAriaLimits() {
	      var minHandle = this._minHandleElement;
	      var maxHandle = this._maxHandleElement;

	      if (!minHandle || !maxHandle) return;

	      //todo: add aria-value formatter
	      minHandle.setAttribute('aria-valuemin', this.min);
	      minHandle.setAttribute('aria-valuemax', this.max);

	      maxHandle.setAttribute('aria-valuemin', this.min);
	      maxHandle.setAttribute('aria-valuemax', this.max);
	    }

	    /**
	     * Update aria-valuetext attributes for both handles
	     * @private
	     * @param {number} valMin Min handle value
	     * @param {number} valMax Max handle value
	     */

	  }, {
	    key: '_updateAriaValueTexts',
	    value: function _updateAriaValueTexts(valMin, valMax) {
	      var ariaValueTextFormatter = this._settings.ariaValueTextFormatter;

	      var minValueText = ariaValueTextFormatter.call(this, valMin);
	      var maxValueText = ariaValueTextFormatter.call(this, valMax);
	      this._minHandleElement.setAttribute('aria-valuetext', minValueText);
	      this._maxHandleElement.setAttribute('aria-valuetext', maxValueText);
	    }
	  }, {
	    key: '_updateDisabled',
	    value: function _updateDisabled() {
	      if (!this._rootElement) return;

	      if (this._settings.disabled) {
	        this._rootElement.setAttribute('disabled', 'true');
	        this._minHandleElement.setAttribute('tabindex', '-1');
	        this._maxHandleElement.setAttribute('tabindex', '-1');
	      } else {
	        this._rootElement.removeAttribute('disabled');
	        // restore tabindex
	        this.tabindex = this.tabindex;
	      }
	    }

	    /**
	     * Fixes passed value according to current settings.
	     * @param {number|number[]} val
	     * @return {number[]}
	     * @private
	     */

	  }, {
	    key: '_prepareValueToSet',
	    value: function _prepareValueToSet(val) {
	      // for not range slider value can be number
	      // so it should be converted to array
	      if (typeof val === 'number') {
	        var minVal = void 0;
	        // reset set minimum value for non-range if its larger than maximum
	        if (this.isRange) {
	          minVal = this._value && this._value[0] || this.min;
	        } else {
	          minVal = this._value && this._value[0] <= val ? this._value[0] : this.min;
	        }
	        val = [minVal, val];
	      }

	      var isMaxChanged = void 0;

	      if (typeof this._value !== 'undefined') {
	        isMaxChanged = this._value[1] !== val[1];
	      }

	      val = _helpFuncs2.default.fixValue(val, this.min, this.max, this.step, !this.isRange, isMaxChanged);

	      return val;
	    }

	    /**
	     * Sets slider value.
	     * @param {number|number[]} val - New value.
	     * @param {boolean} [force=false] - If `true` will set value with emitting CHANGE event even value is not changed.
	     * @private
	     */

	  }, {
	    key: '_setValue',
	    value: function _setValue(val) {
	      var force = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : false;

	      if (typeof val !== 'number' && !Array.isArray(val)) {
	        throw new Error(this.constructor.name + ' set value error: passed value\'s (' + val + ') type is not supported.');
	      }

	      val = this._prepareValueToSet(val);

	      var valueChanged = !this.constructor._valuesAreEqual(this._value, val);

	      this._value = val;

	      if (valueChanged || force) {
	        var minPercentVal = _helpFuncs2.default.getPercent(val[0], this.max, this.min);
	        var maxPercentVal = _helpFuncs2.default.getPercent(val[1], this.max, this.min);
	        this._minHandleElement.style.left = minPercentVal + '%';
	        this._maxHandleElement.style.left = maxPercentVal + '%';
	        //todo: add aria-value formatter
	        this._minHandleElement.setAttribute('aria-valuenow', val[0]);
	        this._maxHandleElement.setAttribute('aria-valuenow', val[1]);

	        this._updateAriaValueTexts(val[0], val[1]);

	        this._progressElement.style.left = minPercentVal + '%';
	        this._progressElement.style.width = maxPercentVal - minPercentVal + '%';
	        this.emit(this.constructor.EVENTS.CHANGE, this.value);
	      }
	    }
	  }, {
	    key: 'ariaLabel',
	    get: function get() {
	      return this.getSetting('ariaLabel');
	    }

	    /**
	     *
	     * @param {string|string[]} val
	     */
	    ,
	    set: function set(val) {
	      this.setSetting('ariaLabel', val);
	    }

	    /**
	     *
	     * @returns {string|string[]}
	     */

	  }, {
	    key: 'ariaLabelledBy',
	    get: function get() {
	      return this.getSetting('ariaLabelledBy');
	    }

	    /**
	     *
	     * @param {string|string[]} val
	     */
	    ,
	    set: function set(val) {
	      this.setSetting('ariaLabelledBy', val);
	    }

	    /**
	     *
	     * @returns {string|string[]}
	     */

	  }, {
	    key: 'ariaDescribedBy',
	    get: function get() {
	      return this.getSetting('ariaDescribedBy');
	    }

	    /**
	     *
	     * @param {string|string[]} val
	     */
	    ,
	    set: function set(val) {
	      this.setSetting('ariaDescribedBy', val);
	    }

	    /**
	     * 
	     * @returns {function}
	     */

	  }, {
	    key: 'ariaValueTextFormatter',
	    get: function get() {
	      return this.getSetting('ariaValueTextFormatter');
	    }

	    /**
	     * 
	     * @param {function(number):string} val
	     */
	    ,
	    set: function set(val) {
	      this.setSetting('ariaValueTextFormatter', val);
	    }

	    /**
	     * DOM Element which contains slider.
	     * @returns {Element}
	     */

	  }, {
	    key: 'container',
	    get: function get() {
	      return this._container;
	    }

	    /**
	     *
	     * @returns {boolean}
	     */

	  }, {
	    key: 'disabled',
	    get: function get() {
	      return this.getSetting('disabled');
	    }

	    /**
	     *
	     * @param {boolean} val
	     */
	    ,
	    set: function set(val) {
	      this.setSetting('disabled', val);
	    }

	    /**
	     *
	     * @returns {boolean}
	     */

	  }, {
	    key: 'isRange',
	    get: function get() {
	      return this.getSetting('isRange');
	    }

	    /**
	     *
	     * @param {boolean} val
	     */
	    ,
	    set: function set(val) {
	      this.setSetting('isRange', val);
	    }

	    /**
	     *
	     * @returns {number}
	     */

	  }, {
	    key: 'min',
	    get: function get() {
	      return this.getSetting('min');
	    }

	    /**
	     *
	     * @param {number} val
	     */
	    ,
	    set: function set(val) {
	      this.setSetting('min', val);
	    }

	    /**
	     *
	     * @returns {number}
	     */

	  }, {
	    key: 'max',
	    get: function get() {
	      return this.getSetting('max');
	    }

	    /**
	     *
	     * @param {number} val
	     */
	    ,
	    set: function set(val) {
	      this.setSetting('max', val);
	    }

	    /**
	     *
	     * @returns {number}
	     */

	  }, {
	    key: 'step',
	    get: function get() {
	      return this.getSetting('step');
	    }

	    /**
	     *
	     * @param {number} val
	     */
	    ,
	    set: function set(val) {
	      this.setSetting('step', val);
	    }

	    /**
	     *
	     * @returns {boolean|function}
	     */

	  }, {
	    key: 'ticks',
	    get: function get() {
	      return this.getSetting('ticks');
	    }

	    /**
	     *
	     * @param {boolean|function} val
	     */
	    ,
	    set: function set(val) {
	      this.setSetting('ticks', val);
	    }

	    /**
	     *
	     * @returns {number|number[]}
	     */

	  }, {
	    key: 'tabindex',
	    get: function get() {
	      return this.getSetting('tabindex');
	    }

	    /**
	     *
	     * @param {number|number[]} val
	     */
	    ,
	    set: function set(val) {
	      this.setSetting('tabindex', val);
	    }

	    /**
	     *
	     * @returns {number|number[]}
	     */

	  }, {
	    key: 'value',
	    get: function get() {
	      return this.isRange ? this._value : this._value[1];
	    }

	    /**
	     *
	     * @param {number|number[]} val
	     */
	    ,
	    set: function set(val) {
	      if (Array.isArray(val)) {
	        val.sort(function (a, b) {
	          return a - b;
	        });
	      }
	      this._setValue(val);
	    }
	  }]);

	  return CgSlider;
	}(_events2.default);

	CgSlider.DEFAULT_SETTINGS = {
	  disabled: false,
	  initialValue: null,
	  isRange: false,
	  min: 0,
	  max: 100,
	  step: 1,
	  ticks: false,
	  tabindex: [0, 0],
	  ariaLabel: '',
	  ariaLabelledBy: '',
	  ariaDescribedBy: '',
	  ariaValueTextFormatter: function ariaValueTextFormatter(val) {
	    return val.toString();
	  }
	};
	CgSlider.EVENTS = {
	  CHANGE: 'change',
	  START_CHANGE: 'start_change',
	  STOP_CHANGE: 'stop_change'
	};


	module.exports = CgSlider;

/***/ }),
/* 2 */
/***/ (function(module, exports, __webpack_require__) {

	// style-loader: Adds some css to the DOM by adding a <style> tag

	// load the styles
	var content = __webpack_require__(3);
	if(typeof content === 'string') content = [[module.id, content, '']];
	// add the styles to the DOM
	var update = __webpack_require__(5)(content, {});
	if(content.locals) module.exports = content.locals;
	// Hot Module Replacement
	if(false) {
		// When the styles change, update the <style> tags
		if(!content.locals) {
			module.hot.accept("!!../node_modules/css-loader/index.js!../node_modules/postcss-loader/index.js!../node_modules/less-loader/dist/cjs.js!./common.less", function() {
				var newContent = require("!!../node_modules/css-loader/index.js!../node_modules/postcss-loader/index.js!../node_modules/less-loader/dist/cjs.js!./common.less");
				if(typeof newContent === 'string') newContent = [[module.id, newContent, '']];
				update(newContent);
			});
		}
		// When the module is disposed, remove the <style> tags
		module.hot.dispose(function() { update(); });
	}

/***/ }),
/* 3 */
/***/ (function(module, exports, __webpack_require__) {

	exports = module.exports = __webpack_require__(4)();
	// imports


	// module
	exports.push([module.id, ".cg-slider {\n  padding: 10px 13px;\n  position: relative;\n  -webkit-user-select: none;\n     -moz-user-select: none;\n      -ms-user-select: none;\n          user-select: none;\n  box-sizing: border-box;\n}\n.cg-slider .cg-slider-bg {\n  height: 6px;\n  background: #aaaaaa;\n  position: relative;\n}\n.cg-slider .cg-slider-progress {\n  position: absolute;\n  top: 0;\n  left: 0;\n  height: 100%;\n  background: #17AC5B;\n}\n.cg-slider .cg-slider-handle {\n  top: 50%;\n  left: 0;\n  border-radius: 50%;\n  position: absolute;\n  height: 18px;\n  width: 18px;\n  background: #17AC5B;\n  cursor: pointer;\n  margin-left: -9px;\n  margin-top: -9px;\n  z-index: 1;\n}\n.cg-slider .cg-slider-handle:before,\n.cg-slider .cg-slider-handle:after {\n  content: \"\";\n  position: absolute;\n  left: 0;\n  right: 0;\n  bottom: 0;\n  top: 0;\n  border-radius: 50%;\n}\n.cg-slider .cg-slider-handle:after {\n  transition: left 0.3s, right 0.3s, bottom 0.3s, top 0.3s;\n}\n.cg-slider .cg-slider-handle:before,\n.cg-slider .cg-slider-handle:hover:after,\n.cg-slider .cg-slider-handle:active:after {\n  left: -4px;\n  right: -4px;\n  bottom: -4px;\n  top: -4px;\n}\n.cg-slider .cg-slider-handle:hover:after,\n.cg-slider .cg-slider-handle:active:after {\n  background: #17AC5B;\n}\n.cg-slider .cg-slider-handle:focus {\n  outline: none;\n}\n.cg-slider .cg-slider-handle:focus:before {\n  background-color: rgba(23, 172, 91, 0.4);\n}\n.cg-slider .cg-slider-ticks {\n  position: relative;\n  width: 100%;\n  top: -20px;\n}\n.cg-slider .cg-slider-ticks .cg-slider-tick {\n  position: absolute;\n  height: 6px;\n  width: 2px;\n  margin-left: -1px;\n  background: #aaaaaa;\n}\n.cg-slider .cg-slider-handle-min {\n  display: none;\n}\n.cg-slider.cg-slider-range .cg-slider-handle-min {\n  display: block;\n}\n.cg-slider[disabled=true] {\n  opacity: 0.6;\n}\n.cg-slider[disabled=true] .cg-slider-handle {\n  cursor: auto;\n}\n.cg-slider[disabled=true] .cg-slider-handle:before,\n.cg-slider[disabled=true] .cg-slider-handle:after {\n  display: none;\n}\n", ""]);

	// exports


/***/ }),
/* 4 */
/***/ (function(module, exports) {

	/*
		MIT License http://www.opensource.org/licenses/mit-license.php
		Author Tobias Koppers @sokra
	*/
	// css base code, injected by the css-loader
	module.exports = function() {
		var list = [];

		// return the list of modules as css string
		list.toString = function toString() {
			var result = [];
			for(var i = 0; i < this.length; i++) {
				var item = this[i];
				if(item[2]) {
					result.push("@media " + item[2] + "{" + item[1] + "}");
				} else {
					result.push(item[1]);
				}
			}
			return result.join("");
		};

		// import a list of modules into the list
		list.i = function(modules, mediaQuery) {
			if(typeof modules === "string")
				modules = [[null, modules, ""]];
			var alreadyImportedModules = {};
			for(var i = 0; i < this.length; i++) {
				var id = this[i][0];
				if(typeof id === "number")
					alreadyImportedModules[id] = true;
			}
			for(i = 0; i < modules.length; i++) {
				var item = modules[i];
				// skip already imported module
				// this implementation is not 100% perfect for weird media query combinations
				//  when a module is imported multiple times with different media queries.
				//  I hope this will never occur (Hey this way we have smaller bundles)
				if(typeof item[0] !== "number" || !alreadyImportedModules[item[0]]) {
					if(mediaQuery && !item[2]) {
						item[2] = mediaQuery;
					} else if(mediaQuery) {
						item[2] = "(" + item[2] + ") and (" + mediaQuery + ")";
					}
					list.push(item);
				}
			}
		};
		return list;
	};


/***/ }),
/* 5 */
/***/ (function(module, exports, __webpack_require__) {

	/*
		MIT License http://www.opensource.org/licenses/mit-license.php
		Author Tobias Koppers @sokra
	*/
	var stylesInDom = {},
		memoize = function(fn) {
			var memo;
			return function () {
				if (typeof memo === "undefined") memo = fn.apply(this, arguments);
				return memo;
			};
		},
		isOldIE = memoize(function() {
			return /msie [6-9]\b/.test(self.navigator.userAgent.toLowerCase());
		}),
		getHeadElement = memoize(function () {
			return document.head || document.getElementsByTagName("head")[0];
		}),
		singletonElement = null,
		singletonCounter = 0,
		styleElementsInsertedAtTop = [];

	module.exports = function(list, options) {
		if(false) {
			if(typeof document !== "object") throw new Error("The style-loader cannot be used in a non-browser environment");
		}

		options = options || {};
		// Force single-tag solution on IE6-9, which has a hard limit on the # of <style>
		// tags it will allow on a page
		if (typeof options.singleton === "undefined") options.singleton = isOldIE();

		// By default, add <style> tags to the bottom of <head>.
		if (typeof options.insertAt === "undefined") options.insertAt = "bottom";

		var styles = listToStyles(list);
		addStylesToDom(styles, options);

		return function update(newList) {
			var mayRemove = [];
			for(var i = 0; i < styles.length; i++) {
				var item = styles[i];
				var domStyle = stylesInDom[item.id];
				domStyle.refs--;
				mayRemove.push(domStyle);
			}
			if(newList) {
				var newStyles = listToStyles(newList);
				addStylesToDom(newStyles, options);
			}
			for(var i = 0; i < mayRemove.length; i++) {
				var domStyle = mayRemove[i];
				if(domStyle.refs === 0) {
					for(var j = 0; j < domStyle.parts.length; j++)
						domStyle.parts[j]();
					delete stylesInDom[domStyle.id];
				}
			}
		};
	}

	function addStylesToDom(styles, options) {
		for(var i = 0; i < styles.length; i++) {
			var item = styles[i];
			var domStyle = stylesInDom[item.id];
			if(domStyle) {
				domStyle.refs++;
				for(var j = 0; j < domStyle.parts.length; j++) {
					domStyle.parts[j](item.parts[j]);
				}
				for(; j < item.parts.length; j++) {
					domStyle.parts.push(addStyle(item.parts[j], options));
				}
			} else {
				var parts = [];
				for(var j = 0; j < item.parts.length; j++) {
					parts.push(addStyle(item.parts[j], options));
				}
				stylesInDom[item.id] = {id: item.id, refs: 1, parts: parts};
			}
		}
	}

	function listToStyles(list) {
		var styles = [];
		var newStyles = {};
		for(var i = 0; i < list.length; i++) {
			var item = list[i];
			var id = item[0];
			var css = item[1];
			var media = item[2];
			var sourceMap = item[3];
			var part = {css: css, media: media, sourceMap: sourceMap};
			if(!newStyles[id])
				styles.push(newStyles[id] = {id: id, parts: [part]});
			else
				newStyles[id].parts.push(part);
		}
		return styles;
	}

	function insertStyleElement(options, styleElement) {
		var head = getHeadElement();
		var lastStyleElementInsertedAtTop = styleElementsInsertedAtTop[styleElementsInsertedAtTop.length - 1];
		if (options.insertAt === "top") {
			if(!lastStyleElementInsertedAtTop) {
				head.insertBefore(styleElement, head.firstChild);
			} else if(lastStyleElementInsertedAtTop.nextSibling) {
				head.insertBefore(styleElement, lastStyleElementInsertedAtTop.nextSibling);
			} else {
				head.appendChild(styleElement);
			}
			styleElementsInsertedAtTop.push(styleElement);
		} else if (options.insertAt === "bottom") {
			head.appendChild(styleElement);
		} else {
			throw new Error("Invalid value for parameter 'insertAt'. Must be 'top' or 'bottom'.");
		}
	}

	function removeStyleElement(styleElement) {
		styleElement.parentNode.removeChild(styleElement);
		var idx = styleElementsInsertedAtTop.indexOf(styleElement);
		if(idx >= 0) {
			styleElementsInsertedAtTop.splice(idx, 1);
		}
	}

	function createStyleElement(options) {
		var styleElement = document.createElement("style");
		styleElement.type = "text/css";
		insertStyleElement(options, styleElement);
		return styleElement;
	}

	function createLinkElement(options) {
		var linkElement = document.createElement("link");
		linkElement.rel = "stylesheet";
		insertStyleElement(options, linkElement);
		return linkElement;
	}

	function addStyle(obj, options) {
		var styleElement, update, remove;

		if (options.singleton) {
			var styleIndex = singletonCounter++;
			styleElement = singletonElement || (singletonElement = createStyleElement(options));
			update = applyToSingletonTag.bind(null, styleElement, styleIndex, false);
			remove = applyToSingletonTag.bind(null, styleElement, styleIndex, true);
		} else if(obj.sourceMap &&
			typeof URL === "function" &&
			typeof URL.createObjectURL === "function" &&
			typeof URL.revokeObjectURL === "function" &&
			typeof Blob === "function" &&
			typeof btoa === "function") {
			styleElement = createLinkElement(options);
			update = updateLink.bind(null, styleElement);
			remove = function() {
				removeStyleElement(styleElement);
				if(styleElement.href)
					URL.revokeObjectURL(styleElement.href);
			};
		} else {
			styleElement = createStyleElement(options);
			update = applyToTag.bind(null, styleElement);
			remove = function() {
				removeStyleElement(styleElement);
			};
		}

		update(obj);

		return function updateStyle(newObj) {
			if(newObj) {
				if(newObj.css === obj.css && newObj.media === obj.media && newObj.sourceMap === obj.sourceMap)
					return;
				update(obj = newObj);
			} else {
				remove();
			}
		};
	}

	var replaceText = (function () {
		var textStore = [];

		return function (index, replacement) {
			textStore[index] = replacement;
			return textStore.filter(Boolean).join('\n');
		};
	})();

	function applyToSingletonTag(styleElement, index, remove, obj) {
		var css = remove ? "" : obj.css;

		if (styleElement.styleSheet) {
			styleElement.styleSheet.cssText = replaceText(index, css);
		} else {
			var cssNode = document.createTextNode(css);
			var childNodes = styleElement.childNodes;
			if (childNodes[index]) styleElement.removeChild(childNodes[index]);
			if (childNodes.length) {
				styleElement.insertBefore(cssNode, childNodes[index]);
			} else {
				styleElement.appendChild(cssNode);
			}
		}
	}

	function applyToTag(styleElement, obj) {
		var css = obj.css;
		var media = obj.media;

		if(media) {
			styleElement.setAttribute("media", media)
		}

		if(styleElement.styleSheet) {
			styleElement.styleSheet.cssText = css;
		} else {
			while(styleElement.firstChild) {
				styleElement.removeChild(styleElement.firstChild);
			}
			styleElement.appendChild(document.createTextNode(css));
		}
	}

	function updateLink(linkElement, obj) {
		var css = obj.css;
		var sourceMap = obj.sourceMap;

		if(sourceMap) {
			// http://stackoverflow.com/a/26603875
			css += "\n/*# sourceMappingURL=data:application/json;base64," + btoa(unescape(encodeURIComponent(JSON.stringify(sourceMap)))) + " */";
		}

		var blob = new Blob([css], { type: "text/css" });

		var oldSrc = linkElement.href;

		linkElement.href = URL.createObjectURL(blob);

		if(oldSrc)
			URL.revokeObjectURL(oldSrc);
	}


/***/ }),
/* 6 */
/***/ (function(module, exports) {

	// Copyright Joyent, Inc. and other Node contributors.
	//
	// Permission is hereby granted, free of charge, to any person obtaining a
	// copy of this software and associated documentation files (the
	// "Software"), to deal in the Software without restriction, including
	// without limitation the rights to use, copy, modify, merge, publish,
	// distribute, sublicense, and/or sell copies of the Software, and to permit
	// persons to whom the Software is furnished to do so, subject to the
	// following conditions:
	//
	// The above copyright notice and this permission notice shall be included
	// in all copies or substantial portions of the Software.
	//
	// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
	// OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
	// MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
	// NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
	// DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
	// OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
	// USE OR OTHER DEALINGS IN THE SOFTWARE.

	function EventEmitter() {
	  this._events = this._events || {};
	  this._maxListeners = this._maxListeners || undefined;
	}
	module.exports = EventEmitter;

	// Backwards-compat with node 0.10.x
	EventEmitter.EventEmitter = EventEmitter;

	EventEmitter.prototype._events = undefined;
	EventEmitter.prototype._maxListeners = undefined;

	// By default EventEmitters will print a warning if more than 10 listeners are
	// added to it. This is a useful default which helps finding memory leaks.
	EventEmitter.defaultMaxListeners = 10;

	// Obviously not all Emitters should be limited to 10. This function allows
	// that to be increased. Set to zero for unlimited.
	EventEmitter.prototype.setMaxListeners = function(n) {
	  if (!isNumber(n) || n < 0 || isNaN(n))
	    throw TypeError('n must be a positive number');
	  this._maxListeners = n;
	  return this;
	};

	EventEmitter.prototype.emit = function(type) {
	  var er, handler, len, args, i, listeners;

	  if (!this._events)
	    this._events = {};

	  // If there is no 'error' event listener then throw.
	  if (type === 'error') {
	    if (!this._events.error ||
	        (isObject(this._events.error) && !this._events.error.length)) {
	      er = arguments[1];
	      if (er instanceof Error) {
	        throw er; // Unhandled 'error' event
	      } else {
	        // At least give some kind of context to the user
	        var err = new Error('Uncaught, unspecified "error" event. (' + er + ')');
	        err.context = er;
	        throw err;
	      }
	    }
	  }

	  handler = this._events[type];

	  if (isUndefined(handler))
	    return false;

	  if (isFunction(handler)) {
	    switch (arguments.length) {
	      // fast cases
	      case 1:
	        handler.call(this);
	        break;
	      case 2:
	        handler.call(this, arguments[1]);
	        break;
	      case 3:
	        handler.call(this, arguments[1], arguments[2]);
	        break;
	      // slower
	      default:
	        args = Array.prototype.slice.call(arguments, 1);
	        handler.apply(this, args);
	    }
	  } else if (isObject(handler)) {
	    args = Array.prototype.slice.call(arguments, 1);
	    listeners = handler.slice();
	    len = listeners.length;
	    for (i = 0; i < len; i++)
	      listeners[i].apply(this, args);
	  }

	  return true;
	};

	EventEmitter.prototype.addListener = function(type, listener) {
	  var m;

	  if (!isFunction(listener))
	    throw TypeError('listener must be a function');

	  if (!this._events)
	    this._events = {};

	  // To avoid recursion in the case that type === "newListener"! Before
	  // adding it to the listeners, first emit "newListener".
	  if (this._events.newListener)
	    this.emit('newListener', type,
	              isFunction(listener.listener) ?
	              listener.listener : listener);

	  if (!this._events[type])
	    // Optimize the case of one listener. Don't need the extra array object.
	    this._events[type] = listener;
	  else if (isObject(this._events[type]))
	    // If we've already got an array, just append.
	    this._events[type].push(listener);
	  else
	    // Adding the second element, need to change to array.
	    this._events[type] = [this._events[type], listener];

	  // Check for listener leak
	  if (isObject(this._events[type]) && !this._events[type].warned) {
	    if (!isUndefined(this._maxListeners)) {
	      m = this._maxListeners;
	    } else {
	      m = EventEmitter.defaultMaxListeners;
	    }

	    if (m && m > 0 && this._events[type].length > m) {
	      this._events[type].warned = true;
	      console.error('(node) warning: possible EventEmitter memory ' +
	                    'leak detected. %d listeners added. ' +
	                    'Use emitter.setMaxListeners() to increase limit.',
	                    this._events[type].length);
	      if (typeof console.trace === 'function') {
	        // not supported in IE 10
	        console.trace();
	      }
	    }
	  }

	  return this;
	};

	EventEmitter.prototype.on = EventEmitter.prototype.addListener;

	EventEmitter.prototype.once = function(type, listener) {
	  if (!isFunction(listener))
	    throw TypeError('listener must be a function');

	  var fired = false;

	  function g() {
	    this.removeListener(type, g);

	    if (!fired) {
	      fired = true;
	      listener.apply(this, arguments);
	    }
	  }

	  g.listener = listener;
	  this.on(type, g);

	  return this;
	};

	// emits a 'removeListener' event iff the listener was removed
	EventEmitter.prototype.removeListener = function(type, listener) {
	  var list, position, length, i;

	  if (!isFunction(listener))
	    throw TypeError('listener must be a function');

	  if (!this._events || !this._events[type])
	    return this;

	  list = this._events[type];
	  length = list.length;
	  position = -1;

	  if (list === listener ||
	      (isFunction(list.listener) && list.listener === listener)) {
	    delete this._events[type];
	    if (this._events.removeListener)
	      this.emit('removeListener', type, listener);

	  } else if (isObject(list)) {
	    for (i = length; i-- > 0;) {
	      if (list[i] === listener ||
	          (list[i].listener && list[i].listener === listener)) {
	        position = i;
	        break;
	      }
	    }

	    if (position < 0)
	      return this;

	    if (list.length === 1) {
	      list.length = 0;
	      delete this._events[type];
	    } else {
	      list.splice(position, 1);
	    }

	    if (this._events.removeListener)
	      this.emit('removeListener', type, listener);
	  }

	  return this;
	};

	EventEmitter.prototype.removeAllListeners = function(type) {
	  var key, listeners;

	  if (!this._events)
	    return this;

	  // not listening for removeListener, no need to emit
	  if (!this._events.removeListener) {
	    if (arguments.length === 0)
	      this._events = {};
	    else if (this._events[type])
	      delete this._events[type];
	    return this;
	  }

	  // emit removeListener for all listeners on all events
	  if (arguments.length === 0) {
	    for (key in this._events) {
	      if (key === 'removeListener') continue;
	      this.removeAllListeners(key);
	    }
	    this.removeAllListeners('removeListener');
	    this._events = {};
	    return this;
	  }

	  listeners = this._events[type];

	  if (isFunction(listeners)) {
	    this.removeListener(type, listeners);
	  } else if (listeners) {
	    // LIFO order
	    while (listeners.length)
	      this.removeListener(type, listeners[listeners.length - 1]);
	  }
	  delete this._events[type];

	  return this;
	};

	EventEmitter.prototype.listeners = function(type) {
	  var ret;
	  if (!this._events || !this._events[type])
	    ret = [];
	  else if (isFunction(this._events[type]))
	    ret = [this._events[type]];
	  else
	    ret = this._events[type].slice();
	  return ret;
	};

	EventEmitter.prototype.listenerCount = function(type) {
	  if (this._events) {
	    var evlistener = this._events[type];

	    if (isFunction(evlistener))
	      return 1;
	    else if (evlistener)
	      return evlistener.length;
	  }
	  return 0;
	};

	EventEmitter.listenerCount = function(emitter, type) {
	  return emitter.listenerCount(type);
	};

	function isFunction(arg) {
	  return typeof arg === 'function';
	}

	function isNumber(arg) {
	  return typeof arg === 'number';
	}

	function isObject(arg) {
	  return typeof arg === 'object' && arg !== null;
	}

	function isUndefined(arg) {
	  return arg === void 0;
	}


/***/ }),
/* 7 */
/***/ (function(module, exports) {

	// Source: http://jsfiddle.net/vWx8V/
	// http://stackoverflow.com/questions/5603195/full-list-of-javascript-keycodes

	/**
	 * Conenience method returns corresponding value for given keyName or keyCode.
	 *
	 * @param {Mixed} keyCode {Number} or keyName {String}
	 * @return {Mixed}
	 * @api public
	 */

	exports = module.exports = function(searchInput) {
	  // Keyboard Events
	  if (searchInput && 'object' === typeof searchInput) {
	    var hasKeyCode = searchInput.which || searchInput.keyCode || searchInput.charCode
	    if (hasKeyCode) searchInput = hasKeyCode
	  }

	  // Numbers
	  if ('number' === typeof searchInput) return names[searchInput]

	  // Everything else (cast to string)
	  var search = String(searchInput)

	  // check codes
	  var foundNamedKey = codes[search.toLowerCase()]
	  if (foundNamedKey) return foundNamedKey

	  // check aliases
	  var foundNamedKey = aliases[search.toLowerCase()]
	  if (foundNamedKey) return foundNamedKey

	  // weird character?
	  if (search.length === 1) return search.charCodeAt(0)

	  return undefined
	}

	/**
	 * Get by name
	 *
	 *   exports.code['enter'] // => 13
	 */

	var codes = exports.code = exports.codes = {
	  'backspace': 8,
	  'tab': 9,
	  'enter': 13,
	  'shift': 16,
	  'ctrl': 17,
	  'alt': 18,
	  'pause/break': 19,
	  'caps lock': 20,
	  'esc': 27,
	  'space': 32,
	  'page up': 33,
	  'page down': 34,
	  'end': 35,
	  'home': 36,
	  'left': 37,
	  'up': 38,
	  'right': 39,
	  'down': 40,
	  'insert': 45,
	  'delete': 46,
	  'command': 91,
	  'left command': 91,
	  'right command': 93,
	  'numpad *': 106,
	  'numpad +': 107,
	  'numpad -': 109,
	  'numpad .': 110,
	  'numpad /': 111,
	  'num lock': 144,
	  'scroll lock': 145,
	  'my computer': 182,
	  'my calculator': 183,
	  ';': 186,
	  '=': 187,
	  ',': 188,
	  '-': 189,
	  '.': 190,
	  '/': 191,
	  '`': 192,
	  '[': 219,
	  '\\': 220,
	  ']': 221,
	  "'": 222
	}

	// Helper aliases

	var aliases = exports.aliases = {
	  'windows': 91,
	  '⇧': 16,
	  '⌥': 18,
	  '⌃': 17,
	  '⌘': 91,
	  'ctl': 17,
	  'control': 17,
	  'option': 18,
	  'pause': 19,
	  'break': 19,
	  'caps': 20,
	  'return': 13,
	  'escape': 27,
	  'spc': 32,
	  'pgup': 33,
	  'pgdn': 34,
	  'ins': 45,
	  'del': 46,
	  'cmd': 91
	}


	/*!
	 * Programatically add the following
	 */

	// lower case chars
	for (i = 97; i < 123; i++) codes[String.fromCharCode(i)] = i - 32

	// numbers
	for (var i = 48; i < 58; i++) codes[i - 48] = i

	// function keys
	for (i = 1; i < 13; i++) codes['f'+i] = i + 111

	// numpad keys
	for (i = 0; i < 10; i++) codes['numpad '+i] = i + 96

	/**
	 * Get by code
	 *
	 *   exports.name[13] // => 'Enter'
	 */

	var names = exports.names = exports.title = {} // title for backward compat

	// Create reverse mapping
	for (i in codes) names[codes[i]] = i

	// Add aliases
	for (var alias in aliases) {
	  codes[alias] = aliases[alias]
	}


/***/ }),
/* 8 */
/***/ (function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function(module) {/*!
	 * @name JavaScript/NodeJS Merge v1.2.0
	 * @author yeikos
	 * @repository https://github.com/yeikos/js.merge

	 * Copyright 2014 yeikos - MIT license
	 * https://raw.github.com/yeikos/js.merge/master/LICENSE
	 */

	;(function(isNode) {

		/**
		 * Merge one or more objects 
		 * @param bool? clone
		 * @param mixed,... arguments
		 * @return object
		 */

		var Public = function(clone) {

			return merge(clone === true, false, arguments);

		}, publicName = 'merge';

		/**
		 * Merge two or more objects recursively 
		 * @param bool? clone
		 * @param mixed,... arguments
		 * @return object
		 */

		Public.recursive = function(clone) {

			return merge(clone === true, true, arguments);

		};

		/**
		 * Clone the input removing any reference
		 * @param mixed input
		 * @return mixed
		 */

		Public.clone = function(input) {

			var output = input,
				type = typeOf(input),
				index, size;

			if (type === 'array') {

				output = [];
				size = input.length;

				for (index=0;index<size;++index)

					output[index] = Public.clone(input[index]);

			} else if (type === 'object') {

				output = {};

				for (index in input)

					output[index] = Public.clone(input[index]);

			}

			return output;

		};

		/**
		 * Merge two objects recursively
		 * @param mixed input
		 * @param mixed extend
		 * @return mixed
		 */

		function merge_recursive(base, extend) {

			if (typeOf(base) !== 'object')

				return extend;

			for (var key in extend) {

				if (typeOf(base[key]) === 'object' && typeOf(extend[key]) === 'object') {

					base[key] = merge_recursive(base[key], extend[key]);

				} else {

					base[key] = extend[key];

				}

			}

			return base;

		}

		/**
		 * Merge two or more objects
		 * @param bool clone
		 * @param bool recursive
		 * @param array argv
		 * @return object
		 */

		function merge(clone, recursive, argv) {

			var result = argv[0],
				size = argv.length;

			if (clone || typeOf(result) !== 'object')

				result = {};

			for (var index=0;index<size;++index) {

				var item = argv[index],

					type = typeOf(item);

				if (type !== 'object') continue;

				for (var key in item) {

					var sitem = clone ? Public.clone(item[key]) : item[key];

					if (recursive) {

						result[key] = merge_recursive(result[key], sitem);

					} else {

						result[key] = sitem;

					}

				}

			}

			return result;

		}

		/**
		 * Get type of variable
		 * @param mixed input
		 * @return string
		 *
		 * @see http://jsperf.com/typeofvar
		 */

		function typeOf(input) {

			return ({}).toString.call(input).slice(8, -1).toLowerCase();

		}

		if (isNode) {

			module.exports = Public;

		} else {

			window[publicName] = Public;

		}

	})(typeof module === 'object' && module && typeof module.exports === 'object' && module.exports);
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(9)(module)))

/***/ }),
/* 9 */
/***/ (function(module, exports) {

	module.exports = function(module) {
		if(!module.webpackPolyfill) {
			module.deprecate = function() {};
			module.paths = [];
			// module.parent = undefined by default
			module.children = [];
			module.webpackPolyfill = 1;
		}
		return module;
	}


/***/ }),
/* 10 */
/***/ (function(module, exports, __webpack_require__) {

	'use strict';

	__webpack_require__(11);

	module.exports = {

	  /**
	   *
	   * @param {Element} element
	   * @param {string} className
	   */
	  addClass: function addClass(element, className) {
	    var re = new RegExp('(^|\\s)' + className + '(\\s|$)', 'g');
	    if (re.test(element.className)) return;
	    element.className = (element.className + ' ' + className).replace(/\s+/g, ' ').replace(/(^ | $)/g, '');
	  },

	  /**
	   *
	   * @param {Element} element
	   * @param {string} className
	   * @returns {boolean}
	   */
	  hasClass: function (element, className) {
	    return element.matches('.' + className);
	  },

	  /**
	   *
	   * @param {Element} element
	   * @param {string} className
	   */
	  removeClass: function removeClass(element, className) {
	    var re = new RegExp('(^|\\s)' + className + '(\\s|$)', 'g');
	    element.className = element.className.replace(re, '$1').replace(/\s+/g, ' ').replace(/(^ | $)/g, '');
	  },

	  /**
	   * Removes current node from tree.
	   * @param {Node} node
	   */
	  removeNode: function removeNode(node) {
	    if (node.parentNode)
	      node.parentNode.removeChild(node);
	  },

	  /**
	   *
	   * @param {string} html
	   * @returns {Node}
	   */
	  createHTML: function createHTML(html) {
	    var div = document.createElement('div');
	    div.innerHTML = html.trim();
	    return div.firstChild;
	  },

	  /**
	   * Adds coordinates to event object independently of event from touching or mouse. (cx, cy - client coordinates, px, py - page coordinates)
	   * @param event
	   */
	  extendEventObject: function extendEventObject(event) {
	    if (event.touches && event.touches[0]) {
	      event.cx = event.touches[0].clientX;
	      event.cy = event.touches[0].clientY;
	      event.px = event.touches[0].pageX;
	      event.py = event.touches[0].pageY;
	    }
	    else if (event.changedTouches && event.changedTouches[0]) {
	      event.cx = event.changedTouches[0].clientX;
	      event.cy = event.changedTouches[0].clientY;
	      event.px = event.changedTouches[0].pageX;
	      event.py = event.changedTouches[0].pageY;
	    }
	    else {
	      event.cx = event.clientX;
	      event.cy = event.clientY;
	      event.px = event.pageX;
	      event.py = event.pageY;
	    }
	  }
	};

/***/ }),
/* 11 */
/***/ (function(module, exports) {

	'use strict';

	if (!Element.prototype.matches) {
	  Element.prototype.matches =
	    Element.prototype.matchesSelector ||
	    Element.prototype.mozMatchesSelector ||
	    Element.prototype.msMatchesSelector ||
	    Element.prototype.oMatchesSelector ||
	    Element.prototype.webkitMatchesSelector ||
	    function (s) {
	      var matches = (this.document || this.ownerDocument).querySelectorAll(s),
	          i       = matches.length;
	      while (--i >= 0 && matches.item(i) !== this) {
	        // empty
	      }
	      return i > -1;
	    };
	}

/***/ }),
/* 12 */
/***/ (function(module, exports) {

	'use strict';

	Object.defineProperty(exports, "__esModule", {
	  value: true
	});
	exports.default = {

	  /**
	   *
	   * @param {number} percent
	   * @param {number} max
	   * @param {number} [min = 0]
	   * @returns {number}
	   */
	  calcValueByPercent: function calcValueByPercent(percent, max) {
	    var min = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : 0;

	    return min + (max - min) * percent / 100;
	  },

	  /**
	   *
	   * @param {number[]} value - array of two numbers which represent min and max values of slider.
	   * @param {number} min - the minimum allowed value.
	   * @param {number} max - the maximum allowed value.
	   * @param {number} step - step between allowed numbers.
	   * @param {boolean} [allowSameValue = true] - allow min and max values be the same. It is `false` for range slider.
	   * @param {boolean} [minIsForeground = true] - min value (value[0]) is foreground.
	   *                                            It is mean that if this argument is `true` and max value (value[1]) is less than min value,
	   *                                            max value will be recalculated to be the same or greater than min value.
	   *                                            If it is `false` min value will be recalculated regarding the max value.
	   * @returns {number[]}
	   */
	  fixValue: function fixValue(value, min, max, step) {
	    var allowSameValue = arguments.length > 4 && arguments[4] !== undefined ? arguments[4] : true;
	    var minIsForeground = arguments.length > 5 && arguments[5] !== undefined ? arguments[5] : true;

	    for (var i = 0; i < value.length; i++) {

	      var minAllowed = !allowSameValue && i == 1 ? min + step : min;
	      var maxAllowed = !allowSameValue && i == 0 ? max - step : max;
	      var val = Math.max(minAllowed, Math.min(maxAllowed, value[i]));
	      //find nearest stepped value
	      value[i] = this.getSteppedNumber(val, min, step);
	    }

	    if (minIsForeground) {
	      // max range value can not be less than min range value
	      var minVal = allowSameValue ? value[0] : value[0] + step;
	      value[1] = Math.max(minVal, value[1]);
	    } else {
	      // min range value can not be greater than max range value
	      var maxVal = allowSameValue ? value[1] : value[1] - step;
	      value[0] = Math.min(value[0], maxVal);
	    }

	    // round all values
	    value = value.map(this.roundValue);

	    return value;
	  },

	  /**
	   * Round single value up to 10 decimal positions
	   * @param {number} num - a number to round
	   * @returns {number}
	   */
	  roundValue: function roundValue(num) {
	    return +num.toFixed(10);
	  },

	  /**
	   * Returns stepped number.
	   * @param {number} num
	   * @param {number} min
	   * @param {number} step
	   * @returns {number}
	   */
	  getSteppedNumber: function getSteppedNumber(num, min, step) {
	    var steps = (num - min) / step;
	    var leftSteppedVal = min + Math.floor(steps) * step;
	    var rightSteppedVal = min + Math.ceil(steps) * step;
	    var leftDiff = Math.abs(leftSteppedVal - num);
	    var rightDiff = Math.abs(rightSteppedVal - num);

	    return rightDiff <= leftDiff ? rightSteppedVal : leftSteppedVal;
	  },

	  /**
	   * Returns position of the handle's center in container.
	   * @param {Element} handleElement
	   * @param {Element} container
	   * @returns {{x: number, y: number}}
	   */
	  getHandlePosition: function getHandlePosition(handleElement, container) {
	    var bounds = handleElement.getBoundingClientRect();
	    var containerBounds = container.getBoundingClientRect();

	    return {
	      x: (bounds.left + bounds.right) / 2 - containerBounds.left,
	      y: (bounds.top + bounds.bottom) / 2 - containerBounds.top
	    };
	  },

	  /**
	   *
	   * @param {number} val
	   * @param {number} max
	   * @param {number} [min = 0]
	   * @returns {number}
	   */
	  getPercent: function getPercent(val, max) {
	    var min = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : 0;

	    return Math.min(100, Math.max(0, 100 * (val - min) / (max - min)));
	  },

	  /**
	   * Sets attribute with `attrName` to passed element if `attrVal` is not empty otherwise remove this attribute.
	   * @param {Element} element
	   * @param {string} attrName
	   * @param {string} [attrVal]
	   */
	  setAttributeOrRemoveIfEmpty: function setAttributeOrRemoveIfEmpty(element, attrName) {
	    var attrVal = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : '';

	    if (attrVal) {
	      element.setAttribute(attrName, attrVal);
	    } else {
	      element.removeAttribute(attrName);
	    }
	  },

	  /**
	   * Removes all `parent` children
	   * @param {Element} parent
	   */
	  removeChildElements: function removeChildElements(parent) {
	    if (!parent || parent.tagName === 'HTML') {
	      return;
	    }

	    while (parent.lastChild) {
	      parent.removeChild(parent.lastChild);
	    }

	    return parent;
	  }
	};

/***/ })
/******/ ])
});
;
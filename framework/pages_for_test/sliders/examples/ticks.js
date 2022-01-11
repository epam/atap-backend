(function () {
  new CgSlider({
    container: 'ticks_slider',
    max: 5,
    step: 0.2,
    initialValue: 2.2,
    ariaLabel: 'slider with ticks',
    ticks: true
  });

  new CgSlider({
    container: 'custom_ticks_slider',
    max: 15,
    initialValue: 5,
    ariaLabel: 'slider with custom ticks',
    ticks: function (tick, currentStep, offsetPercent) {
      if ([1, 4, 6, 9, 11, 14].indexOf(currentStep) > -1) {
        return false;
      }

      if (currentStep % 5 === 0) {
        tick.style.height = '10px';
        tick.style.marginTop = '-4px';
        tick.style.backgroundColor = 'black';
      }
    }
  });
})();
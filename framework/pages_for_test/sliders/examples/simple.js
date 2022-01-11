(function () {
  var valueElement = document.getElementById('sliderValue');
  var slider = new CgSlider({
    container: 'slider',
    initialValue: 50,
    ariaLabel: 'slider'
  });

  slider.on(CgSlider.EVENTS.CHANGE, function (value) {
//    console.log('changed to:', value);
    updateValue();
  });
  updateValue();

  function updateValue() {
    valueElement.innerHTML = slider.value;
  }
})();
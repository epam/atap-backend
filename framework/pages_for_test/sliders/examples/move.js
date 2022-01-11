(function () {
  var valueElement = document.getElementById('sliderValue_steps');
  var slider = new CgSlider({
    container: 'slider_steps',
    initialValue: 50,
    ariaLabel: 'slider'
  });
  document.querySelector('#stepBack').addEventListener('click', function () {
    slider.move(-5);
  });

  document.querySelector('#stepForward').addEventListener('click', function () {
    slider.move(10);
  });

  slider.on(CgSlider.EVENTS.CHANGE, function (value) {
    updateValue();
  });
  updateValue();

  function updateValue() {
    valueElement.innerHTML = slider.value;
  }
})();
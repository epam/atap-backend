(function () {
  var eventsLog = document.getElementById('events_log');
  var slider = new CgSlider({
    min: 0,
    max: 10,
    container: 'events_slider',
    initialValue: 2
  });

  slider.on(CgSlider.EVENTS.CHANGE, function (value) {
    pushToLog(CgSlider.EVENTS.CHANGE, value);
  });

  slider.on(CgSlider.EVENTS.START_CHANGE, function (value) {
    pushToLog(CgSlider.EVENTS.START_CHANGE, value);
  });
  slider.on(CgSlider.EVENTS.STOP_CHANGE, function (value) {
    pushToLog(CgSlider.EVENTS.STOP_CHANGE, value);
  });

  function pushToLog(eventName, value) {
    var log = document.createElement('div');
    var logContent = 'Emitted <b>\'' + eventName + '\'</b> event';

    if (typeof value !== 'undefined') {
      logContent += ' with value: <b>' + value + '</b>';
    }

    log.innerHTML = logContent;
    eventsLog.appendChild(log);

    // scroll to bottom
    eventsLog.scrollTop = eventsLog.scrollHeight;
  }

})();
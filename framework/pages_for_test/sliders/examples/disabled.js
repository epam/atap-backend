(function () {
    var switcher = document.getElementById('switcher');
    var slider = new CgSlider({
        container: 'disabled_slider',
        initialValue: 50,
        disabled: true
    });

    switcher.addEventListener('change', function () {
        slider.disabled = !this.checked;
    });

})();
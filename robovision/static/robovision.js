function setSource(key, type) {
    var camera = '#camera__' + key;
    if (type == undefined) {
        $(camera).attr("src", "");
        return;
    }
    var url = "/" + type + "/" + key;
    if ($(camera).attr("src") != url) {
        $(camera).attr("src", "");
        $(camera).attr("src", url);
    }
}

function setColor(values) {
    var channel = this.target.dataset.channel;
    var query = "LOWER=" + values[0] + "&UPPER=" + values[1] + "&channel=" + channel;
    $.ajax({
        url: "/config/camera/" + this.target.id,
        type: 'POST',
        data: query
    });
}

var sliders = $(".no-ui-slider").find(".slider");
for (var i = 0; i < sliders.length; i++) {
    var min = parseInt(sliders[i].getAttribute("data-min"));
    var max = parseInt(sliders[i].getAttribute("data-max"));
    var start = parseInt(sliders[i].getAttribute("data-start"));
    var end = parseInt(sliders[i].getAttribute("data-end"));
    noUiSlider.create(sliders[i], {
        start: [start, end],
        behaviour: 'drag',
        animate: false,
        step: 1,
        connect: true,
        tooltips: true,
        range: {'min': min, 'max': max},
        format: {
            to: function (value) {
                return Math.round(value);
            },
            from: function (value) {
                return value;
            }
        }
    });
    sliders[i].noUiSlider.on('change', setColor);
}


function updateStatus() {
    var data = {"action":"gamepad"};
    for (j in controllers) {
        var controller = controllers[j];
        data[j] = {'button': {}, 'axis': {}};
        for (var i = 0; i < controller.buttons.length; i++) {
            var val = controller.buttons[i];
            var pressed = val == 1.0;
            if (typeof(val) == "object") {
                pressed = val.pressed;
                val = val.value;
            }
            data[j]['button'][i] = [pressed, val];
        }
        for (var i = 0; i < controller.axes.length; i++) {
            data[j]['axis'][i] = controller.axes[i];
        }


    }
    return JSON.stringify(data);
}

function scangamepads() {
    var gamepads = navigator.getGamepads ? navigator.getGamepads() : (navigator.webkitGetGamepads ? navigator.webkitGetGamepads() : []);
    for (var i = 0; i < gamepads.length; i++) {
        if (gamepads[i]) {
            controllers[gamepads[i].index] = gamepads[i];
        }
    }
}


function probe_server() {
    setTimeout(probe_server, 1000);
    var probe = new WebSocket(socked_addr);
    probe.onopen = function (event) {
        location.reload();
    }
}

var controllers = {};
var running = false;
const socked_addr = "ws://"+document.domain + ':' + (parseInt(location.port)+1);

$(document).ready(function () {

    console.log(' websocket loop start!!!!!!!!!!!', window.location.host)

    socket = new WebSocket(socked_addr);

    function send_data() {
        if (running){
            scangamepads();
            var status = updateStatus();
            socket.send(status);
            window.requestAnimationFrame(send_data);
        }
    };

    socket.onopen = function (event) {
        console.log("connected");
        running = true;
        window.requestAnimationFrame(send_data);
    };
    
    socket.onerror = function (error) {
        console.log('WebSocket Error: ');
        running = false;
        console.log(error);
        probe_server();
    };
    
    socket.onclose = function (event) {
        console.log(event);
        running = false;
        probe_server();         

    };
    

    $("#toggle_recording").click(function() {
        if ($("#toggle_recording").html().indexOf("Rec") >= 0) {
          $("#toggle_recording").html("Disable recording");
          $.get("http://192.168.12.107:5000/record/enable/");
          socket.send(JSON.stringify({"action":"record_enable"}));
//          socket.send(JSON.stringify({"action":"record_enable"}));
        } else {
          $("#toggle_recording").html("Record");
          $.get("http://192.168.12.107:5000/record/disable/");
          socket.send(JSON.stringify({"action":"record_disable"}));
        }
    });  
});


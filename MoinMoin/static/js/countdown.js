var state = 0; // 0: start; 1: long count; 2: short count; 3: timeout; 4/5: blink
var counter = 0, step = 1, delay = 1;

function countdown() {
    // change state if counter is down
    if (counter <= 1) {
        state += 1
        if (state == 1) {
            counter = countdown_timeout_min
            step = 1
            delay = 60000
        }
        if (state == 2) {
            counter = 60
            step = 5
            delay = step * 1000
        }
        if (state == 3 || state == 5) {
            window.status = countdown_lock_expire
            state = 3
            counter = 1
            step = 1
            delay = 500
        }
        if (state == 4) {
            // blink the above text
            window.status = " "
            counter = 1
            delay = 250
        }
    }

    // display changes
    if (state < 3) {
        var msg
        if (state == 1) msg = countdown_lock_mins
        if (state == 2) msg = countdown_lock_secs
        window.status = msg.replace(/#/, counter)
    }
    counter -= step

    // Set timer for next update
    setTimeout("countdown()", delay);    
}


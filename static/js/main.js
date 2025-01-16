const terminal = new Terminal({
    cursorBlink: true,
    cursorStyle: "underline",
    cursorInactiveStyle: "underline",
    theme: {
        background: '#000000',
        foreground: '#ffffff',
    },
});
terminal.open(document.getElementById('terminal'));

let inputBuffer = '';
const promptSymbol = '~$ ';

terminal.write(promptSymbol);

const socket = io();

const bellSound = new Audio(bellSoundPath);

String.prototype.hexEncode = function(){
    var hex, i;

    var result = "";
    for (i=0; i<this.length; i++) {
        hex = this.charCodeAt(i).toString(16);
        result += ("000"+hex).slice(-4);
    }

    return result
}

terminal.onData(data => {
    if (data === '\r') {
        terminal.write('\r\n');
        socket.emit('input', { command: inputBuffer });
        inputBuffer = '';
    } else if (data === '\u007F') {
        if (inputBuffer.length > 0) {
            inputBuffer = inputBuffer.slice(0, -1);
            terminal.write('\b \b');
        } else {
            bellSound.currentTime = 0;
            bellSound.play();
        }
    } else {
        inputBuffer += data;
        terminal.write(data);
    }
});

socket.on('output', data => {
    terminal.write(data.output);
});
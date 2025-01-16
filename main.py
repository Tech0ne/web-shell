from flask import Flask, render_template, request
from flask_socketio import SocketIO
import subprocess
import threading
import os
import pty

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)

SHELLS = {}

class InteractiveBash:
    def __init__(self):
        self.master_fd, self.slave_fd = pty.openpty()
        self.process = subprocess.Popen(
            ["bash", "-i"],
            stdin=self.slave_fd,
            stdout=self.slave_fd,
            stderr=self.slave_fd,
            text=True,
            bufsize=0,
        )
        self.running = True
        self.output_lock = threading.Lock()
        self.output = []
        self.last_command = ""

        self.output_thread = threading.Thread(target=self._read_output, daemon=True)
        self.output_thread.start()

    def _read_output(self):
        while self.running:
            try:
                output = os.read(self.master_fd, 1024).decode()
                if output:
                    if self.last_command and output.startswith(self.last_command):
                        self.last_command = ""
                        continue
                    with self.output_lock:
                        self.output.append(output)
            except OSError:
                break

    def send_input(self, command: str):
        self.last_command = command
        os.write(self.master_fd, (command + '\n').encode())

    def get_output(self):
        with self.output_lock:
            combined_output = ''.join(self.output)
            self.output.clear()
        return combined_output

    def close(self):
        self.running = False
        self.process.terminate()
        self.process.wait()
        os.close(self.master_fd)
        os.close(self.slave_fd)

def emit_bash_outputs(bash: InteractiveBash, event: threading.Event, user):
    while not event.is_set():
        output = bash.get_output()
        if output:
            socketio.emit('output', {'output': output}, to=user)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def start_bash_communication():
    global SHELLS
    user = request.sid
    if SHELLS.get(user) is not None:
        return
    bash = InteractiveBash()
    bash.send_input("clear")
    event = threading.Event()
    thread = threading.Thread(target=emit_bash_outputs, args=(bash, event, user), daemon=True)
    thread.start()
    SHELLS[user] = (bash, event, thread)

@socketio.on('disconnect')
def stop_bash_communication():
    global SHELLS
    user = request.sid
    if SHELLS.get(user) is None:
        return
    bash, event, thread = SHELLS[user]
    event.set()
    bash.close()
    thread.join()
    del SHELLS[user]

@socketio.on('input')
def handle_input(data):
    user = request.sid
    command = data.get('command', '').strip()
    if SHELLS.get(user) is None:
        return
    bash = SHELLS[user][0]
    bash.send_input(command)

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0")
import datetime
import multiprocessing
import os
import select
import subprocess
import sys
import time
import re


def pipe_file_object():
    a, b = os.pipe()
    return os.fdopen(a), os.fdopen(b, 'w')


server_log_message_regex = re.compile(r'\[(\d\d:\d\d:\d\d)\] \[([^]]*)\]: (.*)')
chat_message_regex = re.compile(r'[[<]([^\]]+)[\]>] (.*)')


class Server:
    """
    The minecraft server wrapper class.
    """
    def __init__(self, server_jar, jvm_args=('-Xms1G', '-Xmx8G', '-jar'),
                 jvm_exec='java', server_args=('nogui',)):
        self.server_process = None
        self.args = list((jvm_exec,) + jvm_args + (server_jar,) + server_args)
        self.backup_process = None
        self.cpu_process = None
        self.event_sources = [sys.stdin]
        self.event_handlers = {
                sys.stdin.fileno(): self.handle_stdin,
        }

    def add_event_source(self, file, handler):
        self.event_handlers[file.fileno()] = handler
        self.event_sources.append(file)

    def remove_event_source(self, file):
        del self.event_handlers[file.fileno()]
        self.event_sources.remove(file)

    def add_popen_as_event_source(self, popen, stdout_handler=None, stderr_handler=None):
        if (popen.stdout is not None and stdout_handler is not None):
            self.add_event_source(popen.stdout, stdout_handler)

        if (popen.stderr is not None and stderr_handler is not None):
            self.add_event_source(popen.stderr, stderr_handler)

    def remove_popen_as_event_source(self, popen):
        if (popen.stdout is not None and popen.stdout.fileno() in self.event_handlers):
            self.remove_event_source(popen.stdout)

        if (popen.stderr is not None and popen.stderr.fileno() in self.event_handlers):
            self.remove_event_source(popen.stderr)

    def backup_data(self):
        """
        Backs up the server folder somewhere.
        """
        pass

    def print_cpu_usage(self):
        """
        Checks current CPU usage of the server using `top` and prints it.
        """
        self.cpu_process = subprocess.Popen(
            ['top', '-pid', str(self.server_process.pid), '-l2', '-stats', 'CPU'],
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            universal_newlines=True,
        )
        self.add_popen_as_event_source(self.cpu_process, self.handle_cpu_use)

    def say_to_chat(self, message):
        """
        Sends a given message to the game chat using the say command.
        """
        print("say", message, file=self.server_process.stdin)
        self.server_process.stdin.flush()

    def log_string_to_out(self, message, file, level='Wrapper'):
        """
        Logs a string to given file in minecraft server logging format.
        """
        time = datetime.datetime.now().strftime("%H:%M:%S")
        print("[{}] [{}]: {}".format(time, level, message), file=file)

    def handle_stdin(self, stream):
        line = stream.readline()
        line_str = line.strip()
        if line_str[0] == "!":
            self.process_command(line_str[1:])
        else:
            self.server_process.stdin.write(line)
            self.server_process.stdin.flush()

    def handle_server_out(self, stream):
        line = stream.readline().strip()
        out_stream = sys.stdout if stream == self.server_process.stdout else sys.stderr
        print(line, file=out_stream)
        if not line:
            return
        match = server_log_message_regex.match(line)
        if match:
            time = match.group(1)
            logger = match.group(2)
            message = match.group(3)
            self.process_log_message(logger, message)
        else:
            print("Log message:", line, "Doesn't match", file=sys.stderr)

    def handle_cpu_use(self, stream):
        lines = [line for line in stream]
        cpu_use = lines[-1].strip()
        cpu_use_float = float(cpu_use)
        if cpu_use_float > 80:
            self.say_to_chat("CPU usage is too high: {}%!".format(cpu_use))
        else:
            self.say_to_chat("CPU Usage: {}".format(cpu_use))
        self.remove_popen_as_event_source(self.cpu_process)

    def process_log_message(self, logger, message):
        """
        Processes the log message.
        """
        if logger == "Server thread/WARN":
            self.say_to_chat(message)
        elif logger == "Server thread/INFO":
            match = chat_message_regex.match(message)
            if match:
                nickname = match.group(1)
                chat_msg = match.group(2)
                if chat_msg[0] == '!':
                    self.process_command(chat_msg[1:])

    def process_command(self, command):
        if command == "cpu":
            self.print_cpu_usage()

    def run(self):
        """
        Starts the server subprocess and the polling loop.
        """
        self.server_process = subprocess.Popen(
                self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
        )
        self.add_popen_as_event_source(
                self.server_process,
                self.handle_server_out,
                self.handle_server_out,
        )
        while self.server_process.poll() is None:
            try:
                events, _, _ = select.select(self.event_sources, [], [], 10)
                for stream in events:
                    self.event_handlers[stream.fileno()](stream)
            except KeyboardInterrupt:
                self.server_process.send_signal(subprocess.signal.SIGINT)


if __name__ == "__main__":
    srv = Server('minecraft_server.1.13.2.jar')
    srv.run()

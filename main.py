import multiprocessing
import os
import select
import subprocess
import sys
import time


def pipe_file_object():
    a, b = os.pipe()
    return os.fdopen(a), os.fdopen(b, 'w')


class Server:
    """
    The minecraft server wrapper class.
    """
    def __init__(self, server_jar, jvm_args=('-Xms1G', '-Xmx8G', '-jar'),
                 jvm_exec='java', server_args=('nogui',)):
        self.server_process = None
        self.args = list((jvm_exec,) + jvm_args + (server_jar,) + server_args)

    def backup_data(self):
        """
        Backs up the server folder somewhere.
        """
        pass


    def print_cpu_usage(self):
        """
        Checks current CPU usage of the server using `top` and print it.
        """
        pass


    def run(self):
        """
        Starts the server subprocess and the polling loop.
        """
        self.server_process = subprocess.Popen(
                self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
        )
        while self.server_process.poll() is None:
            try:
                events, _, _ = select.select([self.server_process.stdout, self.server_process.stderr, sys.stdin], [], [], 10)
                for event in events:
                    if event == sys.stdin:
                        line = sys.stdin.readline()
                        self.server_process.stdin.write(line)
                        self.server_process.stdin.flush()
                    elif event == self.server_process.stdout:
                        sys.stdout.write(self.server_process.stdout.readline())
                    elif event == self.server_process.stderr:
                        sys.stderr.write(self.server_process.stderr.readline())
            except KeyboardInterrupt:
                self.server_process.send_signal(subprocess.signal.SIGINT)

if __name__ == "__main__":
    srv = Server('minecraft_server.1.13.2.jar')
    srv.run()

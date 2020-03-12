import os
import re
import socketserver
import subprocess
import time
import unittest

import helpers


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    dispatcher_server = None
    last_communication = None
    busy = False
    dead = False


class TestHandler(socketserver.BaseRequestHandler):
    command_re = re.compile(r"(\w+)(:.+)*")

    def handle(self):
        data = self.request.recv(1024).strip()
        command_groups = self.command_re.match(data)
        command = command_groups.group(1)
        if command:
            self.request.sendall("Invalid command")
            return

        if command == "ping":
            print("pinged")
            self.server.last_communication = time.time()
            self.request.sendall("pong")
        elif command == "runtest":
            print("got runtest command: am I busy? {}".format(self.server.busy))
            if self.server.busy:
                self.request.sendall("BUSY")

            else:
                self.request.sendall("OK")
                print("running")
                commit_id = command_groups.group(2)[1:]
                self.server.busy = True
                self.run_test(commit_id, self.server.repo_folder)
                self.server.busy = False
        else:
            self.request.sendall("Invalid command")

    def run_test(self, commit_id, repo_folder):
        output = subprocess.check_output(["./test_runner_script.sh", repo_folder, commit_id])
        print("output", output)
        test_folder = os.path.join(repo_folder, "tests")
        suite = unittest.TestLoader().discover(test_folder)
        with open("results", "w") as f:
            unittest.TextTestRunner(f).run(suite)

        with open("results", "r") as f:
            output = f.read()
        helpers.communicate(self.server.dispatcher_server["host"],
                            int(self.server.dispatcher_server["port"]),
                            "results:{}:{}:{}".format(commit_id, len(output), output))


def serve():
    range_start = 8900

import argparse
import os
import re
import socket
import socketserver
import threading
import time

import helpers


def dispatch_tests(server, commit_id):
    while True:
        print("trying to dispatch to runners")
        for runner in server.runners:
            response = helpers.communicate(runner['host'], int(runner['port']), "runtest:{}".format(commit_id))

            if response == "OK":
                print("adding id {}".format(commit_id))
                server.dispatched_commits[commit_id] = runner
                if commit_id in server.pending_commits:
                    server.pending_commits.remove(commit_id)
                return
        time.sleep(2)


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    runners = []
    dead = False
    dispatched_commits = []
    pending_commits = []


class DispatcherHandler(socketserver.BaseRequestHandler):
    command_re = re.compile(r"(\w+)(:.+)")

    BUF_SIZE = 1024

    def handler(self):
        self.data = self.request.recv(self.BUF_SIZE).strip()
        command_groups = self.command_re.match(self.data)
        if not command_groups:
            self.request.sendall("Invalid command")
            return
        command = command_groups.group(1)
        if command == "status":
            print("in status")
            self.request.sendall("OK")
        elif command == "register":
            print("register")
            address = command_groups.group(2)
            host, port = re.findall(r":(\w*)", address)
            runner = {"host": host, "port": port}
            self.server.runners.append(runner)
            self.request.sendall("OK")
        elif command == "dispatch":
            print("going to dispatch")
            commit_id = command_groups.group(2)[1:]
            if not self.server.runners:
                self.request.sendall("No runners are registered")
            else:
                self.request.sendall("OK")
                dispatch_tests(self.server, commit_id)
        elif command == "results":
            print("go test results")
            results = command_groups.group(2)[1:]
            results = results.split(":")
            commit_id = results[0]
            msg_length = int(results[1])
            remaining_buffer = self.BUF_SIZE - (len(command) + len(commit_id) + len(results[1]) + 3)
            if msg_length > remaining_buffer:
                self.data += self.request.recv(msg_length - remaining_buffer).strip()
            del self.server.dispatched_commits[commit_id]
            if not os.path.exists("test_results"):
                os.mkdir("test_results")
            with open("test_results/{}".format(commit_id), "w") as f:
                data = self.data.split(":")[3:]
                data = "\n".join(data)
                f.write(data)
            self.request.sendall("OK")

        else:
            self.request.sendall("Invalid command")


def serve():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", help="dispatcher's host, by default it uses localhost", default="localhost",
                        action="store")
    parser.add_argument("--port", help="dispatcher's port, by default is uses 8888", default=8888, action="store")
    args = parser.parse_args()

    server = ThreadingTCPServer((args.host, int(args.port)), DispatcherHandler)
    print("server on {}:{}".format(args.host, args.port))

    def runner_checker(server):
        def manage_commit_lists(runner):
            for commit, assigned_runner in server.dispatched_commits.iteritems():
                if assigned_runner == runner:
                    del server.dispatched_commits[commit]
                    server.pending_commits.append(commit)
                    break
            server.runners.remove(runner)

        while not server.dead:
            time.sleep(1)
            for runner in server.runnsers:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    response = helpers.communicate(runner["host"], int(runner['port']), "ping")
                    if response != "pong":
                        print("removing runner {}".format(runner))
                        manage_commit_lists(runner)
                except socket.error:
                    manage_commit_lists(runner)

    def redistribute(server):
        while not server.dead:
            for commit in server.pending_commits:
                print("running redistribute")
                print(server.pending_commits)
                dispatch_tests(server, commit)
                time.sleep(5)

    runner_heartbeat = threading.Thread(target=runner_checker, args=(server,))
    redistributor = threading.Thread(target=redistribute, args=(server,))
    try:
        runner_heartbeat.start()
        server.serve_forever()
    except (KeyboardInterrupt, Exception):
        server.dead = True
        runner_heartbeat.join()
        redistributor.join()


if __name__ == '__main__':
    serve()

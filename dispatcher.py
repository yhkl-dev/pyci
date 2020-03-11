import helpers
import socket
import os
import re
import threading
import time
import socketserver


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


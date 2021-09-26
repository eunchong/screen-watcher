from datetime import datetime
import os
import time
import socket
import argparse
import textwrap
import collections

from tabulate import tabulate
import psutil

from .slack import send_slack_msg
from .models import get_pinfo_list, update_pinfo


class Worker:
    tree = None
    screen_pids = None
    running_pids = None

    def __init__(self):
        self.tree = collections.defaultdict(list)
        self.screen_pids = set()
        self.running_pids = set()

    # traverse processes tree
    def traverse(self, parent, indent=""):
        try:
            p = psutil.Process(parent).as_dict(
                attrs=[
                    "cwd",
                    "exe",
                    "pid",
                    "name",
                    "ppid",
                    "cmdline",
                    "environ",
                    "terminal",
                    "username",
                    "create_time",
                ]
            )

        except psutil.Error:
            p = {}

        pid = p.get("pid", None)
        name = p.get("name", None)
        cmdline = p.get("cmdline", [])
        environ = p.get("environ", None)

        if not (name == "screen" or cmdline == ["/bin/bash"]):
            is_created = update_pinfo(p)
            self.running_pids.add(pid)

        if parent not in self.tree:
            return
        children = self.tree[parent][:-1]
        for child in children:
            self.traverse(child, indent + "| ")
        child = self.tree[parent][-1]
        self.traverse(child, indent + "  ")

    def run(self):
        # construct a dict where 'values' are all the processes
        # having 'key' as their parent
        for p in psutil.process_iter():
            try:
                self.tree[p.ppid()].append(p.pid)
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                pass
            # on systems supporting PID 0, PID 0's parent is usually 0
            if p.name() == "screen":
                self.screen_pids.add(p.pid)

        # traverse screen child processes
        for p in self.screen_pids:
            self.traverse(p)

        # find terminated process
        for pinfo in get_pinfo_list(only_running=True):
            if pinfo.pid not in self.running_pids:
                update_pinfo(pinfo.as_dict(), False)

                # alert slack message
                if os.environ.get("SLACK_BOT_TOKEN"):

                    msg = (
                        "*screen process terminated*\n"
                        + f"`{pinfo.cmdline}`\n"
                        + "```"
                        + f"username : {pinfo.username}\n"
                        + f"hostname : {socket.gethostname()}\n"
                        + f"sty      : {pinfo.environ.get('STY', None) if pinfo.environ else None}\n"
                        + f"cwd      : {pinfo.cwd}\n"
                        + "```\n"
                        + datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                    )

                    send_slack_msg(
                        os.environ.get("SLACK_BOT_CHANNEL", "screen-watcher"), msg
                    )


def main():
    parser = argparse.ArgumentParser(description="screen watcher")
    parser.add_argument(
        "--daemon",
        dest="is_daemon",
        action="store_const",
        const=True,
        default=False,
        help="worker daemon (default: print running processes)",
    )
    parser.add_argument(
        "--all",
        dest="only_running",
        action="store_const",
        const=False,
        default=True,
        help="all processes (default: only running process)",
    )
    parser.add_argument(
        "--json",
        dest="is_json",
        action="store_const",
        const=True,
        default=False,
        help="print json format (default: tabulate)",
    )
    parser.add_argument(
        "--cmd",
        dest="is_cmd",
        action="store_const",
        const=True,
        default=False,
        help="print cmd format (default: tabulate)",
    )

    args = parser.parse_args()

    if args.is_daemon:
        while True:
            Worker().run()
            time.sleep(10)

    else:
        Worker().run()

        headers = [
            "pid",
            "ppid",
            "username",
            "sty",
            "name",
            "cwd",
            "cmdline",
            "updated_at",
            "status",
        ]
        rows = []
        for pinfo in get_pinfo_list(only_running=args.only_running):
            if args.is_json:
                print(pinfo.as_dict())
                continue

            if args.is_cmd:
                print("cd %s;%s" % (pinfo.cwd, pinfo.cmdline))
                continue

            row = [
                pinfo.pid,
                pinfo.ppid,
                pinfo.username,
                pinfo.environ.get("STY", None) if pinfo.environ else None,
                pinfo.name,
                pinfo.cwd,
                textwrap.fill(pinfo.cmdline, width=48) if pinfo.cmdline else None,
                pinfo.updated_at,
                str(pinfo.status),
            ]
            rows.append(row)

        if not args.is_json and not args.is_cmd:
            print(tabulate(rows, headers=headers, tablefmt="grid"))


if __name__ == "__main__":
    main()

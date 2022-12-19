#!/usr/bin/env -S python
import os
import re
import time
from datetime import datetime, timedelta, timezone
import subprocess as sp
from typing import *
from dataclasses import dataclass
from argparse import ArgumentParser

def do_cmd(cmd):
    return sp.check_output(cmd, shell=True).decode("utf-8")

@dataclass
class TODO:
    file: str
    line: int
    text: str
    author: str
    timestamp: timedelta

# returns author, delta
def get_blame_info(path: str, line: int) -> (str, timedelta):
    blamed = do_cmd(f"git blame --incremental -L{line},{line} {path}")

    data = {}
    for line in list(filter(len, blamed.split("\n")))[1:]:
        key, *values = line.split()
        data[key] = values[0] if len(values) == 1 else " ".join(values)

    tz = timezone(timedelta(hours=int(data["author-tz"][:-2])))
    blametime = datetime.fromtimestamp(int(data["author-time"]), tz)
    dt = datetime.now(tz) - blametime

    return (data["author"], dt)

def find_todos(path: str) -> list[TODO]:
    if not os.path.isdir(path):
        print("error: path is not the location of a valid directory.")
        exit(1)

    # grep for todos
    grepped = do_cmd(f"grep -rn TODO {path}")

    todos = []
    for line in grepped.split("\n"):
        if len(line) == 0 or line.isspace():
            continue

        # convert to todo object
        matches = re.split(r":", line, maxsplit=2)
        if matches == None:
            print("error: match failed on grep output")
            exit(1)

        file, linenum, text = matches
        linenum = int(linenum)
        author, stamp = get_blame_info(file, linenum)

        todos.append(TODO(file, linenum, text, author, stamp))

    return todos

def sort_todos(todos: list[TODO]) -> list[TODO]:
    return list(sorted(todos, key=lambda todo: todo.timestamp))

def readable(dt: timedelta) -> str:
    date = [
        ("weeks", dt.days // 7),
        ("days", dt.days % 7),
        ("hours", dt.seconds // 3600),
        ("minutes", (dt.seconds % 3600) // 60),
        ("seconds", dt.seconds % 60)
    ]

    formatted = []
    for k, v in date:
        if v > 0:
            formatted.append(f"{v} {k}")

    return ", ".join(formatted) + " ago"

def display_todos(todos: list[TODO]):
    code = lambda c: f"\x1b[{c}m"

    for todo in todos:
        print(f"{code(35)}{todo.file}:{todo.line}{code(0)}: ", end='')
        print(f"<{code(32)}{todo.author}{code(0)}> ", end='')
        print(f"{code(34)}{readable(todo.timestamp)}{code(0)}")
        print(f"{todo.text}\n")

def parse_args():
    # read args
    parser = ArgumentParser(
        prog="blame-me",
        description="list TODOs within a directory indexed by git and when " \
                  + "they were written."
    )
    parser.add_argument("<path>")

    args = vars(parser.parse_args())

    return {
        "path": args["<path>"]
    }

def main():
    args = parse_args()

    todos = find_todos(args["path"])
    todos = sort_todos(todos)
    display_todos(todos)

if __name__ == "__main__":
    main()
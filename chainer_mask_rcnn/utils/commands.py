#!/usr/bin/env python

import os
import subprocess


def git_hash(filename=None):
    if filename is None:
        cwd = None
    else:
        cwd = os.path.dirname(os.path.abspath(filename))
    cmd = 'git log -1 --format="%h"'
    return subprocess.check_output(cmd, shell=True, cwd=cwd).decode().strip()

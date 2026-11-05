"""Local workaround for PyCharm's package-list helper on Unicode Windows paths.

Only the IDE packaging helper is affected; application streams are unchanged.
Remove this file to undo the workaround.
"""
import os
import sys

if os.path.basename(sys.argv[0]) == "packaging_tool.py":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

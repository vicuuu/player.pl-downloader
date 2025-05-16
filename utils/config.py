import os
from functools import partial

for p in ["output"]:
    os.makedirs(p, exist_ok=True)

CONFIG = {
    "WVD_FILE": "device.wvd",
    "UA": "Mozilla/5.0 ...",
    "THREADS": {"SCRAPER": 4},
    "OUTPUT": {
        "DIR": "media",
        "TMP": "tmp",
        "CMD_FILE": "output/cmds.txt",
        "FAILED_FILE": "output/cmds_failed.txt"
    },
    "CMD": {
        "JOIN": "&",
        "CLOSE": "exit",
        "TERMINAL": partial('start /wait cmd /k "{command}"'.format)
    },
    "TOOL": {
        "BASE": (
            'N_m3u8DL-RE "[!manifest!]" [!keys!] '
            '--save-name "[!element!]"'
        ),
        "KEY": "--key {value}"
    },
    "MESSAGES": {"INFO": "[INFO] {msg}", "WARN": "[WARNING] {msg}"},
    "PLAYREADY_ID": "9A04F079-9840-4286-AB92-E65BE0885F95"
}

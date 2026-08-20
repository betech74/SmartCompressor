import os
import subprocess


def hidden_process_kwargs():
    """Paramètres pour lancer un programme Windows sans fenêtre console."""
    if os.name != "nt":
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE

    return {
        "creationflags": subprocess.CREATE_NO_WINDOW,
        "startupinfo": startupinfo,
    }

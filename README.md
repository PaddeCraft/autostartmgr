# Autostartmgr

This is a simple cross-platform per-user autostart manager.

## How to install

First, install the package using pipx or pip. Then, run `asmgrd &` on linux to start it, e.g. by putting it in your bspwmrc of any other file launched on login. For windows, put a batch file running `start /b asmgrd` in your autostart folder (%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup or shell:startup).

## asmgrctl

The main command. Run `asmgrctl --help` for help.

## asmgrd

The start command for the daemon. Only to be execute once per boot.

## ToDo

- Implement startup orders
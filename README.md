# aiidalab-dev
Development utilities for AiiDAlab

This package helps with the development of `aiidalab` and `aiidalab-home`
packages by installing them in a sandboxed development environment in `~/local/`.

**NOTE**: This package is meant to be run inside the AiiDAlab Docker stack
and expects the `aiidalab` package to be already installed.

To install, execute
```console
pip install git+https://github.com/aiidalab/aiidalab-dev
```
To use, execute
```console
$ develop-aiidalab --help
Usage: develop-aiidalab [OPTIONS] COMMAND [ARGS]...

  Manage the AiiDAlab development environment.

Options:
  --local-prefix PATH
  --help               Show this message and exit.

Commands:
  restore  Restore the system configuration of the home app.
  setup    Set up the AiiDAlab environment for development.
  status   Show current status of the AiiDAlab environment.
```

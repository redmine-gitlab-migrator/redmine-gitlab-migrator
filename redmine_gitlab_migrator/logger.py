import sys
import logging


def setup_logging(log, level=None):
    console_handler = logging.StreamHandler(sys.stderr)

    if level is not None:
        log.setLevel(level)
        console_handler.setLevel(level)

    console_handler.setFormatter(
        logging.Formatter("%(levelname)s: %(message)s"))

    log.addHandler(console_handler)


def setup_module_logging(name, level=None, *args, **kwargs):
    """ Sets up module-level logging
    """
    log = logging.getLogger(name, *args, **kwargs)
    setup_logging(log, level=level)
    return log

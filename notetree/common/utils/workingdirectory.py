import os
import contextlib

@contextlib.contextmanager
def working_directory(dir: str):
    prev = os.getcwd()
    os.chdir(dir)

    try:
        yield
    finally:
        os.chdir(prev)

import os

from lib import foo

print("Hello world!", foo())

assert "INPUT_FOLDER" in os.environ
assert "OUTPUT_FOLDER" in os.environ

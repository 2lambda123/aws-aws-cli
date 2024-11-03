import os
import subprocess
import sys
from security import safe_command

RST_GENERATION_SCRIPT = 'htmlgen'
script_path = os.path.join(os.path.dirname(__file__), RST_GENERATION_SCRIPT)
os.environ['PATH'] += ':.'
rc = safe_command.run(subprocess.call, "python " + script_path, shell=True, env=os.environ)
if rc != 0:
    sys.stderr.write("Failed to generate documentation!\n")
    sys.exit(2)

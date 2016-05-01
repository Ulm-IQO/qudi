#!/bin/bash
# based on simple_kernel (https://github.com/dsblank/simple_kernel)
# by Doug Blank <doug.blank@gmail.com>
# placed in the public domain, see
# https://github.com/dsblank/simple_kernel/issues/5

mkdir -p ~/.ipython/kernels/qudikernel/
START_SCRIPT_PATH=$(cd `dirname "${BASH_SOURCE[0]}"` && pwd)/qudikernel.py
PYTHON_PATH=$(which python3)
CONTENT='{
   "argv": ["'${PYTHON_PATH}'", "'${START_SCRIPT_PATH}'", "{connection_file}"],
                "display_name": "QuDi",
                "language": "python"
}'
echo $CONTENT > ~/.ipython/kernels/qudikernel/kernel.json

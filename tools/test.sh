#!/bin/bash

function print_log () {
echo "======== Qudi Logfile ========"
cat qudi.log

if [ -e crash.log ]; then
    echo "======== Qudi Crashfile ========"
    cat crash.log
fi
}

if [[ $(python --version 2>&1) == *"2.7"* ]]; then
    PYCMD=python3
else
    PYCMD=python
fi

$PYCMD start.py &
QUDIPID=$!

sleep 10

if ! kill -0 $QUDIPID; then
    echo "Start has failed: $QUDIPID not here" >&2
    print_log
    exit 1
fi

jupyter-nbconvert --execute notebooks/debug.ipynb
jupyter-nbconvert --execute notebooks/matplotlib.ipynb


if ! kill -0 $QUDIPID; then
    echo "Test run has failed: $QUDIPID not here" >&2
    print_log
    exit 1
fi

jupyter-nbconvert --execute notebooks/shutdown.ipynb

sleep 20

if kill $QUDIPID; then
    echo "Shutdown has failed: $QUDIPID was killed" >&2
    print_log
    exit 1
fi

print_log


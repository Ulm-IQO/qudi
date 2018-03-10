#!/bin/bash

function test_notebook () {
    let "total += 1"
    jupyter-nbconvert --ExecutePreprocessor.timeout=600 --execute $1;
    grep '<div.*output_stderr' "notebooks/"`basename $1 .ipynb`".html" > /dev/null
    retcode=$?

    if ! kill -0 $QUDIPID; then
        echo "Test run has failed: $QUDIPID not here" >&2
        print_log
        exit 1
    fi;

    if [ $retcode -ne 0 ]; then
        return 0;
    else
        let "failed += 1"
        echo "Failed / Total: $failed / $total" >&2
        return 1;
    fi;
}

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

total=0
failed=0

test_notebook notebooks/matplotlib.ipynb

for notebook in notebooks/fit_testing_*.ipynb; do
    test_notebook $notebook;
done

jupyter-nbconvert --execute notebooks/shutdown.ipynb

sleep 60

if kill $QUDIPID; then
    echo "Shutdown has failed: $QUDIPID was killed" >&2
    print_log
    exit 1
fi

grep "^....-..-.. ..:..:.. error" qudi.log > /dev/null
if [ $? -eq 0 ]; then
    let "failed += 1"
fi

print_log

exit $failed


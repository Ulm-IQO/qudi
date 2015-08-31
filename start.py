#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2015 Jan M. Binder jan.binder@uni-ulm.de
"""

import subprocess
import sys
import os

myenv = os.environ.copy()
argv = [sys.executable, '-m', 'core'] + sys.argv[1:]

while True:
    process = subprocess.Popen(argv, close_fds=False, env=myenv, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr, shell=False)
    try:
        retval = process.wait()
        if retval == 0:
            break
        elif retval == 42:
            print('Restarting...')
            continue
        else:
            print('Unexpected return value {0}. Exiting.'.format(retval))
            sys.exit(retval)
    except KeyboardInterrupt:
        print('Keyboard Interrupt, quitting!')
        break
    except:
        process.kill()
        process.wait()
        raise

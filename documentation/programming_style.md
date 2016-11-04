# Programming and code formatting style  {#programming-style}

## Source code formatting

Your source code should be encoded in UTF-8 and declare the encoding

    # -*- coding: utf-8 -*-

Use American English while programming.

Indentation steps should be 4 spaces wide, Python 3.x forbids mixing of space and tab indentation.

Lines should be a maximum of 100 characterss wide, 99 usable characters and the line feed
(\\n) character.
If you need to break a line, do so inside a pair of brackets where it is fine to do so.
DO NOT use the backslash line continuation, we have had too many problems with that.

Variable names are lower case with underscores as word separators, except for GUI code which can also
use Qt formatting.

Class names should be in CamelCase.

File names need to be lowercase with underscores as word separators.
Qt .ui files are prefixed with ui\_ and generally named like the Python file that loads them.

Typical abbreviations used for imported modules:
 * daq: PyDAQMx
 * mpl: matplotlib
 * np: numpy
 * pg: pyqtgraph
 * plt: matplotlib.pyplot

 In general, follow [PEP8](https://www.python.org/dev/peps/pep-0008/).

## Program structure

There are some very general guidelines given in
[PEP20](https://www.python.org/dev/peps/pep-0020/).

Especially in this codebase, please try to refrain from abusing the more complex
features of Python, even something as simple as lambdas tends to scare Physicists
and other natural science people.


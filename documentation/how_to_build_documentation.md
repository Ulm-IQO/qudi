# How to build the documentation  {#build-docs}

This project comes with included documentation in Markdown format which is [available online](http://qosvn.physik.uni-ulm.de/qudi-docs).
To browse the documentation in a web browser, a HTML version needs to be built with Doxygen,
which will also extract class and function documentation from the Python source.

## Prerequisites
You need [Doxygen](http://stack.nl/~dimitri/doxygen) to build the documentation
and [doxypypy](https://github.com/Feneric/doxypypy) to preprocess the Python source code.

Just install Doxygen from your distribuiton repository and doxypypy with pip (take care to install this for Python 3.x).
Then add a py_filter script to your PATH as described in the doxypypy documentation.

## Build documentation 

Now you can run doxygen documentaton/doxyfile which creates the folder documentation/generated and subfolders.

## Browse documentation

Just open documentation/generated/html/index.html in a web browser.


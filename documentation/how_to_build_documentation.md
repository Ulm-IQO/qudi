# How to build the documentation  {#build-docs}

This project comes with included documentation in Markdown format which is
[available online](https://ulm-iqo.github.io/qudi-generated-docs/html-docs/index.html).
To browse the documentation in a web browser, a HTML version needs to be built with Doxygen,
which will also extract class and function documentation from the Python source.

## Prerequisites
You need [Doxygen](http://stack.nl/~dimitri/doxygen) to build the documentation
and [doxypypy](https://github.com/Feneric/doxypypy) to preprocess the Python source code.

Just install Doxygen from your distribuiton repository and doxypypy with pip (take care to install this for Python 3.x).
Then add a py_filter script to your PATH as described in the doxypypy documentation.

You need to clone the image repository into the documentation folder, like this:
´git clone https://github.com/Ulm-IQO/qudi-docs-images documentation/images´

## Build documentation 

Now you can run doxygen documentaton/doxyfile which creates the folder ´documentation/generated´ and subfolders.
Afterwards, copy the ´documentation/images´ folder to ´documentation/generated/html-docs/images´

## Browse documentation

Just open documentation/generated/html/index.html in a web browser.


Installation			{#installation}
============

PyDAQmx fix
-----------

The original PyDAQmx module in version 1.3.1 has a bug in it, that inhibits our software from running. If you install it with pip and then run qudi, you will get a “wrong argument type” error close to something where it is written +'InternalOutput'.

The problem is, that the PyDAQmx does not handle the C const char \*data correctly.

To fix it, you need to change the file DAQmxFunctions.py in the folder: \Lib\site-packages\PyDAQmx

`In line 150 add an additional regular expression for const_char_etoile`
`In line 163 add this const_char_etoile to the c_to_ctype_map variable`

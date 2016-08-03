How to use and understand a config file  {#config-explanation}
===============

Config files are essential in our software, since they tell basically which
modules you want to connect to each other. The config file is also the place
where needed parameters can be saved individually for a module of you needs.

Each module is defined in a predetermined category i.e. in

   - global,
   - hardware,
   - logic or
   - gui.

These categories (all except global) are folders in the trunk
directory of our software.

Let's have a look on an example scenario of an (incomplete) configuration:

    hardware:
        <identifier>:
            module.Class: '<foldername>.<filename>.<classname>'
            attribute_string_example:   'example_text'
            attribute_int_example:      12345
            attribute_float_example:    1.234
            attribute_boolean_example:  True
            attribute_list_example:     ['first', 'second']


    logic:
        <identifier-other>:
            module.Class: '<foldername2>.<filename2>.<classname2>'
            attribute1: 'assigned_value1'
            connect:
                <keyword_in1>: '<identifier>.<keyword_out1>'

    gui:
        <identifier-other2>:
            module.Class: '<foldername3>.<filename3>.<classname3>'
            attribute1: 'assigned_value1'
            connect:
                <keyword_in2>: '<identifier-other>.<keyword_out2>'

Each of this categories contains an `<identifier>`, i.e.
a name which is used for a module. This identifier is relevant in order to
separate and distinguish between the different modules. The `<identifier>`
represents a reference to the constructed object of the module. Therefore the
keyword `module.Class` indicates the path to the construction class.

For instance:
In the category `hardware` you can specify the attribute `module.Class` in the
`<identifier>` as

    module.Class: 'ni_card.NICard'

which will determine that the module will be found in the trunk folder in the
folder structure:

    \trunk\hardware\ni_card.py

where the class `NICard` should be situated within the file `ni_card.py`.

Within the construction class, connectors ( `_in` and `_out`) must be declared.
These connectors will allow other modules to attach to it
(via the `_in` connectors) and/or allow the specific module to be connected to
something else (via the `_out` connectors).

Therefore, gui modules have by definition **only `_in` connectors**, since
different logic outputs (`_out` connectors) can be 'plugged' into the gui. Due
to the same idea, hardware modules can **only have `_out` connectors**, which have
to be 'plugged' into logic modules. As a result, the logic modules can have
both, `_in` or `_out` connectors.

The connector is defined as follows:
Within a class, the connector is saved in a dictionary type, e.g.

    class <classname2>(...):
    ...
        _in  = {'<keyword_in1>' : '<itemname1>'}
        _out = {'<keyword_out2>': '<itemname2>'}

meaning that it has a `<keyword>` and an `<item>`. Only the `<keywords>` for
the `_in` connector will appear in the `connect` attribute of the `<identifier-other>`
module. (See above in the configuration example).
To this `_in` connectors you can plug in other modules, which are represented by an
`<identifier-other>`. After the `<identifier-other>` the keyword `<keyword-out3>`
from the module with the `_out` connector, has to follow.


Note that `<keyword_out3>` has to be declared as `_out` connector in the class
`<classname>` like:

    class <classname>(...):
        ...
        _out = { '<keyword_out1>' : '<itemname3>'}

Consequently the class `<classname2>` has to have the `_in` connector definition
like stated above.

The names `<itemname>`, `<itemname2>` and `<itemname3>` can be chosen freely,
but for consistency reasons, we have chosen the following definition:

* `_out` connectors of the hardware classes should have the name of the interfaces through
which you can access that hardware object as their itemnames,
e.g. for a microwave source this would be `'MicrowaveInterface'`.
* Consequently, the itemnames of `_in` connectors in the logic files should also have interface names.
* The itemnames of the `_out` connectors in the Logic should be called after the present logic classname.
* The itemnames of the `_in` connector in the GUI should be called after the logic class, which should be attached to it.


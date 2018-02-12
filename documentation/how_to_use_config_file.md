# How to use and understand a config file  {#config-explanation}

Config files are essential in our software, since they tell basically which
modules you want to connect to each other. The config file is also the place
where the required parameters are specified individually for a module.

## YAML implementation in Qudi

Our config file uses the [YAML](http://yaml.org/) format, a data serialization format designed for
human readability and interaction with scripting languages. Qudi modifies the
ruamel.yaml implementation, which serves as a YAML parser. Therefore Qudi has
implemented a loader and a dumper using an collections.OrderedDict() instead of
the regular python dict() used by ruamel.yaml.
Additionally, it fixes a bug in ruamel.yaml with scientific notation and allows
to dump numpy.dtypes and numpy.ndarrays.

## Example of a config file

Each module is defined in a predetermined category i.e. in

   - global,
   - hardware,
   - logic or
   - gui.

These categories (all except global) are folders in the trunk
directory of our software.

Let's have a look on an example scenario of an (incomplete) configuration:
```yaml
hardware:
    <identifier>:
        module.Class: '<foldername>.<filename>.<classname>'
        attribute_string_example:   'example_text'
        attribute_int_example:      12345
        attribute_float_example:    1.234
        attribute_boolean_example:  True
        attribute_list_example:
                                - 'first'
                                - 'second'
                                - 'another'
        attribute_list_floats:
                                - -200.0    # the second minus belongs to the number
                                - 0.0
                                - 200.0


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
```

Each of this categories contains an `<identifier>`, i.e.
a name which is used for a module. This identifier is relevant in order to
separate and distinguish between the different modules. The `<identifier>`
represents a reference to the constructed object of the module. Therefore the
keyword `module.Class` indicates the path to the construction class in pythonic
notation (directory separated by points).

For instance:
In the category `hardware` you can specify the attribute `module.Class` in the
`<identifier>` as

```yaml
module.Class: 'ni_card.NICard'
```

which will determine that the module will be found in the trunk folder in the
folder structure:

    hardware/ni_card.py

where the class `NICard` should be situated within the file `ni_card.py`.

## Connectors

A connector is a way for the Qudi manager to give a module access to other modules.

The general rule for this is that logic modules can only have a connector that gives access
to hardware modules or other logic modules and GUI modules can only access logic modules.

To create a Connector, declare it as a class variable in the module like this:

```python
class <classname2>(...):
...
    <connector name> = Connector(interface='<InterfaceForThisConnector>')
    <another connector name> = Connector(interface='<InterfaceForTheOtherConnector>')
```

A reference to the connected module can then be obtained at runtime by:

```python
<connected module> = self.get_connector('<connector name>')
<antother connected module> = self.get_connector('<another connector name>')
```


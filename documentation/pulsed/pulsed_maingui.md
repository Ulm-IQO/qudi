# Structure of Pulsed Main GUI {#pulsed_maingui}


## General File structure

Each Tab of the PulsedMainGui is configured in a spatially separated part within
the file pulsed_maingui.py. The different parts are declare with such a comment
heading structure (here exemplarily shown for the Settings for the 'Pulse Generator' Tab ):

    ###########################################################################
    ###     Methods related to Settings for the 'Pulse Generator' Tab:      ###
    ###########################################################################


The interaction to other file parts will be hold to a minimum. Therefore all
methods defined below such a header should as far as possible to interaction
with other methods, which are not related to this tab.

Somethings it is not possible to keep the interaction separate, because an
establishment of interaction is actually desired. For Maintainability reasons,
these interactions will be still kept to an minimum.


## Idea of Pulsed Main GUI interaction with PulsedMeasurementLogic and SequenceGeneratorLogic

make access via get and set functions.

## Explanation of specific Methods and general concept of object usage

### Usage of QTableWidgets

In general a table consist out of an object for viewing the data and of an
object where the data are saved. For viewing the data, there is the general
QWidgetView class and for holding/storing the data you have to define a model.

The model ensures to hold your data in the proper data type and give the
possibility to separate the data from the display.
The QTableWidget class is a specialized class to handle user input into an
table. In order to handle the data, it contains already a model (due to that
you can e.g. easily add rows and columns and modify the content of each cell).
Therefore the model of a QTableWidget is a private attribute and cannot be
changed externally. If you want to define a custom model for QTableWidget you
have to start from a QTableView and construct your own data handling in the
model.

Since QTableWidget has all the (nice and) needed requirements for us, a
custom definition of QTableView with a Model is not needed.

### Customize Delegate Methods for QTableWidget

The delegation is a procedure, where you a new or another constructor and viewer
will be assigned to QWidget objects.

Here the constructor and viewer for entries in a QTableWidget will be altered
by using customized Delegation.

A general idea, which functions are customizable for our purpose is displayed in
the documentation for the
[QItemDelegate Class](http://pyqt.sourceforge.net/Docs/PyQt4/qitemdelegate.html "QItemDelegate Class Reference"),
which is worth reading!

If you want to delegate a row or a column of a QTableWidget, then you have
at least to declare the constructors and the modification function for the
displayed data (which you see in the table) and the saved data (which is
handeled by the model class of the table). That means your delegate should
at least contain the functions:

   - createEditor
   - setEditor
   - updateEditorGeometry
   - setModelData

I.e. when editing data in an item view, editors are created and displayed by
a delegate.

Use the
[QStyledItemDelegate class](http://pyqt.sourceforge.net/Docs/PyQt4/qstyleditemdelegate.html "QStyledItemDelegate Class Reference"),
instead of
[QItemDelegate class](http://pyqt.sourceforge.net/Docs/PyQt4/qitemdelegate.html "QItemDelegate Class Reference"),
since the first one provides extended possibilities of painting the windows and can be
changed by Qt style sheets.

Since the delegate is a subclass of QItemDelegate or QStyledItemDelegate, the
data it retrieves from the model and is displayed in a default style, and we do
not need to provide a custom paintEvent().
We use QStyledItemDelegate as our base class, so that we benefit from the
default delegate implementation. We could also have used
[QAbstractItemDelegate class](http://pyqt.sourceforge.net/Docs/PyQt4/qabstractitemdelegate.html "QAbstractItemDelegate Class Reference"),
if we had wanted to start completely from scratch.

Examples how to create e.g. of SpinBoxdelegate in native Qt:
http://qt.developpez.com/doc/4.7/itemviews-spinboxdelegate/
and a similar python implementation:
https://github.com/PySide/Examples/blob/master/examples/itemviews/spinboxdelegate.py


### How are the mathematical functions displayed in the Block Editor

Relate that to the method get_func_config from the sequence generator logic


### How are the table widgets being created, configured and arranged

The columns for the Table Widgets are determined by the present `channel_config`
obtained from the hardware constraints and the `add_pbe_param`
( = additional Pulse_Block_Element Parameter) and `add_pb_param`
( = additional Pulse_Block Parameters) dictionary in the logic.

How the configuration is eventually arranged in the GUI in the QTableWidgets
will be told in the dictionary `cfg_param_pbe` ( = configuration Parameter for
Pulse_Block_Element objects) and `cfg_param_pb` ( = configuration Parameter for
Pulse_Block objects). These dictionaries are written from the GUI to the Logic
in order to have a standardized way for obtaining and saving the display
configuration.

**These set of dictionaries will and should handle all needed information. Moreover
it is a way to centralize the configuration to a small set of configuration
dictionaries and avoid the establishment of various obscure cross relationship
between Logic and GUI variables!**

`cfg_param_pbe` and `cfg_param_pb` are abstract dictionary, which tells the
logic the configuration of a Pulse_Block_Element, i.e. how many parameters are
used for a Pulse_Block_Element (pbe) object (in the GUI). In principle, the way
how the GUI is displaying the pbe object should be irrelevant for the logic
(which is guaranteed by these abstract dictionaries)!

Parameters to create all needed rows for analog channels are taken from the
`get_func_config` method from the Logic, where the biggest desired function will
be taken for the input of the analog parameters. The biggest function can be
changed in the Settings of the Block Generation.

### Influence of Channel_config and activation_map on the GUI

The GUI asks for the hardware constraints in order to obtain all parameters in
`channel_config`. The available channel configuration will determine the display
for the Pulse Block Editor.

By pressing the `Pulser On` or `Pulser Off` button, or starting the Pulse
Experiment with the Start Button in the ToolBar, the `pulser_on_clicked` or
`pulser_on_clicked` method will pass those channel to the Logic, which should be
activated or deactivated, according to the selected activation map.

The activation map can also be chosen in the Settings of Block Generation (which
is basically dictated by the hardware). The hardware will state all possible
activation and deactivation scenarios for the corresponding channels.
Note, that the `activation_map` parameter is **substantially different** from the
`channel_config` parameter (both parameters can be found in the dictionary which
the GUI obtains from the Logic, by asking for the hardware constraints).

The activation map is the additional information, you will need for several
pulsing devices. See more information about these parameters in the explanation
of the [Pulser Interface](@ref pulser_interface).



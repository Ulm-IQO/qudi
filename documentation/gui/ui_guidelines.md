# User Interface (GUI) Design Concept {#uiguidelines}

The Qudi suite of tools should have a unified interface concept.  It is important for conceptually different interface elements to be visually separated, and for similar elements to appear in the same (ie the expected) place across all Qudi modules.

## The Problem of Precedence

Many of the initial users of Qudi will be familiar with similar tools from DiQo, and may expect the new tools to be laid out in a similar "familiar" fashion.  However, not all of the interfaces for the old software were carefully and intentionally designed.  The argument of precedence ("but that's the way it was in the old software...") is therefore not a strong one.

## General GUI design guidelines

* There should be as few Main Windows as possible.  Dock widgets allow sub-tools or specific functions to be hidden away when not in use, and this flexibility prevents the need for every specific tool to be its own Main Window interface.
  * **EVERY** dock widget should have its own entry in a "View" menu. [This can be implemented in a standard way through QT Designer](@ref viewmenu).
* All user actions (such as scan, save, stop, optimise position, zoom, set POI, etc) should live in toolbars.  There can be multiple toolbars to help categorise these actions.
  * _Where should the toolbars be by default?  Top or Left or Top+Left?_
* There are three places to put user-adjustable "settings".  These should be used sensibly:
  * Display settings (such as color-bar scaling) should be in the dock widget with the display graph.
  * Often-used experiment control parameters (such as the scan ranges in Confocal) should go in a Control dock-widget.
  * _When is it better to use a Settings sub-window?_

## GUI element naming

Technically all GUI elements (such as `QSpinBox`, `QPushButton`, etc) are classes.  That's why they have those CamelCase names!  However, for readability we want fairly long and clear names for all our GUI elements.  We will therefore adopt a naming convention which has a lower-case description with underscores, finishing in the CammelCaps element type.

~~~~~~~~~~~~~{.py}
# GUI element names should have the form 
a_readable_name_ElementType

# Some examples:
roi_cb_max_SpinBox
view_poi_editor_Action
sample_shift_DockWidget
~~~~~~~~~~~~~

The trailing ElementType also increases readability when using functions of these classes, for example:

~~~~~~~~~~~~~{.py}
roi_cb_manual_RadioButton.setChecked(True)
~~~~~~~~~~~~~

A very frequent need when building UI is the need to have a QtObject, like spinbox or checkbox, matching an attribute
of the logic.
The Mapper class in core.mapper can help do just that.
 
Example :
~~~~~~~~~~~~~{.py}
self.mapper.add_mapping(self.lineedit, self.logic_module, 'some_value', 'some_value_changed')
~~~~~~~~~~~~~
For more detail, please refer to the class documentation or
look at an example in counter GUI.
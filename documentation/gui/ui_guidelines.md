# User Interface (GUI) Design Concept {#uiguidelines}

The QuDi suite of tools should have a unified interface concept.  It is important for conceptually different interface elements to be visually separated, and for similar elements to appear in the same (ie the expected) place across all QuDi modules.

## The Problem of Precedence

Many of the initial users of QuDi will be familiar with similar tools from DiQo, and may expect the new tools to be laid out in a similar "familiar" fashion.  However, not all of the interfaces for the old software were carefully and intentionally designed.  The argument of precedence ("but that's the way it was in the old software...") is therefore not a strong one.

## General GUI design guidelines

  * There should be as few Main Windows as possible.  Dock widgets allow sub-tools or specific functions to be hidden away when not in use, and this flexibility prevents the need for every specific tool to be its own Main Window interface.
    * EVERY dock widget should have its own entry in a "View" menu.  [[log:lachlan:2015:06:2015-06-24-ljr#constructing_view_menu_for_docks_using_qt_desiner|This can be implemented in a standard way through QT Designer]].
  * All user actions (such as scan, save, stop, optimise position, zoom, set POI, etc) should live in toolbars.  There can be multiple toolbars to help categorise these actions.
    * //Where should the toolbars be by default?  Top or Left or Top+Left?//
  * There are three places to put user-adjustable "settings".  These should be used sensibly:
    * Display settings (such as color-bar scaling) should be in the dock widget with the display graph.
    * Often-used experiment control parameters (such as the scan ranges in Confocal) should go in a Control dock-widget.
    * //When is it better to use a Settings sub-window?//

## GUI element naming

Technically all GUI elements (such as QSpinBox, QPushButton, etc) are classes.  That's why they have those CammelCaps names!  However, for readability we want fairly long and clear names for all our GUI elements.  We will therefore adopt a naming convention which has a lower-case description with underscores, finishing in the CammelCaps element type.

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

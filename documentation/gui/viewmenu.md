# Constructing View menu for docks using Qt Desiner {#viewmenu}

Dock Widgets have their own toggleViewAction, but this is not directly visible in QT Designer.
To make it more future-tracable we want to have all the GUI elements constructed in QT Designer rather than some elements added in by code.

It is possible to construct the View menu, but it is a bit convoluted.  Here are the steps:

- Create a dock widget and give it a name `dock_widget_name`.
- Create a menu called View.
- Create an action in the View menu.  It usually makes sense for this action to have its text set to `Dock_widget_name`.
- For coding clarity, set the objectName for this action to `dock_widget_name_view_Action`.
- Set this action "checkable" and "checked".
- Now switch to the Signal/Slot Editor in QT Designer.  We need to connect the menu action to the dock widget visibility.
- Create a new entry with the following values:
  - Sender: `dock_widget_name_view_action` 
  - Signal: `triggered(bool)`
  - Receiver: `dock_widget_name_dockWidget` (the actual objectName of the dock widget)
  - Slot: `setVisible(bool)`
- Since the Dock Widget can be closed without using this menu, we need to connect back the other way to update the menu action.  Create a second new entry with the following values:
  - Sender: `dock_widget_name_dockWidget`
  - Signal: `visibilityChanged(bool)`
  - Receiver: `dock_widget_name_view_Action`
  - Slot: `setChecked(bool)`


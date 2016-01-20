<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainWindow</class>
 <widget class="QMainWindow" name="MainWindow">
  <property name="geometry">
   <rect>
    <x>0</x>
    <y>0</y>
    <width>800</width>
    <height>844</height>
   </rect>
  </property>
  <property name="windowTitle">
   <string>qudi: Slow Counter</string>
  </property>
  <widget class="QWidget" name="centralwidget"/>
  <widget class="QMenuBar" name="menubar">
   <property name="geometry">
    <rect>
     <x>0</x>
     <y>0</y>
     <width>800</width>
     <height>30</height>
    </rect>
   </property>
   <widget class="QMenu" name="menuView">
    <property name="title">
     <string>&amp;View</string>
    </property>
    <widget class="QMenu" name="menuToolbars">
     <property name="title">
      <string>&amp;Toolbars</string>
     </property>
     <addaction name="counting_controls_view_Action"/>
    </widget>
    <addaction name="pid_view_Action"/>
    <addaction name="pid_parameters_view_Action"/>
    <addaction name="separator"/>
    <addaction name="menuToolbars"/>
    <addaction name="separator"/>
    <addaction name="restore_default_view_Action"/>
   </widget>
   <addaction name="menuView"/>
  </widget>
  <widget class="QStatusBar" name="statusbar"/>
  <widget class="QDockWidget" name="pid_trace_DockWidget">
   <property name="windowTitle">
    <string>Slow &amp;counter</string>
   </property>
   <attribute name="dockWidgetArea">
    <number>4</number>
   </attribute>
   <widget class="QWidget" name="dockWidgetContents">
    <layout class="QGridLayout" name="gridLayout">
     <item row="0" column="0">
      <widget class="QLabel" name="process_value_Label">
       <property name="font">
        <font>
         <pointsize>60</pointsize>
         <weight>75</weight>
         <bold>true</bold>
        </font>
       </property>
       <property name="text">
        <string>0</string>
       </property>
       <property name="alignment">
        <set>Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter</set>
       </property>
      </widget>
     </item>
     <item row="1" column="0" colspan="3">
      <widget class="PlotWidget" name="trace_PlotWidget"/>
     </item>
     <item row="0" column="2">
      <widget class="QLabel" name="control_value_Label">
       <property name="font">
        <font>
         <pointsize>60</pointsize>
         <weight>75</weight>
         <bold>true</bold>
        </font>
       </property>
       <property name="text">
        <string>0</string>
       </property>
       <property name="alignment">
        <set>Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter</set>
       </property>
      </widget>
     </item>
     <item row="0" column="1">
      <widget class="QLabel" name="setpoint_value_Label">
       <property name="font">
        <font>
         <pointsize>60</pointsize>
         <weight>75</weight>
         <bold>true</bold>
        </font>
       </property>
       <property name="text">
        <string>0</string>
       </property>
       <property name="alignment">
        <set>Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter</set>
       </property>
      </widget>
     </item>
    </layout>
   </widget>
  </widget>
  <widget class="QDockWidget" name="pid_parameters_DockWidget">
   <property name="minimumSize">
    <size>
     <width>311</width>
     <height>200</height>
    </size>
   </property>
   <property name="maximumSize">
    <size>
     <width>524287</width>
     <height>200</height>
    </size>
   </property>
   <property name="windowTitle">
    <string>&amp;PID parameters</string>
   </property>
   <attribute name="dockWidgetArea">
    <number>8</number>
   </attribute>
   <widget class="QWidget" name="dockWidgetContents_2">
    <layout class="QGridLayout" name="gridLayout_2">
     <item row="0" column="0">
      <widget class="QLabel" name="labelP">
       <property name="text">
        <string>P</string>
       </property>
      </widget>
     </item>
     <item row="0" column="1">
      <widget class="QSpinBox" name="P_SpinBox">
       <property name="minimum">
        <number>1</number>
       </property>
       <property name="maximum">
        <number>1000000</number>
       </property>
       <property name="singleStep">
        <number>10</number>
       </property>
       <property name="value">
        <number>300</number>
       </property>
      </widget>
     </item>
     <item row="1" column="0">
      <widget class="QLabel" name="labelI">
       <property name="text">
        <string>I</string>
       </property>
      </widget>
     </item>
     <item row="1" column="1">
      <widget class="QSpinBox" name="I_SpinBox">
       <property name="minimum">
        <number>1</number>
       </property>
       <property name="maximum">
        <number>1000000</number>
       </property>
       <property name="singleStep">
        <number>10</number>
       </property>
       <property name="value">
        <number>50</number>
       </property>
      </widget>
     </item>
     <item row="2" column="0">
      <widget class="QLabel" name="labelD">
       <property name="toolTip">
        <string>If bigger than 1, the number of samples is averaged over the given number and then displayed. 
Use for extremely fast counting, since all the raw data is saved. 
Timestamps in oversampling interval are all equal to the averaging time.</string>
       </property>
       <property name="text">
        <string>D</string>
       </property>
      </widget>
     </item>
     <item row="2" column="1">
      <widget class="QSpinBox" name="D_SpinBox">
       <property name="toolTip">
        <string>If bigger than 1, the number of samples is averaged over the given number and then displayed. 
Use for extremely fast counting, since all the raw data is saved. 
Timestamps in oversampling interval are all equal to the averaging time.</string>
       </property>
       <property name="minimum">
        <number>1</number>
       </property>
       <property name="maximum">
        <number>10000</number>
       </property>
       <property name="value">
        <number>1</number>
       </property>
      </widget>
     </item>
    </layout>
   </widget>
  </widget>
  <widget class="QToolBar" name="pid_control_ToolBar">
   <property name="windowTitle">
    <string>Counting Controls</string>
   </property>
   <property name="toolButtonStyle">
    <enum>Qt::ToolButtonTextUnderIcon</enum>
   </property>
   <attribute name="toolBarArea">
    <enum>TopToolBarArea</enum>
   </attribute>
   <attribute name="toolBarBreak">
    <bool>false</bool>
   </attribute>
   <addaction name="start_control_Action"/>
   <addaction name="record_control_Action"/>
  </widget>
  <action name="start_control_Action">
   <property name="checkable">
    <bool>true</bool>
   </property>
   <property name="icon">
    <iconset>
     <normaloff>../../artwork/icons/qudiTheme/22x22/start_counter.png</normaloff>../../artwork/icons/qudiTheme/22x22/start_counter.png</iconset>
   </property>
   <property name="text">
    <string>Start counter</string>
   </property>
   <property name="toolTip">
    <string>Start the counter</string>
   </property>
  </action>
  <action name="record_control_Action">
   <property name="checkable">
    <bool>true</bool>
   </property>
   <property name="icon">
    <iconset>
     <normaloff>../../artwork/icons/qudiTheme/22x22/record_counter.png</normaloff>../../artwork/icons/qudiTheme/22x22/record_counter.png</iconset>
   </property>
   <property name="text">
    <string>Record counts</string>
   </property>
   <property name="toolTip">
    <string>Save count trace to file</string>
   </property>
  </action>
  <action name="pid_view_Action">
   <property name="checkable">
    <bool>true</bool>
   </property>
   <property name="text">
    <string>&amp;Slow counter</string>
   </property>
   <property name="toolTip">
    <string>Show the Slow counter</string>
   </property>
  </action>
  <action name="pid_parameters_view_Action">
   <property name="checkable">
    <bool>true</bool>
   </property>
   <property name="text">
    <string>Slow &amp;counter parameters</string>
   </property>
   <property name="toolTip">
    <string>Show Slow counter parameters</string>
   </property>
  </action>
  <action name="restore_default_view_Action">
   <property name="text">
    <string>&amp;Restore default</string>
   </property>
  </action>
  <action name="counting_controls_view_Action">
   <property name="text">
    <string>&amp;Counting controls</string>
   </property>
  </action>
 </widget>
 <customwidgets>
  <customwidget>
   <class>PlotWidget</class>
   <extends>QGraphicsView</extends>
   <header>pyqtgraph.h</header>
  </customwidget>
 </customwidgets>
 <resources/>
 <connections>
  <connection>
   <sender>pid_view_Action</sender>
   <signal>triggered(bool)</signal>
   <receiver>pid_trace_DockWidget</receiver>
   <slot>setVisible(bool)</slot>
   <hints>
    <hint type="sourcelabel">
     <x>-1</x>
     <y>-1</y>
    </hint>
    <hint type="destinationlabel">
     <x>399</x>
     <y>136</y>
    </hint>
   </hints>
  </connection>
  <connection>
   <sender>pid_trace_DockWidget</sender>
   <signal>visibilityChanged(bool)</signal>
   <receiver>pid_view_Action</receiver>
   <slot>setChecked(bool)</slot>
   <hints>
    <hint type="sourcelabel">
     <x>399</x>
     <y>136</y>
    </hint>
    <hint type="destinationlabel">
     <x>-1</x>
     <y>-1</y>
    </hint>
   </hints>
  </connection>
  <connection>
   <sender>pid_parameters_view_Action</sender>
   <signal>triggered(bool)</signal>
   <receiver>pid_parameters_DockWidget</receiver>
   <slot>setVisible(bool)</slot>
   <hints>
    <hint type="sourcelabel">
     <x>-1</x>
     <y>-1</y>
    </hint>
    <hint type="destinationlabel">
     <x>399</x>
     <y>551</y>
    </hint>
   </hints>
  </connection>
  <connection>
   <sender>pid_parameters_DockWidget</sender>
   <signal>visibilityChanged(bool)</signal>
   <receiver>pid_parameters_view_Action</receiver>
   <slot>setChecked(bool)</slot>
   <hints>
    <hint type="sourcelabel">
     <x>399</x>
     <y>551</y>
    </hint>
    <hint type="destinationlabel">
     <x>-1</x>
     <y>-1</y>
    </hint>
   </hints>
  </connection>
  <connection>
   <sender>counting_controls_view_Action</sender>
   <signal>triggered(bool)</signal>
   <receiver>pid_control_ToolBar</receiver>
   <slot>setVisible(bool)</slot>
   <hints>
    <hint type="sourcelabel">
     <x>-1</x>
     <y>-1</y>
    </hint>
    <hint type="destinationlabel">
     <x>399</x>
     <y>41</y>
    </hint>
   </hints>
  </connection>
  <connection>
   <sender>pid_control_ToolBar</sender>
   <signal>visibilityChanged(bool)</signal>
   <receiver>counting_controls_view_Action</receiver>
   <slot>setChecked(bool)</slot>
   <hints>
    <hint type="sourcelabel">
     <x>399</x>
     <y>41</y>
    </hint>
    <hint type="destinationlabel">
     <x>-1</x>
     <y>-1</y>
    </hint>
   </hints>
  </connection>
 </connections>
</ui>

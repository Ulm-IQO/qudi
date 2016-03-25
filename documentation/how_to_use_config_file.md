How to use and understand a config file  {#config-explanation}
==================

Config files are essential in our software, since they tell basically which
module you want to connect to each other. The config file is also the place 
where needed parameter can be saved individually for a module of you needs.

Each module is defined in a predetermined category i.e. in 
    global, 
    hardware,
    logic or 
    gui. 
These categories (all except global) are folders in the trunk
directory of our software. Each of this categories contain <identifier>, i.e.
a name which is used for a module. This identifier is relevant in order to
separate and distinguish between the different module. The <identifier>  
represents a reference to the construction class of the module. Therefore the 
keyword 'module.Class' indicates the path to the construction class.

For instance:
below the category 'gui', it will be determined, where to find the
construction class for the <identifier> 'confocalgui', it is in
  'confocal.confocalgui.ConfocalGui'
The most right term after the last point represents the <class>.
Consequently, the term before that is the <filename>, containing the class.
All other terms before <filename> represent <foldernames>.
Additional configuration attributes for a module <identifier> can be set
below 'module.Class'. All these attributes will be passed to the init method
for constructing the object, which is represented by <identifier>.
Within the contruction class, connectors (_in and _out) must be declared.
These connectors will allow that other modules can attach to it
(_in connectors) and/or that the specific module can be connected to
something (_out connector).
Therefore, gui modules have by definition only _in connectors, since
different logic outputs (_out connectors) can be 'plugged' into the gui. Due
to the same idea, hardware modules can only have _out connectors, which have
to be 'plugged' in to logic modules. As a result, the logic modules can have
both, _in or _out connectors.
The connector is defined as follows:
Within a class, the connector is saved in a dictionary type meaning that it
has a <keyword> and an <item>. The <keywords> for the _in connector will
appear in the 'connect' attribute of the <identifier> module. To this _in
connectors you can plug in other modules, which are represented by other an
<identifier-other>. After the <identifier-other> the keyword <keyword-out>
from the module with the _out connector, has to follow.
To summarize the procedure for a exemplary hardware and logic category:

from core.module import Base, ConfigOption
import importlib


class PythonIviBase(Base):
    """
    Base class for connecting to hardware via PythonIVI library.
    """

    driver_config = ConfigOption('driver', missing='error')
    uri = ConfigOption('uri', missing='error')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._driver_module = None
        self._driver_class = None
        self.driver = None

    def on_activate(self):
        # load driver package
        module_name, class_name = self.driver_config.rsplit('.', 1)
        self._driver_module = importlib.import_module(module_name)
        # instantiate class and connect to scope
        self._driver_class = getattr(self._driver_module, class_name)
        self.driver = self._driver_class(self.uri)

    def on_deactivate(self):
        if (self.driver is not None):
            self.driver.close()
            self.driver = None
        self._driver_class = None
        self._driver_module = None
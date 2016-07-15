import fysom

class Fysom():
    def __init__(self, cfg={}, initial=None, events=None, callbacks=None,
            final=None, **kwargs):
        self._fysom = fysom.Fysom(cfg, initial, events, callbacks, final)
        super().__init__(**kwargs)

    def __getattr__(self, name):
        if hasattr(self._fysom, name):
            return getattr(self._fysom, name)
        else:
            raise AttributeError("'{}' object has no attribute '{}'".format(
                self.__class__, name))

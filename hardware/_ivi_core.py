"""

Example:

class Scope(SomeBaseClass):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._channel_count = 4

    @Namespace
    class measurement:
        @property
        def status(self):
            return self.root.send_command('status')

    @Namespace
    class acquisition:
        def start(self):
            self.root.send_command('acquisition:start')

    @Namespace
    class trigger:
        @Namespace
        class edge:
            @property
            def level(self):
                return self.root.send_command('trigger:edge:level?')

            @level.setter
            def level(self, value):
                self.root.send_command('trigger:edge:level {0}'.format(value))

    @Namespace.repeat('_channel_count')
    class channels:
        @property
        def offset(self):
            return self.root.send_command('channel{0}:offset?'.format(self.index))

        @offset.setter
        def offset(self, value):
            self.root.send_command('channel{0}:offset {1}'.format(self.index, value))
"""


class Namespace:
    def __init__(self, cls):
        self.cls = cls

    def __get__(self, instance, owner):
        if not instance:
            return self.cls

        name = self.cls.__name__

        # if we are already cached, use this version
        if name in instance.__dict__:
            return instance.__dict__[name]

        # create instance
        namespace = self.cls()
        # parent
        namespace.parent_namespace = instance
        # find root, root has no root attribute
        namespace.root = instance
        while hasattr(namespace.root, 'root'):
            namespace.root = namespace.root.root
        setattr(instance, name, namespace)
        return namespace

    @classmethod
    def repeat(cls, count):
        class NamespaceRepeat:
            def __init__(self, cls):
                self.cls = cls
                self.count = count

            def __get__(self, instance, owner):
                if not instance:
                    return self.cls

                name = self.cls.__name__

                # if we are already cached, use this version
                if name in instance.__dict__:
                    return instance.__dict__[name]

                # find root, root has no root attribute
                root = instance
                while hasattr(root, 'root'):
                    root = root.root

                # determine number of instances
                # if it is a string, check namespace container instance first, then root
                if isinstance(self.count, int):
                    if self.count <= 0:
                        raise Exception('Invalid value for count: {0}.'.format(self.count))
                elif isinstance(self.count, str):
                    value = getattr(instance, self.count, None)
                    if value is None:
                        value = getattr(root, self.count, 1)
                    self.count = value
                else:
                    raise Exception('Invalid value for count: {0}.'.format(self.count))

                # create instances
                namespaces = [self.cls() for ii in range(self.count)]
                for ii in range(len(namespaces)):
                    namespaces[ii].parent_namespace = instance
                    namespaces[ii].root = root
                    namespaces[ii].index = ii
                setattr(instance, name, namespaces)
                return namespaces

        return NamespaceRepeat



# class Test:
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self._channel_count = 3
#
#     @Namespace.repeat('_channel_count')
#     class channels:
#         @property
#         def test(self):
#             return 100
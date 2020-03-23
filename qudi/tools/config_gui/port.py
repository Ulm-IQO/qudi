
def can_connect(out_port, in_port):
    if out_port.base == 'hardware' and in_port.base != 'logic':
        return False
    if out_port.base == 'gui':
        return False

    return set(in_port.interfaces) <= set(out_port.interfaces)


class QudiPortType:

    def __init__(self, direction, base, interfaces):
        self.dir = direction.lower()
        self.base = base
        self.interfaces = interfaces

    def __eq__(self, other):
        if isinstance(other, QudiPortType):
            if self.base not in ('hardware', 'logic', 'gui'):
                return NotImplemented
            if other.base not in ('hardware', 'logic', 'gui'):
                return NotImplemented

            if self.dir == 'in' and other.dir == 'out':
                return can_connect(other, self)
            elif other.dir == 'in' and self.dir == 'out':
                return can_connect(self, other)
            return False
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

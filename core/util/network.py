# -*- coding: utf-8 -*-
"""
Check if something is a rpyc remote object and transfer it

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import rpyc.core.netref
import rpyc.utils.classic

def netobtain(obj):
    """
    """
    if isinstance(obj, rpyc.core.netref.BaseNetref):
        return rpyc.utils.classic.obtain(obj)
    else:
        return obj

# -*- coding: utf-8 -*-
import rpyc.core.netref
import rpyc.utils.classic

def netobtain(obj):
    """
    """
    if isinstance(obj, rpyc.core.netref.BaseNetref):
        return rpyc.utils.classic.obtain(obj)
    else:
        return obj

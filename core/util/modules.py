# -*- coding: utf-8 -*-
"""
This file contains Qudi module helper functions.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>

Derived form ACQ4:
Copyright 2010  Luke Campagnola
Originally distributed under MIT/X11 license. See documentation/MITLicense.txt for more infomation.
"""
import os


def get_main_dir():
    """ Returns the absolut path to the directory of the main software.

         @return string: path to the main tree of the software

    """
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../..'))


def get_home_dir():
    """ Returns the path to the home directory, which should definitely
        exist.
        @return string: absolute path to the home directory
    """
    return os.path.abspath(os.path.expanduser('~'))


def toposort(deps, cost=None):
    """Topological sort. Arguments are:

      @param dict deps: Dictionary describing dependencies where a:[b,c]
                        means "a depends on b and c"
      @param dict cost: Optional dictionary of per-node cost values. This
                        will be used to sort independent graph branches by
                        total cost.

    Examples::

        # Sort the following graph:
        #
        #   B ──┬─────> C <── D
        #       │       │
        #   E <─┴─> A <─┘
        #
        deps = {'a': ['b', 'c'], 'c': ['b', 'd'], 'e': ['b']}
        toposort(deps)
        => ['b', 'e', 'd', 'c', 'a']

        # This example is underspecified; there are several orders that
        # correctly satisfy the graph. However, we may use the 'cost'
        # argument to impose more constraints on the sort order.

        # Let each node have the following cost:
        cost = {'a': 0, 'b': 0, 'c': 1, 'e': 1, 'd': 3}

        # Then the total cost of following any node is its own cost plus
        # the cost of all nodes that follow it:
        #   A = cost[a]
        #   B = cost[b] + cost[c] + cost[e] + cost[a]
        #   C = cost[c] + cost[a]
        #   D = cost[d] + cost[c] + cost[a]
        #   E = cost[e]
        # If we sort independent branches such that the highest cost comes
        # first, the output is:
        toposort(deps, cost=cost)
        => ['d', 'b', 'c', 'e', 'a']
    """
    # copy deps and make sure all nodes have a key in deps
    deps0 = deps
    deps = {}
    for k, v in list(deps0.items()):
        deps[k] = v[:]
        for k2 in v:
            if k2 not in deps:
                deps[k2] = []

    # Compute total branch cost for each node
    key = None
    if cost is not None:
        order = Manager.toposort(deps)
        allDeps = {n: set(n) for n in order}
        for n in order[::-1]:
            for n2 in deps.get(n, []):
                allDeps[n2] |= allDeps.get(n, set())

        totalCost = {n: sum([cost.get(x, 0)
                             for x in allDeps[n]]) for n in allDeps}
        key = lambda x: totalCost.get(x, 0)

    # compute weighted order
    order = []
    while len(deps) > 0:
        # find all nodes with no remaining dependencies
        ready = [k for k in deps if len(deps[k]) == 0]

        # If no nodes are ready, then there must be a cycle in the graph
        if len(ready) == 0:
            print(deps, deps0)
            raise Exception(
                'Cannot resolve requested device configure/start order.')

        # sort by branch cost
        if key is not None:
            ready.sort(key=key, reverse=True)

        # add the highest-cost node to the order, then remove it from the
        # entire set of dependencies
        order.append(ready[0])
        del deps[ready[0]]
        for v in list(deps.values()):
            try:
                v.remove(ready[0])
            except ValueError:
                pass

    return order


def isBase(base):
    """Is the given base one of the three allowed ones?
      @return bool: base is allowed
    """
    return base in ('hardware', 'logic', 'gui')


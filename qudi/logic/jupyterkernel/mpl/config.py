"""Configurable for configuring the IPython inline backend
This module does not import anything from matplotlib.

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
"""
#-----------------------------------------------------------------------------
#       Copyright (C) 2011 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file documentation/BSDLicense_IPython.md, distributed as part of this
#  software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from traitlets.config import Config
from traitlets.config.configurable import SingletonConfigurable
from traitlets import (
    Dict, Instance, CaselessStrEnum, Set, Bool, Int, TraitError, Unicode
)

#-----------------------------------------------------------------------------
# Configurable for inline backend options
#-----------------------------------------------------------------------------

class InlineBackend(SingletonConfigurable):
    """An object to store configuration of the inline backend."""

    # The typical default figure size is too large for inline use,
    # so we shrink the figure size to 6x4, and tweak fonts to
    # make that fit.
    rc = Dict({
        # figures are
        'figure.figsize': (9.0,6.0),
        # play nicely with white background in the Qt and notebook frontend
        'figure.facecolor': (1,1,1,0),
        'figure.edgecolor': (1,1,1,0),
        # 12pt labels get cutoff on 6x4 logplots, so use 10pt.
        'font.size': 10,
        # 72 dpi matches SVG/qtconsole
        # this only affects PNG export, as SVG has no dpi setting
        'savefig.dpi': 72,
        # 10pt still needs a little more room on the xlabel:
        'figure.subplot.bottom' : .125
        },
        config=True,
        help="""Subset of matplotlib rcParams that should be different for the
        inline backend."""
    )

    figure_formats = Set({'png'}, config=True,
                          help="""A set of figure formats to enable: 'png',
                          'retina', 'jpeg', 'svg', 'pdf'.""")
    figure_format = Unicode(config=True, help="""The figure format to enable (deprecated
                                         use `figure_formats` instead)""")
    print_figure_kwargs = Dict({'bbox_inches' : 'tight'}, config=True,
        help="""Extra kwargs to be passed to fig.canvas.print_figure.

        Logical examples include: bbox_inches, quality (for jpeg figures), etc.
        """
    )
    close_figures = Bool(True, config=True,
        help="""Close all figures at the end of each cell.

        When True, ensures that each cell starts with no active figures, but it
        also means that one must keep track of references in order to edit or
        redraw figures in subsequent cells. This mode is ideal for the notebook,
        where residual plots from other cells might be surprising.

        When False, one must call figure() to create new figures. This means
        that gcf() and getfigs() can reference figures created in other cells,
        and the active figure can continue to be edited with pylab/pyplot
        methods that reference the current active figure. This mode facilitates
        iterative editing of figures, and behaves most consistently with
        other matplotlib backends, but figure barriers between cells must
        be explicit.
        """)

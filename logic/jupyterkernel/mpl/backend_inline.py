"""A matplotlib backend for publishing figures via display_data

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
# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License. See documentation/BSDLicense_IPython.md

import matplotlib
from matplotlib.backends.backend_agg import new_figure_manager, FigureCanvasAgg # analysis: ignore
from matplotlib._pylab_helpers import Gcf
from io import BytesIO
import struct

from .config import InlineBackend

# You really have to monkeypatch this for the backend to work
qudikernel = None

def show(close=None, block=None):
    """Show all figures as SVG/PNG payloads sent to the IPython clients.

    Parameters
    ----------
    close : bool, optional
      If true, a ``plt.close('all')`` call is automatically issued after
      sending all the figures. If this is set, the figures will entirely
      removed from the internal list of figures.
    block : Not used.
      The `block` parameter is a Matplotlib experimental parameter.
      We accept it in the function signature for compatibility with other
      backends.
    """
    if close is None:
        close = InlineBackend.instance().close_figures
    try:
        for figure_manager in Gcf.get_all_fig_managers():
            display(figure_manager.canvas.figure)
    finally:
        show._to_draw = []
        # only call close('all') if any to close
        # close triggers gc.collect, which can be slow
        if close and Gcf.get_all_fig_managers():
            matplotlib.pyplot.close('all')


# This flag will be reset by draw_if_interactive when called
show._draw_called = False
# list of figures to draw when flush_figures is called
show._to_draw = []

def display(fig):
    #print('Matplotlib has something to show:')
    imgdata, metadata = print_figure(fig)
    fmt_dict = {'image/png': imgdata}
    qudikernel.display_data('image/png', fmt_dict, metadata)

def draw_if_interactive():
    """
    Is called after every pylab drawing command
    """
    # signal that the current active figure should be sent at the end of
    # execution.  Also sets the _draw_called flag, signaling that there will be
    # something to send.  At the end of the code execution, a separate call to
    # flush_figures() will act upon these values
    manager = Gcf.get_active()
    if manager is None:
        return
    fig = manager.canvas.figure

    # Hack: matplotlib FigureManager objects in interacive backends (at least
    # in some of them) monkeypatch the figure object and add a .show() method
    # to it.  This applies the same monkeypatch in order to support user code
    # that might expect `.show()` to be part of the official API of figure
    # objects.
    # For further reference:
    # https://github.com/ipython/ipython/issues/1612
    # https://github.com/matplotlib/matplotlib/issues/835

    if not hasattr(fig, 'show'):
        # Queue up `fig` for display
        fig.show = lambda *a: display(fig)

    # If matplotlib was manually set to non-interactive mode, this function
    # should be a no-op (otherwise we'll generate duplicate plots, since a user
    # who set ioff() manually expects to make separate draw/show calls).
    if not matplotlib.is_interactive():
        return

    # ensure current figure will be drawn, and each subsequent call
    # of draw_if_interactive() moves the active figure to ensure it is
    # drawn last
    try:
        show._to_draw.remove(fig)
    except ValueError:
        # ensure it only appears in the draw list once
        pass
    # Queue up the figure for drawing in next show() call
    show._to_draw.append(fig)
    show._draw_called = True


def flush_figures():
    """Send all figures that changed

    This is meant to be called automatically and will call show() if, during
    prior code execution, there had been any calls to draw_if_interactive.

    This function is meant to be used as a post_execute callback in IPython,
    so user-caused errors are handled with showtraceback() instead of being
    allowed to raise.  If this function is not called from within IPython,
    then these exceptions will raise.
    """
    if not show._draw_called:
        return

    if InlineBackend.instance().close_figures:
        # ignore the tracking, just draw and close all figures
        try:
            return show(True)
        except Exception as e:
            # safely show traceback if in IPython, else raise
            qk = qudikernel
            if qk is None:
                raise e
            else:
                qk.showtraceback()
                return
    try:
        # exclude any figures that were closed:
        active = {fm.canvas.figure for fm in Gcf.get_all_fig_managers()}
        for fig in [fig for fig in show._to_draw if fig in active]:
            try:
                display(fig)
            except Exception as e:
                # safely show traceback if in IPython, else raise
                qk = qudikernel
                if qk is None:
                    raise e
                else:
                    qk.showtraceback()
                    return
    finally:
        # clear flags for next round
        show._to_draw = []
        show._draw_called = False

def _pngxy(data):
    """read the (width, height) from a PNG header"""
    ihdr = data.index(b'IHDR')
    # next 8 bytes are width/height
    w4h4 = data[ihdr+4:ihdr+12]
    return struct.unpack('>ii', w4h4)

def print_figure(fig, fmt='png', bbox_inches='tight', **kwargs):
    """Print a figure to an image, and return the resulting file data
    
    Returned data will be bytes unless ``fmt='svg'``,
    in which case it will be unicode.
    
    Any keyword args are passed to fig.canvas.print_figure,
    such as ``quality`` or ``bbox_inches``.
    """
    from matplotlib import rcParams
    metadata = {}
    # When there's an empty figure, we shouldn't return anything, otherwise we
    # get big blank areas in the qt console.
    if not fig.axes and not fig.lines:
        return

    dpi = rcParams['savefig.dpi']
    if fmt == 'retina':
        dpi = dpi * 2
        fmt = 'png'
    
    # build keyword args
    kw = {
        'format': fmt,
        'facecolor': fig.get_facecolor(),
        'edgecolor': fig.get_edgecolor(),
        'dpi': dpi,
        'bbox_inches': bbox_inches,
    }
    # **kwargs get higher priority
    kw.update(kwargs)
    
    bytes_io = BytesIO()
    fig.canvas.print_figure(bytes_io, **kw)
    data = bytes_io.getvalue()
    if fmt == 'svg':
        data = data.decode('utf-8')
    if fmt == 'png':
        w, h = _pngxy(data)
        metadata = {
            'image/png': {
                'width': w,
                'height': h
            }}
    return data, metadata
    
# Changes to matplotlib in version 1.2 requires a mpl backend to supply a default
# figurecanvas. This is set here to a Agg canvas
# See https://github.com/matplotlib/matplotlib/pull/1125
FigureCanvas = FigureCanvasAgg

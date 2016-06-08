# -*- coding: utf-8 -*-
"""
Qt-based IPython/jupyter kernel

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

Copyright (C) 2016 Jan M. Binder jan.binder@uni-ulm.de

Parts of this file are
Copyright (C) 2008-2011  The IPython Development Team

Distributed under the terms of the BSD License.  The full license is in
the file document documentation/BSDLicense_IPython.md,
distributed as part of this software.
"""

import sys
import builtins
from base64 import encodebytes

class ExecutionResult:
    """The result of a call to run_cell
    Stores information about what took place.
    """
    def __init__(self):
        self.execution_count = None
        self.error_before_exec = None
        self.error_in_exec = None
        self.result = list()
        self.display_data = dict()
        self.captured_stdout = ''
        self.captured_stderr = ''

    @property
    def success(self):
        return (self.error_before_exec is None) and (self.error_in_exec is None)

    def raise_error(self):
        """Reraises error if `success` is `False`, otherwise does nothing"""
        if self.error_before_exec is not None:
            raise self.error_before_exec
        if self.error_in_exec is not None:
            raise self.error_in_exec


class DisplayHook:
    """A simple displayhook that publishes the object's repr over a ZeroMQ
    socket."""

    def __init__(self):
        self.result = None

    def __call__(self, obj):
        if obj is None:
            return

        builtins._ = obj
        sys.stdout.flush()
        sys.stderr.flush()
        if self.result is not None:
            self.result.result.append(repr(obj))

    def pass_result_ref(self, result):
        """ Set reference to result container for current cell """
        self.result = result


def cursor_pos_to_lc(text, cursor_pos):
    """Calulate line, coulumn number from position in string.
      
      @param str text: string to calculate position in.
      @param int cursor_pos: cursor position in text.

      @return (int, int): tuple of line and column number of cursor in string
    """
    lines = text.splitlines(True)
    linenr = 1
    for line in lines:
        if len(line) < cursor_pos:
            linenr = linenr + 1
            cursor_pos = cursor_pos - len(line)
        else:
            break
    return linenr, cursor_pos

def softspace(f, newvalue):
    """Copied from code.py, to remove the dependency"""

    oldvalue = 0
    try:
        oldvalue = f.softspace
    except AttributeError:
        pass
    try:
        f.softspace = newvalue
    except (AttributeError, TypeError):
        # "attribute-less object" or "read-only attributes"
        pass
    return oldvalue

def encode_images(format_dict):
    """b64-encodes images in a displaypub format dict

    Perhaps this should be handled in json_clean itself?

    Parameters
    ----------

    format_dict : dict
        A dictionary of display data keyed by mime-type

    Returns
    -------

    format_dict : dict
        A copy of the same dictionary,
        but binary image data ('image/png', 'image/jpeg' or 'application/pdf')
        is base64-encoded.

    """
    # constants for identifying png/jpeg data
    PNG = b'\x89PNG\r\n\x1a\n'
    # front of PNG base64-encoded
    PNG64 = b'iVBORw0KG'
    JPEG = b'\xff\xd8'
    # front of JPEG base64-encoded
    JPEG64 = b'/9'
    # front of PDF base64-encoded
    PDF64 = b'JVBER'

    encoded = format_dict.copy()
    pngdata = format_dict.get('image/png')
    if isinstance(pngdata, bytes):
        # make sure we don't double-encode
        if not pngdata.startswith(PNG64):
            pngdata = encodebytes(pngdata)
        encoded['image/png'] = pngdata.decode('ascii')

    jpegdata = format_dict.get('image/jpeg')
    if isinstance(jpegdata, bytes):
        # make sure we don't double-encode
        if not jpegdata.startswith(JPEG64):
            jpegdata = encodebytes(jpegdata)
        encoded['image/jpeg'] = jpegdata.decode('ascii')

    pdfdata = format_dict.get('application/pdf')
    if isinstance(pdfdata, bytes):
        # make sure we don't double-encode
        if not pdfdata.startswith(PDF64):
            pdfdata = encodebytes(pdfdata)
        encoded['application/pdf'] = pdfdata.decode('ascii')

    return encoded

def getfigs(*fig_nums):
    """Get a list of matplotlib figures by figure numbers.

    If no arguments are given, all available figures are returned.  If the
    argument list contains references to invalid figures, a warning is printed
    but the function continues pasting further figures.

    Parameters
    ----------
    figs : tuple
        A tuple of ints giving the figure numbers of the figures to return.
    """
    from matplotlib._pylab_helpers import Gcf
    if not fig_nums:
        fig_managers = Gcf.get_all_fig_managers()
        return [fm.canvas.figure for fm in fig_managers]
    else:
        figs = []
        for num in fig_nums:
            f = Gcf.figs.get(num)
            if f is None:
                print('Warning: figure %s not available.' % num)
            else:
                figs.append(f.canvas.figure)
        return figs

def setup_matplotlib(kernel):
    import matplotlib
    import matplotlib.pyplot
    matplotlib.pyplot.switch_backend('module://logic.jupyterkernel.mpl.backend_inline')
    import matplotlib.pylab as pylab
    

    from matplotlib.backends.backend_agg import new_figure_manager, FigureCanvasAgg # analysis: ignore
    from matplotlib._pylab_helpers import Gcf

    from logic.jupyterkernel.mpl.backend_inline import InlineBackend

    cfg = InlineBackend.instance()
    matplotlib.pyplot.rcParams.update(cfg.rc)

    # IPython symbols to add
    #kernel.user_ns['figsize'] = figsize
    # Add display and getfigs to the user's namespace
    #kernel.user_ns['display'] = display_data
    #kernel.user_ns['getfigs'] = getfigs

    import logic.jupyterkernel.mpl.backend_inline as bi
    bi.qudikernel = kernel
    kernel.events.register('post_execute', bi.flush_figures)




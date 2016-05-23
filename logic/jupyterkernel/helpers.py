# -*- coding: utf-8 -*-
import sys
import builtins


class ExecutionResult:
    """The result of a call to run_cell
    Stores information about what took place.
    """
    execution_count = None
    error_before_exec = None
    error_in_exec = None
    result = None

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
        self.result_list = list()

    def __call__(self, obj):
        if obj is None:
            return

        builtins._ = obj
        sys.stdout.flush()
        sys.stderr.flush()
        self.result_list.append(repr(obj))

    def set_list(self, resultlist):
        self.result_list = resultlist


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


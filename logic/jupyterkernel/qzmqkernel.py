# -*- coding: utf-8 -*-
"""
Qt-based IPython/jupyter kernel

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

------------------------------------------------------------------------------
based on simple_kernel.py (https://github.com/dsblank/simple_kernel)
by Doug Blank <doug.blank@gmail.com>
placed in the public domain, see
https://github.com/dsblank/simple_kernel/issues/5
------------------------------------------------------------------------------
Parts of this file were taken from
https://github.com/ipython/ipython/blob/master/IPython/core/interactiveshell.py
which carries the following attributions:

Copyright (C) 2001 Janko Hauser <jhauser@zscout.de>
Copyright (C) 2001-2007 Fernando Perez. <fperez@colorado.edu>
Copyright (C) 2008-2011  The IPython Development Team

Distributed under the terms of the BSD License.  The full license is in
the file document documentation/BSDLicense_IPython.md,
distributed as part of this software.
------------------------------------------------------------------------------

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>

"""

## General Python imports:
import sys
import json
import hmac
import uuid
import errno
import hashlib
import datetime
import logging
from warnings import warn

import ast
import traceback
import jedi
import threading

# zmq specific imports:
import zmq
from io import StringIO
from zmq.error import ZMQError

from .compilerop import CachingCompiler, check_linecache_ipython
from .display_trap import DisplayTrap
from .builtin_trap import BuiltinTrap
from .redirect import RedirectedStdOut, RedirectedStdErr
from .stream import NetworkStream, IOStdoutNetworkStream, IOStderrNetworkStream, QZMQHeartbeat
from .helpers import *
from .events import EventManager, available_events
from IPython.core.error import InputRejected

from qtpy import QtCore


# TODO: When executing two cells at the same time (the second before first is finished) the notebook hangs


class QZMQKernel(QtCore.QObject):
    """ A Qt-based embeddable kernel for Jupyter. """

    sigShutdownFinished = QtCore.Signal(str)

    supported_mime = (
        'text/plain',
        'text/html',
        'text/markdown',
        'text/latex',
        'application/json',
        'application/javascript',
        'image/png',
        'image/jpeg',
        'image/svg+xml'
    )

    def __init__(self, config=None):
        super().__init__()
        # namespaces
        self.user_global_ns = globals()
        self.user_ns = self.user_global_ns

        self.exiting = False
        self.engine_id = str(uuid.uuid4())

        if config is not None:
            self._config = config
        else:
            logging.info("Starting simple_kernel with default args...")
            self._config = {
                'control_port': 0,
                'hb_port': 0,
                'iopub_port': 0,
                'ip': '127.0.0.1',
                'key': str(uuid.uuid4()),
                'shell_port': 0,
                'signature_scheme': 'hmac-sha256',
                'stdin_port': 0,
                'transport': 'tcp'
            }

        self.hb_thread = QtCore.QThread()
        self.hb_thread.setObjectName(self.engine_id)
        self.connection = config["transport"] + "://" + config["ip"]
        self.secure_key = config["key"].encode('ascii')
        self.signature_schemes = {"hmac-sha256": hashlib.sha256}
        self.auth = hmac.HMAC(
            self.secure_key,
            digestmod=self.signature_schemes[self._config["signature_scheme"]])
        logging.debug('New Kernel {}'.format(self.engine_id))
        logging.debug('python: {0}, zqm: {1}'.format(sys.version.replace('\n', ' ').replace('\r', ''), zmq.pyzmq_version()))

    @QtCore.Slot()
    def connect_kernel(self):
        # Heartbeat:
        self.ctx = zmq.Context()
        self.heartbeat_stream = NetworkStream(context=self.ctx, zqm_type=zmq.REP, connection=self.connection,
                                              auth=self.auth, engine_id=self.engine_id, port=self._config["hb_port"],
                                              name='heartbeat_stream')

        # IOPub/Sub:
        # also called SubSocketChannel in IPython sources
        self.iopub_stream = NetworkStream(context=self.ctx, zqm_type=zmq.PUB, connection=self.connection,
                                          auth=self.auth, engine_id=self.engine_id, port=self._config["iopub_port"],
                                          name='iopub_stream')
        self.iopub_stream.sigMsgRecvd.connect(self.iopub_handler, QtCore.Qt.QueuedConnection)

        # Control:
        self.control_stream = NetworkStream(context=self.ctx, zqm_type=zmq.ROUTER, connection=self.connection,
                                            auth=self.auth, engine_id=self.engine_id, port=self._config["control_port"],
                                            name='control_stream')
        self.control_stream.sigMsgRecvd.connect(self.control_handler, QtCore.Qt.QueuedConnection)

        # Stdin:
        self.stdin_stream = NetworkStream(context=self.ctx, zqm_type=zmq.ROUTER, connection=self.connection,
                                          auth=self.auth, engine_id=self.engine_id, port=self._config["stdin_port"],
                                          name='stdin_stream')
        self.stdin_stream.sigMsgRecvd.connect(self.stdin_handler, QtCore.Qt.QueuedConnection)

        # Shell:
        self.shell_stream = NetworkStream(context=self.ctx, zqm_type=zmq.ROUTER, connection=self.connection,
                                          auth=self.auth, engine_id=self.engine_id, port=self._config["shell_port"],
                                          name='shell_stream')
        self.shell_stream.sigMsgRecvd.connect(self.shell_handler, QtCore.Qt.QueuedConnection)

        self._config["hb_port"] = self.heartbeat_stream.port
        self._config["iopub_port"] = self.iopub_stream.port
        self._config["control_port"] = self.control_stream.port
        self._config["stdin_port"] = self.stdin_stream.port
        self._config["shell_port"] = self.shell_stream.port

        logging.debug("Config: %s" % json.dumps(self._config))

        self.heartbeat_handler = QZMQHeartbeat(self.heartbeat_stream)
        self.heartbeat_handler.moveToThread(self.hb_thread)
        self.hb_thread.start()

        self.init_exec_env()
        logging.info('{} ready! Listening...'.format(self.engine_id))

    def init_exec_env(self):
        self.execution_count = 1
        self.ast_node_interactivity = 'last_expr'
        self.compile = CachingCompiler()
        self.events = EventManager(self, available_events)
        self.ast_transformers = list()
        self.displaydata = list()
        self.displayhook = DisplayHook()
        self.display_trap = DisplayTrap(self.displayhook)
        self.builtin_trap = BuiltinTrap()
        threading.current_thread().notebook_thread = True
        self.stderr = RedirectedStdErr()
        self.stderr.open(IOStderrNetworkStream(self.iopub_stream, sys.stderr))
        self.stdout = RedirectedStdOut()
        self.stdout.open(IOStdoutNetworkStream(self.iopub_stream, sys.stdout))

        setup_matplotlib(self)

    @QtCore.Slot()
    def shutdown(self):
        logging.info('{} shutting down.'.format(self.engine_id))
        self.iopub_stream.close()
        self.stdin_stream.close()
        self.shell_stream.close()
        self.control_stream.close()
        self.heartbeat_stream.close()

        self.hb_thread.quit()
        self.stdout.close()
        self.stderr.close()
        self.sigShutdownFinished.emit(self.engine_id)

    def display_data(self, mimetype, fmt_dict, metadata=None):

        # fmt_dict, md_dict = formatter(mimetype, obj)
        dataenc = encode_images(fmt_dict)

        if mimetype in self.supported_mime:
            content = {
                'source': '',
                'data': dataenc,
                'metadata': {}
            }
            if metadata is not None:
                content['metadata'] = metadata
            self.displaydata.append(content)

    # Socket Handlers:
    def shell_handler(self, msg):
        logging.debug("shell received: %s" % msg)
        position = 0
        identities, msg = self.shell_stream.deserialize_wire_msg(msg)

        # process some of the possible requests:
        # execute_request, execute_reply, inspect_request, inspect_reply
        # complete_request, complete_reply, history_request, history_reply
        # is_complete_request, is_complete_reply, connect_request, connect_reply
        # kernel_info_request, kernel_info_reply, shutdown_request, shutdown_reply
        if msg['header']["msg_type"] == "execute_request":
            self.shell_execute(identities, msg)
        elif msg['header']["msg_type"] == "kernel_info_request":
            self.shell_kernel_info(identities, msg)
        elif msg['header']["msg_type"] == "complete_request":
            self.shell_complete(identities, msg)
        elif msg['header']["msg_type"] == "history_request":
            self.shell_history(identities, msg)
        else:
            logging.info("unknown msg_type: %s" % msg['header']["msg_type"])

    def shell_execute(self, identities, msg):
        logging.debug("simple_kernel Executing: %s" % msg['content']["code"])
        self.iopub_stream.parent_header = msg['header']
        # tell the notebook server that we are busy
        content = {
            'execution_state': "busy",
        }
        self.iopub_stream.send('status', content)
        # use the code we just got sent as input cell contents
        content = {
            'execution_count': self.execution_count,
            'code': msg['content']["code"],
        }
        self.iopub_stream.send('execute_input', content)

        # redirect Thread module to have a marker for the notebook
        old_thread = sys.modules['threading'].Thread
        sys.modules['threading'].Thread = ThreadFixer

        # capture output
        self.displaydata = list()
        # actual execution
        try:
            res = self.run_cell(msg['content']['code'])
        except Exception as e:
            res = ExecutionResult()
            tb = traceback.format_exc()
            print('{}\n{}'.format(e, tb), file=sys.stderr)

        # reverse the redirect for the Thread module
        sys.modules['threading'].Thread = old_thread

        # send captured result if there is any
        if len(res.result) > 0:
            content = {
                'execution_count': self.execution_count,
                'data': {"text/plain": res.result[0]},
                'metadata': {}
            }
            self.iopub_stream.send('execute_result', content)

        # output data from this run
        for content in self.displaydata:
            self.iopub_stream.send('display_data', content)

        # tell the notebook server that we are not busy anymore
        content = {
            'execution_state': "idle",
        }
        self.iopub_stream.send('status', content)

        # publish execution result on shell channel
        metadata = {
            "dependencies_met": True,
            "engine": self.engine_id,
            "status": "ok",
            "started": datetime.datetime.now().isoformat(),
        }
        content = {
            "status": "ok",
            "execution_count": self.execution_count,
            "user_variables": {},
            "payload": [],
            "user_expressions": {},
        }
        self.shell_stream.send(
            'execute_reply',
            content,
            metadata=metadata,
            parent_header=msg['header'],
            identities=identities)

        self.execution_count += 1

    def shell_kernel_info(self, identities, msg):
        content = {
            "protocol_version": "5.0",
            "ipython_version": [1, 1, 0, ""],
            "language_version": [0, 0, 1],
            "language": "qudi_kernel",
            "implementation": "qudi_kernel",
            "implementation_version": "1.1",
            "language_info": {
                "name": "python",
                "version": sys.version.split()[0],
                'mimetype': "text/x-python",
                'file_extension': ".py",
                'pygments_lexer': "ipython3",
                'codemirror_mode': {
                    'name': 'ipython',
                    'version': sys.version.split()[0]
                },
                'nbconvert_exporter': "python",
            },
            "banner": "Hue!"
        }
        self.shell_stream.send(
            'kernel_info_reply',
            content,
            parent_header=msg['header'],
            identities=identities)

    def shell_history(self, identities, msg):
        logging.info("unhandled history request")

    def shell_complete(self, identities, msg):
        code = msg['content']['code']
        cursor_pos = msg['content']['cursor_pos']
        linenr, colnr = cursor_pos_to_lc(code, cursor_pos)
        script = jedi.Interpreter(
            code,
            [self.user_ns, self.user_global_ns],
            line=linenr,
            column=colnr)
        completions = script.completions()
        matches = [c.name_with_symbols for c in completions]
        rests = [len(c.name_with_symbols) - len(c.complete) for c in completions]
        replace_start = cursor_pos - rests[0] if len(rests) > 0 else cursor_pos
        content = {
            'matches': matches,
            'cursor_start': replace_start,
            'cursor_end': cursor_pos,
            'status': 'ok'
        }
        self.shell_stream.send(
            'complete_reply',
            content,
            parent_header=msg['header'],
            identities=identities)

    def control_handler(self, wire_msg):
        # process some of the possible requests:
        # execute_request, execute_reply, inspect_request, inspect_reply
        # complete_request, complete_reply, history_request, history_reply
        # is_complete_request, is_complete_reply, connect_request, connect_reply
        # kernel_info_request, kernel_info_reply, shutdown_request, shutdown_reply
        logging.debug("control received: %s" % wire_msg)
        identities, msg = self.control_stream.deserialize_wire_msg(wire_msg)
        # Control message handler:
        if msg['header']["msg_type"] == "shutdown_request":
            self.shutdown()

    def iopub_handler(self, msg):
        # handle some of these messages:
        # stream, display_data, data_pub, execute_input, execute_result
        # error, status, clear_output
        logging.debug("iopub received: %s" % msg)

    def stdin_handler(self, msg):
        # handle some of these messages:
        # input_request, input_reply
        logging.debug("stdin received: %s" % msg)

    def run_cell(self, raw_cell, store_history=False, silent=False, shell_futures=True):
        """Run a complete IPython cell.
        Parameters
        ----------
        raw_cell : str
          The code (including IPython code such as %magic functions) to run.
        store_history : bool
          If True, the raw and translated cell will be stored in IPython's
          history. For user code calling back into IPython's machinery, this
          should be set to False.
        silent : bool
          If True, avoid side-effects, such as implicit displayhooks and
          and logging.  silent=True forces store_history=False.
        shell_futures : bool
          If True, the code will share future statements with the interactive
          shell. It will both be affected by previous __future__ imports, and
          any __future__ imports in the code will affect the shell. If False,
          __future__ imports are not shared in either direction.
        Returns
        -------
        result : :class:`ExecutionResult`
        """
        result = ExecutionResult()

        if (not raw_cell) or raw_cell.isspace():
            return result

        if silent:
            store_history = False

        if store_history:
            result.execution_count = self.execution_count

        def error_before_exec(value):
            result.error_before_exec = value
            return result

        self.events.trigger('pre_execute')
        if not silent:
            self.events.trigger('pre_run_cell')

        # If any of our input transformation (input_transformer_manager or
        # prefilter_manager) raises an exception, we store it in this variable
        # so that we can display the error after logging the input and storing
        # it in the history.
        preprocessing_exc_tuple = None
        try:
            # Static input transformations
            # cell = self.input_transformer_manager.transform_cell(raw_cell)
            cell = raw_cell
        except SyntaxError:
            preprocessing_exc_tuple = sys.exc_info()
            cell = raw_cell  # cell has to exist so it can be stored/logged
        else:
            if len(cell.splitlines()) == 1:
                # Dynamic transformations - only applied for single line commands
                try:
                    # restore trailing newline for ast.parse
                    # cell = self.prefilter_manager.prefilter_lines(cell + '\n'
                    cell = cell.rstrip('\n') + '\n'
                except Exception:
                    # don't allow prefilter errors to crash IPython
                    preprocessing_exc_tuple = sys.exc_info()

        # Store raw and processed history
        if store_history:
            pass
            # self.history_manager.store_inputs(self.execution_count,
            #                                  cell, raw_cell)
        if not silent:
            pass
            # self.logger.log(cell, raw_cell)

        # Display the exception if input processing failed.
        if preprocessing_exc_tuple is not None:
            self.showtraceback(preprocessing_exc_tuple)
            if store_history:
                self.execution_count += 1
            return error_before_exec(preprocessing_exc_tuple[2])

        # Our own compiler remembers the __future__ environment. If we want to
        # run code with a separate __future__ environment, use the default
        # compiler
        compiler = self.compile if shell_futures else CachingCompiler()
        with self.builtin_trap:
            cell_name = self.compile.cache(cell, self.execution_count)
            with self.display_trap:
                # Compile to bytecode
                try:
                    code_ast = compiler.ast_parse(cell, filename=cell_name)
                except IndentationError as e:
                    self.showindentationerror()
                    if store_history:
                        self.execution_count += 1
                    return error_before_exec(e)
                except (OverflowError, SyntaxError, ValueError, TypeError, MemoryError) as e:
                    self.showsyntaxerror()
                    if store_history:
                        self.execution_count += 1
                    return error_before_exec(e)

                # Apply AST transformations
                try:
                    code_ast = self.transform_ast(code_ast)
                except InputRejected as e:
                    self.showtraceback()
                    if store_history:
                        self.execution_count += 1
                    return error_before_exec(e)

                # Give the displayhook a reference to our ExecutionResult so it
                # can fill in the output value.
                self.displayhook.pass_result_ref(result)

                # Execute the user code
                interactivity = "none" if silent else self.ast_node_interactivity
                self.run_ast_nodes(
                    code_ast.body,
                    cell_name,
                    interactivity=interactivity,
                    compiler=compiler,
                    result=result)

                # Reset this so later displayed values do not modify the
                # ExecutionResult
                # self.displayhook.exec_result = None
                self.displayhook.pass_result_ref(None)

                self.events.trigger('post_execute')
                if not silent:
                    self.events.trigger('post_run_cell')

        if store_history:
            # Write output to the database. Does nothing unless
            # history output logging is enabled.
            # self.history_manager.store_output(self.execution_count)
            # Each cell is a *single* input, regardless of how many lines it has
            self.execution_count += 1

        return result

    def transform_ast(self, node):
        """Apply the AST transformations from self.ast_transformers

        Parameters
        ----------
        node : ast.Node
          The root node to be transformed. Typically called with the ast.Module
          produced by parsing user input.

        Returns
        -------
        An ast.Node corresponding to the node it was called with. Note that it
        may also modify the passed object, so don't rely on references to the
        original AST.
        """
        for transformer in self.ast_transformers:
            try:
                node = transformer.visit(node)
            except InputRejected:
                # User-supplied AST transformers can reject an input by raising
                # an InputRejected.  Short-circuit in this case so that we
                # don't unregister the transform.
                raise
            except Exception:
                warn("AST transformer %r threw an error. It will be unregistered." % transformer)
                self.ast_transformers.remove(transformer)

        if self.ast_transformers:
            ast.fix_missing_locations(node)
        return node

    def run_ast_nodes(self, nodelist, cell_name, interactivity='last_expr',
                      compiler=compile, result=None):
        """Run a sequence of AST nodes. The execution mode depends on the
        interactivity parameter.
        Parameters
        ----------
        nodelist : list
          A sequence of AST nodes to run.
        cell_name : str
          Will be passed to the compiler as the filename of the cell. Typically
          the value returned by ip.compile.cache(cell).
        interactivity : str
          'all', 'last', 'last_expr' or 'none', specifying which nodes should be
          run interactively (displaying output from expressions). 'last_expr'
          will run the last node interactively only if it is an expression (i.e.
          expressions in loops or other blocks are not displayed. Other values
          for this parameter will raise a ValueError.
        compiler : callable
          A function with the same interface as the built-in compile(), to turn
          the AST nodes into code objects. Default is the built-in compile().
        result : ExecutionResult, optional
          An object to store exceptions that occur during execution.
        Returns
        -------
        True if an exception occurred while running code, False if it finished
        running.
        """
        if not nodelist:
            return

        if interactivity == 'last_expr':
            if isinstance(nodelist[-1], ast.Expr):
                interactivity = "last"
            else:
                interactivity = "none"

        if interactivity == 'none':
            to_run_exec, to_run_interactive = nodelist, []
        elif interactivity == 'last':
            to_run_exec, to_run_interactive = nodelist[:-1], nodelist[-1:]
        elif interactivity == 'all':
            to_run_exec, to_run_interactive = [], nodelist
        else:
            raise ValueError("Interactivity was %r" % interactivity)

        try:
            for i, node in enumerate(to_run_exec):
                mod = ast.Module([node])
                code = compiler(mod, cell_name, "exec")
                if self.run_code(code, result):
                    return True

            for i, node in enumerate(to_run_interactive):
                mod = ast.Interactive([node])
                code = compiler(mod, cell_name, "single")
                if self.run_code(code, result):
                    return True

            # Flush softspace
            if softspace(sys.stdout, 0):
                print()

        except:
            # It's possible to have exceptions raised here, typically by
            # compilation of odd code (such as a naked 'return' outside a
            # function) that did parse but isn't valid. Typically the exception
            # is a SyntaxError, but it's safest just to catch anything and show
            # the user a traceback.

            # We do only one try/except outside the loop to minimize the impact
            # on runtime, and also because if any node in the node list is
            # broken, we should stop execution completely.
            if result:
                result.error_before_exec = sys.exc_info()[1]
            self.showtraceback()
            return True

        return False

    def run_code(self, code_obj, result=None):
        """Execute a code object.
        When an exception occurs, self.showtraceback() is called to display a
        traceback.
        Parameters
        ----------
        code_obj : code object
          A compiled code object, to be executed
        result : ExecutionResult, optional
          An object to store exceptions that occur during execution.
        Returns
        -------
        False : successful execution.
        True : an error occurred.
        """
        # Set our own excepthook in case the user code tries to call it
        # directly, so that the IPython crash handler doesn't get triggered
        old_excepthook, sys.excepthook = sys.excepthook, self.excepthook

        # we save the original sys.excepthook in the instance, in case config
        # code (such as magics) needs access to it.
        self.sys_excepthook = old_excepthook
        outflag = 1  # happens in more places, so it's easier as default
        try:
            try:
                # self.hooks.pre_run_code_hook()
                # rprint('Running code', repr(code_obj)) # dbg
                exec(code_obj, self.user_global_ns, self.user_ns)
            finally:
                # Reset our crash handler in place
                sys.excepthook = old_excepthook
        except SystemExit as e:
            if result is not None:
                result.error_in_exec = e
            self.showtraceback(exception_only=True)
            warn("To exit: use 'exit', 'quit', or Ctrl-D.", level=1)
        # except self.custom_exceptions:
        #    etype, value, tb = sys.exc_info()
        #    if result is not None:
        #        result.error_in_exec = value
        #    self.CustomTB(etype, value, tb)
        except:
            if result is not None:
                result.error_in_exec = sys.exc_info()[1]
            self.showtraceback()
        else:
            outflag = 0
        return outflag

    def excepthook(self, etype, value, tb):
        """One more defense for GUI apps that call sys.excepthook.
        GUI frameworks like wxPython trap exceptions and call
        sys.excepthook themselves.  I guess this is a feature that
        enables them to keep running after exceptions that would
        otherwise kill their mainloop. This is a bother for IPython
        which excepts to catch all of the program exceptions with a try:
        except: statement.
        Normally, IPython sets sys.excepthook to a CrashHandler instance, so if
        any app directly invokes sys.excepthook, it will look to the user like
        IPython crashed.  In order to work around this, we can disable the
        CrashHandler and replace it with this excepthook instead, which prints a
        regular traceback using our InteractiveTB.  In this fashion, apps which
        call sys.excepthook will generate a regular-looking exception from
        IPython, and the CrashHandler will only be triggered by real IPython
        crashes.
        This hook should be used sparingly, only in places which are not likely
        to be true IPython errors.
        """
        self.showtraceback((etype, value, tb), tb_offset=0)

    def _get_exc_info(self, exc_tuple=None):
        """get exc_info from a given tuple, sys.exc_info() or sys.last_type etc.

        Ensures sys.last_type,value,traceback hold the exc_info we found,
        from whichever source.

        raises ValueError if none of these contain any information
        """
        if exc_tuple is None:
            etype, value, tb = sys.exc_info()
        else:
            etype, value, tb = exc_tuple

        if etype is None:
            if hasattr(sys, 'last_type'):
                etype, value, tb = sys.last_type, sys.last_value, \
                                   sys.last_traceback

        if etype is None:
            raise ValueError("No exception to find")

        # Now store the exception info in sys.last_type etc.
        # WARNING: these variables are somewhat deprecated and not
        # necessarily safe to use in a threaded environment, but tools
        # like pdb depend on their existence, so let's set them.  If we
        # find problems in the field, we'll need to revisit their use.
        sys.last_type = etype
        sys.last_value = value
        sys.last_traceback = tb

        return etype, value, tb

    def get_exception_only(self, exc_tuple=None):
        """
        Return as a string (ending with a newline) the exception that
        just occurred, without any traceback.
        """
        etype, value, tb = self._get_exc_info(exc_tuple)
        msg = traceback.format_exception_only(etype, value)
        return ''.join(msg)

    def showtraceback(self, exc_tuple=None, filename=None, tb_offset=None,
                      exception_only=False):
        """Display the exception that just occurred.
        If nothing is known about the exception, this is the method which
        should be used throughout the code for presenting user tracebacks,
        rather than directly invoking the InteractiveTB object.
        A specific showsyntaxerror() also exists, but this method can take
        care of calling it if needed, so unless you are explicitly catching a
        SyntaxError exception, don't try to analyze the stack manually and
        simply call this method."""

        try:
            try:
                etype, value, tb = self._get_exc_info(exc_tuple)
            except ValueError:
                print('No traceback available to show.', file=sys.stderr)
                return
            else:
                traceback.print_exception(etype, value, tb)

        except KeyboardInterrupt:
            print('\n' + self.get_exception_only(), file=sys.stderr)

    def showsyntaxerror(self, filename=None):
        self.showtraceback()

    def showindentationerror(self):
        self.showtraceback()


##############################################################################
# Main
##############################################################################

if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %I:%M:%S %p',
        level=logging.DEBUG)

    logging.info("Loading simple_kernel with args: %s" % sys.argv)
    logging.info("Reading config file '%s'..." % sys.argv[1])

    config = json.loads("".join(open(sys.argv[1]).readlines()))

    app = QtCore.QCoreApplication(sys.argv)
    kernel = QZMQKernel(config)
    kernel.sigShutdownFinished.connect(app.quit)
    QtCore.QMetaObject.invokeMethod(kernel, 'connect_kernel')
    logging.info("GO!")
    app.exec_()
    logging.info("Done.")

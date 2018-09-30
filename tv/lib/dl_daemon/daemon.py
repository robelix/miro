# Miro - an RSS based video player application
# Copyright (C) 2005, 2006, 2007, 2008, 2009, 2010, 2011
# Participatory Culture Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
#
# In addition, as a special exception, the copyright holders give
# permission to link the code of portions of this program with the OpenSSL
# library.
#
# You must obey the GNU General Public License in all respects for all of
# the code used other than OpenSSL. If you modify file(s) with this
# exception, you may extend this exception to your version of the file(s),
# but you are not obligated to do so. If you do not wish to do so, delete
# this exception statement from your version. If you delete this exception
# statement from all source files in the program, then also delete it here.

from miro.dl_daemon import command
import os
import cPickle
from struct import pack, unpack, calcsize
import tempfile
from miro import app
from miro import crashreport
from miro import prefs
from miro import eventloop
from miro import httpauth
from miro import httpclient
import logging
from miro.plat.utils import launch_download_daemon, kill_process
from miro import signals
from miro import trapcall
from miro.net import ConnectionHandler
from miro import util

SIZEOF_LONG = calcsize("Q")

class DaemonError(StandardError):
    """Exception while communicating to a daemon (either controller or
    downloader).
    """
    pass

FIRST_DAEMON_LAUNCH = '1'

def start_download_daemon(oldpid, addr, port):
    global FIRST_DAEMON_LAUNCH

    daemon_env = {
        'DEMOCRACY_DOWNLOADER_ADDR' : str(addr),
        'DEMOCRACY_DOWNLOADER_PORT' : str(port),
        'DEMOCRACY_DOWNLOADER_FIRST_LAUNCH' : FIRST_DAEMON_LAUNCH,
        'DEMOCRACY_SHORT_APP_NAME' : app.config.get(prefs.SHORT_APP_NAME),
    }
    launch_download_daemon(oldpid, daemon_env)
    FIRST_DAEMON_LAUNCH = '0'

def get_data_filename(short_app_name):
    """Generates and returns the name of the file that stores the pid.
    """
    if hasattr(os, "getuid"):
        uid = os.getuid()
    elif "USERNAME" in os.environ:
        # This works for win32, where we don't have getuid()
        uid = os.environ['USERNAME']
    elif "USER" in os.environ:
        uid = os.environ['USER']
    else:
        # FIXME - can we do something better here on Windows
        # platforms?
        uid = "unknown"

    return os.path.join(tempfile.gettempdir(),
            ('%s_Download_Daemon_%s.txt' % (short_app_name, uid)))

PIDFILE = None

def write_pid(short_app_name, pid):
    """Write out our pid.

    This method locks the pid file until the downloader exits.

    On Windows this is achieved by keeping the file open.

    On Linux/OS X, we use the fcntl.lockf() function.
    """
    global PIDFILE
    # Try to remove the pidfile, and then create it from scratch.
    while True:
        try:
            os.remove(get_data_filename(short_app_name))
        except OSError:
            pass
        try:
            mask = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            fd = os.open(get_data_filename(short_app_name), mask)
            PIDFILE = os.fdopen(fd, 'wb')
        except OSError:
            # boh boh.  Try again.
            continue
        if os.name != "nt":
            import fcntl
            fcntl.lockf(PIDFILE, fcntl.LOCK_EX | fcntl.LOCK_NB)
        break

    PIDFILE.write("%s\n" % pid)
    PIDFILE.flush()
    # NOTE: There may be extra data after the line we write left
    # around from previous writes to the pid file.  This is fine since
    # read_pid() only reads the 1st line.
    #
    # NOTE 2: we purposely don't close the file, to achieve locking on
    # windows.

def read_pid(short_app_name):
    try:
        f = open(get_data_filename(short_app_name), "r")
        return int(f.readline())
    except (IOError, ValueError):
        return None

LAST_DAEMON = None

class Daemon(ConnectionHandler):
    def __init__(self):
        ConnectionHandler.__init__(self)
        global LAST_DAEMON
        LAST_DAEMON = self
        self.size = 0
        self.states['ready'] = self.on_size
        self.states['command'] = self.on_command
        self.queued_commands = []
        self.shutdown = False
        # disable read timeouts for the downloader daemon
        # communication.  Our normal state is to wait for long periods
        # of time for without seeing any data.
        self.stream.disable_read_timeout = True

    def on_error(self, error):
        """Call this when an error occurs.  It forces the daemon to
        close its connection.
        """
        logging.warning("socket error in daemon, closing my socket")
        self.close_connection()
        raise error

    def on_connection(self, socket):
        self.change_state('ready')
        for (comm, callback) in self.queued_commands:
            self.send(comm, callback)
        self.queued_commands = []

    def on_size(self):
        if self.buffer.length >= SIZEOF_LONG:
            (self.size,) = unpack("Q", self.buffer.read(SIZEOF_LONG))
            self.change_state('command')

    def on_command(self):
        if self.buffer.length >= self.size:
            try:
                comm = cPickle.loads(self.buffer.read(self.size))
            except cPickle.UnpicklingError:
                logging.exception("WARNING: error unpickling command.")
            else:
                self.process_command(comm)
            self.change_state('ready')

    def process_command(self, comm):
        trapcall.time_trap_call("Running: %s" % comm, self.run_command, comm)

    def run_command(self, comm):
        # FIXME - need a way to enable this on the command line for
        # easier debugging
        if not comm.spammy:
            logging.debug("run command: %r", comm)
        comm.set_daemon(self)
        comm.action()

    def send(self, comm, callback = None):
        if self.state == 'initializing':
            self.queued_commands.append((comm, callback))
        else:
            raw = cPickle.dumps(comm, cPickle.HIGHEST_PROTOCOL)
            self.send_data(pack("Q", len(raw)) + raw, callback)

class DownloaderDaemon(Daemon):
    def __init__(self, host, port, short_app_name):
        logging.debug("DownloaderDaemon __init__")

        # before anything else, write out our PID
        write_pid(short_app_name, os.getpid())
        # connect to the controller and start our listen loop
        Daemon.__init__(self)
        self.open_connection(host, port, self.on_connection,
                             self.on_error)
        signals.system.connect('error', self.handle_error)

    def handle_error(self, obj, report):
        # reduce the amount of stuff we dump to the log since it gets
        # repeated in the next crash
        headers = crashreport.extract_headers(report)
        logging.error("Error: %s (%r) %s", obj, obj, headers)
        command.DownloaderErrorCommand(self, report).send()

    def handle_close(self, type_):
        if self.shutdown:
            return
        logging.info("downloader: quitting")
        self.shutdown = True
        eventloop.shutdown()
        from miro.dl_daemon import download
        download.shutdown()
        logging.info("Cleaning up libcurl")
        httpclient.stop_thread()
        httpclient.cleanup_libcurl()
        import threading
        for thread in threading.enumerate():
            if thread != threading.currentThread() and not thread.isDaemon():
                logging.info("joining with %s", thread)
                thread.join()
        logging.info("handle_close() done")

class ControllerDaemon(Daemon):
    def __init__(self):
        logging.debug("ControllerDaemon __init__")
        Daemon.__init__(self)
        family, addr = util.localhost_family_and_addr()
        self.stream.accept_connection(family, addr, 0, self.on_connection,
                self.on_error)
        self.addr = self.stream.addr
        self.port = self.stream.port
        self._setup_config()
        self._setup_httpauth()
        self._shutdown_callback = None
        self._shutdown_timeout_dc = None
        self._callback_handle = None
        self._httpauth_callback_handle = None

    def start_downloader_daemon(self):
        logging.debug("ControllerDaemon start_downloader_daemon")
        start_download_daemon(self.read_pid(), self.addr, self.port)

    def _setup_config(self):
        logging.debug("ControllerDaemon _setup_config")
        remote_config_items = [
            prefs.LIMIT_UPSTREAM,
            prefs.UPSTREAM_LIMIT_IN_KBS,
            prefs.LIMIT_DOWNSTREAM_BT,
            prefs.DOWNSTREAM_BT_LIMIT_IN_KBS,
            prefs.BT_MIN_PORT,
            prefs.BT_MAX_PORT,
            prefs.USE_UPNP,
            prefs.BT_ENC_REQ,
            prefs.MOVIES_DIRECTORY,
            prefs.PRESERVE_DISK_SPACE,
            prefs.PRESERVE_X_GB_FREE,
            prefs.SUPPORT_DIRECTORY,
            prefs.SHORT_APP_NAME,
            prefs.LONG_APP_NAME,
            prefs.APP_PLATFORM,
            prefs.APP_VERSION,
            prefs.APP_SERIAL,
            prefs.APP_REVISION,
            prefs.PUBLISHER,
            prefs.PROJECT_URL,
            prefs.DOWNLOADER_LOG_PATHNAME,
            prefs.LOG_PATHNAME,
            prefs.GETTEXT_PATHNAME,
            prefs.LIMIT_UPLOAD_RATIO,
            prefs.UPLOAD_RATIO,
            prefs.LIMIT_CONNECTIONS_BT,
            prefs.CONNECTION_LIMIT_BT_NUM,
            prefs.USE_DHT,
            ]

        data = {}
        for desc in remote_config_items:
            data[desc.key] = app.config.get(desc)
        c = command.InitialConfigCommand(self, data)
        c.send()
        self._callback_handle = app.backend_config_watcher.connect(
            "changed", self.on_config_change)

    def _remove_config_callback(self):
        logging.debug("ControllerDaemon _remove_config_callback")
        if self._callback_handle is not None:
            app.backend_config_watcher.disconnect(self._callback_handle)
            self._callback_handle = None

    def on_config_change(self, obj, key, value):
        logging.debug("ControllerDaemon on_config_change")
        if not self.shutdown:
            c = command.UpdateConfigCommand(self, key, value)
            c.send()

    def _setup_httpauth(self):
        logging.debug("ControllerDaemon _setup_httpauth")
        c = command.UpdateHTTPPasswordsCommand(self, httpauth.all_passwords())
        c.send()
        self._httpauth_callback_handle = httpauth.add_change_callback(
                self.update_http_auth)

    def _remove_httpauth_callback(self):
        logging.debug("ControllerDaemon _remove_httpauth_callback")
        if self._httpauth_callback_handle is not None:
            httpauth.remove_change_callback(self._httpauth_callback_handle)

    def update_http_auth(self, passwords):
        logging.debug("ControllerDaemon update_http_auth")
        c = command.UpdateHTTPPasswordsCommand(self, passwords)
        c.send()

    def read_pid(self):
        logging.debug("ControllerDaemon red_pid")
        short_app_name = app.config.get(prefs.SHORT_APP_NAME)
        return read_pid(short_app_name)

    def handle_close(self, type_):
        logging.debug("ControllerDaemon handle_close")
        if not self.shutdown:
            logging.error("Downloader daemon died")
            # FIXME: replace with code to recover here, but for now,
            # stop sending.
            self.shutdown = True
            self._remove_config_callback()
            self._remove_httpauth_callback()

    def shutdown_timeout_cb(self):
        logging.debug("ControllerDaemon shutdown_timeout_cb")
        logging.warning("killing download daemon")
        kill_process(self.read_pid())
        self.shutdown_response()

    def shutdown_response(self):
        logging.debug("ControllerDaemon shutdown_response")
        if self._shutdown_callback:
            self._shutdown_callback()
        if self._shutdown_timeout_dc:
            self._shutdown_timeout_dc.cancel()

    def shutdown_downloader_daemon(self, timeout=5, callback=None):
        logging.debug("ControllerDaemon shutdown_downloader_daemon")
        """Send the downloader daemon the shutdown command.  If it
        doesn't reply before timeout expires, kill it.  (The reply is
        not sent until the downloader daemon has one remaining thread
        and that thread will immediately exit).
        """
        self._shutdown_callback = callback
        c = command.ShutDownCommand(self)
        c.send()
        self.shutdown = True
        self._remove_config_callback()
        self._shutdown_timeout_dc = eventloop.add_timeout(
            timeout, self.shutdown_timeout_cb, "Waiting for dl_daemon shutdown")

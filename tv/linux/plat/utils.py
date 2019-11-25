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

import errno
import locale
import logging
import logging.handlers
import os
import platform
import signal
import statvfs
import subprocess
import sys
import time
import urllib

from miro import app
from miro import prefs
from miro.plat import options
from miro.util import returns_unicode, returns_binary, check_u, check_b
import miro

PlatformFilenameType = str

# We need to define samefile for the portable code.  Lucky for us, this is
# very easy.
from os.path import samefile

# this is used in lib/gtcache.py
_locale_initialized = False

miro_exec_prefix = None


def dirfilt(root, dirs):
    """
    Platform hook to filter out any directories that should not be
    descended into, root and dirs corresponds as per os.walk().
    """
    return dirs

def get_available_bytes_for_movies():
    """Helper method used to get the free space on the disk where downloaded
    movies are stored.

    If it errors out, returns 0.

    :returns: free disk space on drive for MOVIES_DIRECTORY as an int
    Returns an integer
    """
    movie_dir = app.config.get(prefs.MOVIES_DIRECTORY)

    if not os.path.exists(movie_dir):
        # FIXME - this is a bogus value.  need to "do the right thing"
        # here.
        return 0

    statinfo = os.statvfs(movie_dir)
    return statinfo.f_frsize * statinfo.f_bavail


def locale_initialized():
    """Returns whether or not the locale has been initialized.

    :returns: True or False regarding whether initialize_locale has been
        called.
    """
    return _locale_initialized


def initialize_locale():
    """Initializes the locale.
    """
    # gettext understands *NIX locales, so we don't have to do anything
    global _locale_initialized
    _locale_initialized = True


FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def setup_logging(pathname, main_process=False):
    """Sets up logging using the Python logging module.

    :param pathname: Log path to write to.
    :param main_process: Is this for the main miro process?
    """

    if 'MIRO_IN_UNIT_TESTS' in os.environ:
        level = logging.WARN
    elif (os.environ.get('MIRO_DEBUGMODE', "") == "True" or
            app.debugmode):
        level = logging.DEBUG
    else:
        level = logging.INFO

    try:
        rotater = logging.handlers.RotatingFileHandler(
            pathname, mode="w", maxBytes=100000,
            backupCount=5)
    except IOError:
        # bug 13338.  sometimes there's a file there and it causes
        # RotatingFileHandler to flip out when opening it.  so we
        # delete it and then try again.
        os.remove(pathname)
        rotater = logging.handlers.RotatingFileHandler(
            pathname, mode="w", maxBytes=100000,
            backupCount=5)

    formatter = logging.Formatter(FORMAT)
    rotater.setFormatter(formatter)
    root_logger = logging.getLogger('')
    root_logger.setLevel(level)
    root_logger.addHandler(rotater)
    rotater.doRollover()

    if main_process:
        stdouthandler = logging.StreamHandler(sys.stdout)
        stdouthandler.setFormatter(formatter)
        root_logger.addHandler(stdouthandler)

@returns_binary
def utf8_to_filename(filename):
    """Converts a utf-8 encoded string to a FilenameType.
    """
    if not isinstance(filename, str):
        raise ValueError("filename is not a str")
    return filename


@returns_unicode
def shorten_fn(filename):
    check_u(filename)
    first, last = os.path.splitext(filename)

    if first:
        return u"".join([first[:-1], last])

    return unicode(last[:-1])


def encode_fn(filename):
    try:
        return filename.encode(locale.getpreferredencoding())
    except UnicodeEncodeError:
        return filename.encode('ascii', 'replace')


@returns_binary
def unicode_to_filename(filename, path=None):
    """Takes in a unicode string representation of a filename (NOT a
    file path) and creates a valid byte representation of it
    attempting to preserve extensions.

    .. Note::

       This is not guaranteed to give the same results every time it
       is run, nor is it guaranteed to reverse the results of
       filename_to_unicode.
    """
    check_u(filename)
    if path:
        check_b(path)
    else:
        path = os.getcwd()

    # keep this a little shorter than the max length, so we can
    # add a number to the end
    max_len = os.statvfs(path)[statvfs.F_NAMEMAX] - 5

    for mem in ("/", "\000", "\\", ":", "*", "?", "\"", "'",
                "<", ">", "|", "&", "\r", "\n"):
        filename = filename.replace(mem, "_")

    new_filename = encode_fn(filename)

    while len(new_filename) > max_len:
        filename = shorten_fn(filename)
        new_filename = encode_fn(filename)

    return new_filename


@returns_unicode
def filename_to_unicode(filename, path=None):
    """Given a filename in raw bytes, return the unicode representation

    .. Note::

       This is not guaranteed to give the same results every time it
       is run, not is it guaranteed to reverse the results of
       unicode_to_filename.
    """
    if path:
        check_b(path)
    check_b(filename)
    try:
        return filename.decode(locale.getpreferredencoding())
    except UnicodeDecodeError:
        return filename.decode('ascii', 'replace')


@returns_unicode
def make_url_safe(s, safe='/'):
    """Takes in a byte string or a unicode string and does the right thing
    to make a URL
    """
    if isinstance(s, str):
        # quote the byte string
        return urllib.quote(s, safe=safe).decode('ascii')

    try:
        return urllib.quote(s.encode(locale.getpreferredencoding()),
                            safe=safe).decode('ascii')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s.decode('ascii', 'replace')


@returns_binary
def unmake_url_safe(s):
    """Undoes make_url_safe (assuming it was passed a FilenameType)
    """
    # unquote the byte string
    check_u(s)
    return urllib.unquote(s.encode('ascii'))


def _pid_is_running(pid):
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError, err:
        return err.errno == errno.EPERM


def kill_process(pid):
    """Kills the process with the given pid.
    """
    if pid is None:
        return
    if _pid_is_running(pid):
        try:
            os.kill(pid, signal.SIGTERM)
            for i in range(100):
                time.sleep(.01)
                if not _pid_is_running(pid):
                    return
            os.kill(pid, signal.SIGKILL)
        except StandardError:
            logging.exception("error killing download daemon")


def launch_download_daemon(oldpid, env):
    """Launches the download daemon.

    :param oldpid: the pid of the previous download daemon
    :param env: the environment to launch the daemon in
    """
    # Use UNIX style kill
    if oldpid is not None and _pid_is_running(oldpid):
        kill_process(oldpid)

    environ = os.environ.copy()
    environ['MIRO_FRONTEND'] = options.frontend
    environ['DEMOCRACY_DOWNLOADER_LOG'] = app.config.get(
        prefs.DOWNLOADER_LOG_PATHNAME)
    environ['MIRO_APP_VERSION'] = app.config.get(prefs.APP_VERSION)
    environ['MIRO_DEBUGMODE'] = str(app.debugmode)
    if hasattr(miro.app, 'in_unit_tests'):
        environ['MIRO_IN_UNIT_TESTS'] = '1'
    environ.update(env)
    miro_path = os.path.dirname(miro.__file__)
    dl_daemon_path = os.path.join(miro_path, 'dl_daemon')

    # run the Miro_Downloader script
    script = os.path.join(dl_daemon_path, 'MiroDownloader.py')
    subprocess.Popen([sys.executable, script], close_fds=True, env=environ)

def exit_miro(return_code):
    """Exits Miro.
    """
    sys.exit(return_code)

def run_media_metadata_extractor(movie_path, thumbnail_path):
    from miro.frontends.widgets.gst import gst_extractor
    return gst_extractor.run(movie_path, thumbnail_path)

def miro_helper_program_info():
    """Get the command line to launch miro_helper.py """

    miro_path = os.path.dirname(miro.__file__)
    miro_helper_path = os.path.join(miro_path, 'miro_helper.py')

    cmd_line = (sys.executable, miro_helper_path)
    env = None

    return (cmd_line, env)

def get_logical_cpu_count():
    """Returns the logical number of cpus on this machine.

    :returns: int
    """
    try:
        import multiprocessing
        return multiprocessing.cpu_count()
    except ImportError:
        ncpus = os.sysconf("SC_NPROCESSORS_ONLN")
        if isinstance(ncpus, int) and ncpus > 0:
            return ncpus
    return 1

def register_exec_prefix():
    global miro_exec_prefix
    miro_exec_prefix = os.path.dirname(os.path.abspath(sys.argv[0]))

def get_echoprint_executable_path():
    # NB: Since this was installed using distutils this should give the right
    # path.
    return os.path.join(miro_exec_prefix, 'echoprint-codegen')

def get_enmfp_executable_info():
    # NB: Since this was installed using distutils this should give the right
    # path.

    filename = 'codegen.Linux-%s' % platform.machine()

    return {
        'path': os.path.join(miro_exec_prefix, filename)
    }

ffmpeg_version = None

def setup_ffmpeg_presets():
    global ffmpeg_version
    if ffmpeg_version is None:
        commandline = [get_ffmpeg_executable_path(), '-version']
        p = subprocess.Popen(commandline,
                             stdout=subprocess.PIPE,
                             close_fds=True,
                             stderr=file("/dev/null", "wb"))
        stdout, _ = p.communicate()
        lines = stdout.split('\n')
        version = lines[0].rsplit(' ', 1)[1].split('.')
        def maybe_int(v):
            try:
                return int(v)
            except ValueError:
                return v
        ffmpeg_version = tuple(maybe_int(v) for v in version)

def get_ffmpeg_executable_path():
    """Returns the location of the ffmpeg binary.

    :returns: string
    """
    return app.config.get(options.FFMPEG_BINARY)


def customize_ffmpeg_parameters(params):
    """Takes a list of parameters and modifies it based on
    platform-specific issues.  Returns the newly modified list of
    parameters.

    :param params: list of parameters to modify

    :returns: list of modified parameters that will get passed to
        ffmpeg
    """
    if ffmpeg_version < (0, 8):
        # Fallback for older versions of FFmpeg (Ubuntu Natty, in particular).
        # see also #18969
        params = ['-vpre' if i == '-preset' else i for i in params]
        try:
            profile_index = params.index('-profile:v')
        except ValueError:
            pass
        else:
            if params[profile_index + 1] == 'baseline':
                params[profile_index:profile_index+2] = [
                    '-coder', '0', '-bf', '0', '-refs', '1',
                    '-flags2', '-wpred-dct8x8']
    return params

def begin_thread_loop(context_object):
    # used for testing
    pass


def finish_thread_loop(context_object):
    # used for testing
    pass


def get_cookie_path():
    """
    Returns the path to a Netscape-style cookie file for Curl to use.

    Nothing is written to this file, but we use the cookies for downloading
    from Amazon.
    """
    return os.path.join(
        app.config.get(prefs.SUPPORT_DIRECTORY),
        'cookies.txt')


# Expand me: pick up Linux media players.
def get_plat_media_player_name_path():
    return (None, None)


def thread_body(func, *args, **kwargs):
    func(*args, **kwargs)

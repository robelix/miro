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

try:
    import gtk
except RuntimeError:
    print "You do not appear to have a working display."
    import sys
    sys.exit(1)
import gobject
import os
import gconf
import shutil
import platform

try:
    import pynotify
except ImportError:
    print "PyNotify support disabled on your platform."
    PYNOTIFY_SUPPORT = False
else:
    pynotify.init('miro')
    PYNOTIFY_SUPPORT = True

from miro import app
from miro import prefs
from miro.frontends.widgets.application import Application
# from miro.plat.frontends.widgets import threads
from miro.plat import renderers, options
from miro.plat.config import gconf_lock, gconf_key
try:
    from miro.plat.frontends.widgets import miroappindicator
    APP_INDICATOR_SUPPORT = True
except ImportError:
    from miro.frontends.widgets.gtk import trayicon
    APP_INDICATOR_SUPPORT = False
from miro.plat import resources
from miro.plat.utils import get_cookie_path
from miro.plat.frontends.widgets import mediakeys
from miro.plat.frontends.widgets import bonjour
from miro.plat.frontends.widgets.threads import call_on_ui_thread
from miro.plat.associate import associate_protocols

from miro.frontends.widgets.gtk.widgetset import Rect
from miro.frontends.widgets.gtk import gtkmenus
from miro.frontends.widgets.gtk import gtkdirectorywatch

import logging
import sys


def _get_pref(key, getter_name):
    gconf_lock.acquire()
    try:
        client = gconf.client_get_default()
        fullkey = gconf_key(key)
        value = client.get(fullkey)
        if value is not None:
            getter = getattr(value, getter_name)
            return getter()
        else:
            return None
    finally:
        gconf_lock.release()


def _set_pref(key, setter_name, value):
    gconf_lock.acquire()
    try:
        client = gconf.client_get_default()
        fullkey = gconf_key(key)
        setter = getattr(client, setter_name)
        setter(fullkey, value)
    finally:
        gconf_lock.release()


def get_int(key):
    return _get_pref('window/' + key, 'get_int')


def get_bool(key):
    return _get_pref('window/' + key, 'get_bool')


def get_player_int(key):
    return _get_pref(key, 'get_int')


def get_player_bool(key):
    return _get_pref(key, 'get_bool')


def set_int(key, value):
    return _set_pref('window/' + key, 'set_int', value)


def set_bool(key, value):
    return _set_pref('window/' + key, 'set_bool', value)


def set_player_int(key, value):
    return _set_pref(key, 'set_int', value)


def set_player_bool(key, value):
    return _set_pref(key, 'set_bool', value)


def run_application():
    LinuxApplication().run()


class LinuxApplication(Application):
    def run(self):
        self.log_initial_info()
        gobject.set_application_name(app.config.get(prefs.SHORT_APP_NAME))
        os.environ["PULSE_PROP_media.role"] = "video"

        gobject.threads_init()
        associate_protocols(self._get_command())
        gtkdirectorywatch.GTKDirectoryWatcher.install()
        self.menubar = gtkmenus.MainWindowMenuBar()
        renderers.init_renderer()
        self.startup()
        langs = ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")
        langs = [(l, os.environ.get(l)) for l in langs if os.environ.get(l)]
        logging.info("Language:          %s", langs)
        try:
            import libtorrent
            logging.info("libtorrent:        %s", libtorrent.version)
        except AttributeError:
            logging.info("libtorrent:        unknown version")
        except ImportError:
            logging.exception("libtorrent won't load")
        try:
            import pycurl
            logging.info("pycurl:            %s", pycurl.version)
        except ImportError:
            logging.exception("pycurl won't load")
        try:
            gtk.main()
        except (KeyboardInterrupt, SystemExit):
            self.do_quit()
        app.controller.on_shutdown()

    def log_initial_info(self):
        logging.info("Python version:    %s", sys.version)
        logging.info("Gtk+ version:      %s", gtk.gtk_version)
        logging.info("PyGObject version: %s", gtk.ver)
        logging.info("PyGtk version:     %s", gtk.pygtk_version)

    def _get_command(self):
        # The command is always "miro" but the
        # the argument varies according to branding
        themeName = app.config.get(prefs.THEME_NAME)
        if themeName is not None:
            themeName = themeName.replace("\\", "\\\\").replace('"', '\\"')
            command = "miro --theme \"%s\"" % (themeName)
        else:
            command = "miro \"%s\""
        return command

    def on_config_changed(self, obj, key, value):
        """Any time a preference changes, this gets notified so that we
        can adjust things.
        """
        if key == options.SHOW_TRAYICON.key:
            self.trayicon.set_visible(value)

        elif key == prefs.RUN_AT_STARTUP.key:
            self.update_autostart(value)

    def startup_ui(self):
        logging.debug('linux application.py LinuxApplication.startup_ui start')
        sys.excepthook = self.exception_handler
        Application.startup_ui(self)
        call_on_ui_thread(bonjour.check_bonjour_install)
        logging.debug('linux application.py LinuxApplication.startup_ui end')

    def _set_default_icon(self):
        # set the icon so that it doesn't flash when the window is
        # realized in Application.build_window().
        # if this isn't a themed Miro, then we use the default icon set
        ico_path = resources.share_path("icons/hicolor/24x24/apps/miro.png")
        if ((app.config.get(prefs.THEME_NAME) != prefs.THEME_NAME.default
             and app.config.get(options.WINDOWS_ICON))):
            theme_ico_path = resources.theme_path(
                app.config.get(prefs.THEME_NAME),
                app.config.get(options.WINDOWS_ICON))
            if os.path.exists(theme_ico_path):
                ico_path = theme_ico_path
                gtk.window_set_default_icon_from_file(ico_path)
        else:
            gtk.icon_theme_get_default().append_search_path(
                resources.share_path('icons'))
            gtk.window_set_default_icon_name("miro")

        return ico_path

    def build_window(self):
        logging.debug('linux application.py LinuxApplication.build_window start')
        self._set_default_icon()
        Application.build_window(self)
        self.window.connect('save-dimensions', self.set_main_window_dimensions)
        self.window.connect('save-maximized', self.set_main_window_maximized)

        # handle maximized
        maximized = self.get_main_window_maximized()
        if maximized != None:
            if maximized:
                self.window._window.maximize()
            else:
                self.window._window.unmaximize()

        # handle the trayicon
        if APP_INDICATOR_SUPPORT:
            self.trayicon = miroappindicator.MiroAppIndicator('miro')
        else:
            self.trayicon = trayicon.Trayicon('miro')

        if app.config.get(options.SHOW_TRAYICON):
            self.trayicon.set_visible(True)
        else:
            self.trayicon.set_visible(False)

        if options.override_dimensions:
            # if the user specified override dimensions on the command
            # line, set them here.
            self.window.set_frame(
                width=options.override_dimensions[0],
                height=options.override_dimensions[1])

        elif not get_int("width") and not get_int("height"):
            # if this is the first time Miro has been started, we want
            # to set a default size that makes sense in the context of
            # their monitor resolution.  the check here is against
            # whether there are width/height values in gconf already
            # which isn't true in a first-run situation.
            geom = self.window.get_monitor_geometry()
            width = min(1024, geom.width)
            height = min(600, geom.height)
            self.window.set_frame(width=width, height=height)

        else:
            # the user isn't overriding dimensions and this is not the
            # first time Miro has been launched on this computer, so
            # we double-check that the position works on this monitor
            # and if it puts Miro in a bad place, then fix it.
            self.window.check_position_and_fix()

        # handle media keys
        self.mediakeyhandler = mediakeys.get_media_key_handler(self.window)
        logging.debug('linux application.py LinuxApplication.build_window done')

    def quit_ui(self):
        try:
            gtk.main_quit()
        except RuntimeError:
            # main_quit throws a runtimeerror if it's called outside
            # of the gtk main loop.
            pass

    def update_autostart(self, value):
        autostart_dir = resources.get_autostart_dir()
        destination = os.path.join(autostart_dir, "miro.desktop")

        if value:
            if os.path.exists(destination):
                return
            try:
                if not os.path.exists(autostart_dir):
                    os.makedirs(autostart_dir)
                shutil.copy(resources.share_path('applications/miro.desktop'),
                            destination)
            except OSError:
                logging.exception("Problems creating or populating "
                                  "autostart dir.")

        else:
            if not os.path.exists(destination):
                return
            try:
                os.remove(destination)
            except OSError:
                logging.exception("Problems removing autostart dir.")

    def open_url(self, url):
        resources.open_url(url)

    def reveal_file(self, filename):
        if not os.path.isdir(filename):
            filename = os.path.dirname(filename)
        self.open_file(filename)

    def open_file(self, filename):
        resources.open_file(filename)

    def get_clipboard_text(self):
        """Pulls text from the clipboard and returns it.

        This text is not filtered/transformed in any way--that's the
        job of the caller.
        """
        text = gtk.Clipboard(selection="PRIMARY").wait_for_text()
        if text is None:
            text = gtk.Clipboard(selection="CLIPBOARD").wait_for_text()

        if text:
            text = unicode(text)
        return text

    def copy_text_to_clipboard(self, text):
        gtk.Clipboard(selection="CLIPBOARD").set_text(text)
        gtk.Clipboard(selection="PRIMARY").set_text(text)

    def get_main_window_dimensions(self):
        """Gets x, y, width, height from config.

        .. Note::

           If this is the first time that Miro has been started on
           this computer, then build_window will re-figure the width
           and height of the main window and change it.

        Returns Rect.
        """
        x = get_int("x") or 100
        y = get_int("y") or 300
        width = get_int("width") or 800
        height = get_int("height") or 600

        return Rect(x, y, width, height)

    def get_main_window_maximized(self):
        return get_bool("maximized") == True

    def set_main_window_dimensions(self, window, x, y, width, height):
        """Saves x, y, width, height to config.
        """
        set_int("width", width)
        set_int("height", height)
        set_int("x", x)
        set_int("y", y)

    def set_main_window_maximized(self, window, maximized):
        set_bool("maximized", maximized)

    def send_notification(self, title, body,
                          timeout=5000, attach_trayicon=True):
        if not PYNOTIFY_SUPPORT or APP_INDICATOR_SUPPORT:
            return

        notification = pynotify.Notification(title, body)
        if (hasattr(notification, 'attach_to_status_icon') and
            attach_trayicon and
            app.config.get(options.SHOW_TRAYICON)):
            notification.attach_to_status_icon(self.trayicon)
        if timeout:
            notification.set_timeout(timeout)
        notification.show()

    def handle_first_time(self, callback):
        self._set_default_icon()
        Application.handle_first_time(self, callback)

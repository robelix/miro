# -*- coding: utf-8 -*-
# Miro - an RSS based video player application
# Copyright (C) 2007, 2008, 2009, 2010, 2011
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

"""``miro.theme`` -- Holds the ThemeHistory object.
"""

from miro.gtcache import gettext as _
import logging
from miro import app
from miro import prefs
import os
from miro.eventloop import as_urgent
from miro.database import DDBObject, ObjectNotFoundError
from miro import opml
from miro.plat import resources
from miro import feed
from miro import folder
from miro import playlist
from miro import signals

class ThemeHistory(DDBObject):
    """DDBObject that keeps track of the themes used in regards
    to setting up new themes and changing themes.
    """
    def setup_new(self):
        self.lastTheme = None
        self.pastThemes = []
        self.theme = app.config.get(prefs.THEME_NAME)
        if self.theme is not None:
            self.theme = unicode(self.theme)
        # if we don't have a theme, self.theme will be None
        self.pastThemes.append(self.theme)
        self.on_first_run()

    # We used to do this on restore, but we need to make sure that the
    # whole database is loaded because we're checking to see if objects
    # are present.  So, we call it when we access the object in app.py
    def check_new_theme(self):
        self.theme = app.config.get(prefs.THEME_NAME)
        if self.theme is not None:
            self.theme = unicode(self.theme)
        if self.theme not in self.pastThemes:
            self.pastThemes.append(self.theme)
            self.on_first_run()
            self.signal_change()
        if self.lastTheme != self.theme:
            self.lastTheme = self.theme
            self.on_theme_change()

    @as_urgent
    def on_theme_change(self):
        self.signal_change()

    def on_first_run(self):

        if self.theme is not None:
            # we have a theme
            if (((app.config.get(prefs.DEFAULT_CHANNELS_FILE) is not None)
                 and (app.config.get(prefs.THEME_NAME) is not None))):
                importer = opml.Importer()
                filepath = resources.theme_path(app.config.get(prefs.THEME_NAME),
                    app.config.get(prefs.DEFAULT_CHANNELS_FILE))
                if os.path.exists(filepath):
                    importer.import_subscriptions(filepath,
                                                  show_summary=False)
                else:
                    logging.warn("Theme subscription file doesn't exist: %s",
                                 filepath)
            elif None not in self.pastThemes:
                self.pastThemes.append(None)
                self._install_default_feeds()
        else:
            # no theme
            self._install_default_feeds()
        signals.system.theme_first_run(self.theme)

    def _add_default(self, default):
        # folder
        if isinstance(default, tuple) and isinstance(default[1], list):
            defaultFolder = default
            try:
                c_folder = folder.ChannelFolder.get_by_title(defaultFolder[0])
            except ObjectNotFoundError:
                c_folder = folder.ChannelFolder(defaultFolder[0])
                c_folder.signal_change()
            for url, autodownload in defaultFolder[1]:
                logging.info("adding feed %s" % (url,))
                d_feed = feed.lookup_feed(default[0])
                if d_feed is None:
                    d_feed = feed.Feed(url, initiallyAutoDownloadable=autodownload)
                    d_feed.set_folder(c_folder)
                    d_feed.signal_change()
        # feed
        else:
            d_feed = feed.lookup_feed(default[0])
            if d_feed is None:
                logging.info("adding feed %s" % (default,))
                d_feed = feed.Feed(default[0], initiallyAutoDownloadable=default[1])
                d_feed.signal_change()

    @as_urgent
    def _install_default_feeds(self):
        logging.info("Adding default feeds")
        default_feeds = [
            (u"http://feeds.feedburner.com/tedtalks_video", False),
            (u"http://revision3.com/lifehacker/feed/MP4-hd30", False),
            (u"http://feeds.thisamericanlife.org/talpodcast", False),
            (u"http://feeds.themoth.org/themothpodcast", False),
            ]

        for default in default_feeds:
            self._add_default(default)

        # create example playlist
        default_playlists = [
            u"Example Playlist"
            ]
        for default in default_playlists:
            try:
                playlist.SavedPlaylist.get_by_title(default)
            except ObjectNotFoundError:
                playlist.SavedPlaylist(_("Example Playlist"))

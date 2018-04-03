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

"""models.py -- Contains DDBObject subclasses.

This module basically just imports DDBObject subclasses like Feed, Item, etc.
from other modules.  It exists as a central location that any other module can
import.

One reason this module exists is circular imports.  For example Item
references Feed and Feed refereces Item, which is a potential problem.  To get
around this, this module waits to import things until initialize() is called.
"""

def initialize():
    global RemoteDownloader, Feed, FeedImpl, RSSFeedImpl
    global SavedSearchFeedImpl, ScraperFeedImpl, SearchFeedImpl
    global DirectoryWatchFeedImpl, DirectoryFeedImpl, SearchDownloadsFeedImpl
    global ManualFeedImpl, ChannelFolder, PlaylistFolder
    global PlaylistFolderItemMap
    global Item, FileItem, DeviceItem, SharingItem
    global IconCache, SavedPlaylist, PlaylistItemMap, TabOrder, ThemeHistory
    global messages

    from miro.downloader import RemoteDownloader
    from miro.feed import Feed, FeedImpl, RSSFeedImpl, SavedSearchFeedImpl, \
            ScraperFeedImpl, SearchFeedImpl, DirectoryWatchFeedImpl, \
            DirectoryFeedImpl, SearchDownloadsFeedImpl, ManualFeedImpl
    from miro.folder import ChannelFolder, PlaylistFolder, \
            PlaylistFolderItemMap
    from miro.item import Item, FileItem, DeviceItem, SharingItem
    from miro.iconcache import IconCache
    from miro.playlist import SavedPlaylist, PlaylistItemMap
    from miro.tabs import TabOrder
    from miro.theme import ThemeHistory
    from miro import messages

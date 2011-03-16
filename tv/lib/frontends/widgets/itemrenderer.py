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

"""Constants that define the look-and-feel."""
import math
import os

from miro import app
from miro import signals
from miro import displaytext
from miro import prefs
from miro import util
from miro.gtcache import gettext as _
from miro.frontends.widgets import cellpack
from miro.frontends.widgets import imagepool
from miro.frontends.widgets import widgetutil
from miro.plat import resources
from miro.plat.frontends.widgets import widgetset
from miro.plat.frontends.widgets import file_navigator_name

PI = math.pi
# dimensions
RIGHT_WIDTH = 90
RIGHT_WIDTH_DOWNLOAD_MODE = 115
IMAGE_WIDTH_SQUARE = 125
IMAGE_WIDTH_WIDE = 180
CORNER_RADIUS = 5
EMBLEM_HEIGHT = 20
RIGHT_BUTTON_WIDTH = 42
RIGHT_BUTTON_HEIGHT = 22

# padding/spacing
PADDING = (15, 15, 6, 6)
PADDING_BACKGROUND = (5, 5, 4, 6)
EMBLEM_TEXT_PAD_START = 4
EMBLEM_TEXT_PAD_END = 20
EMBLEM_TEXT_PAD_END_SMALL = 6
EMBLEM_MARGIN_RIGHT = 12

# colors
THUMBNAIL_SEPARATOR_COLOR = widgetutil.BLACK
INFO_SEPARATOR_COLOR = widgetutil.css_to_color('#aaaaaa')
ITEM_TITLE_COLOR = widgetutil.BLACK
DOWNLOAD_INFO_COLOR = widgetutil.WHITE
DOWNLOAD_INFO_COLOR_UNEM = (0.2, 0.2, 0.2)
DOWNLOAD_INFO_SEPARATOR_COLOR = widgetutil.WHITE
DOWNLOAD_INFO_SEPARATOR_ALPHA = 0.1
TORRENT_INFO_LABEL_COLOR = (0.6, 0.6, 0.6)
TORRENT_INFO_DATA_COLOR = widgetutil.WHITE
ITEM_DESC_COLOR = (0.3, 0.3, 0.3)
FEED_NAME_COLOR = (0.5, 0.5, 0.5)
PLAYLIST_ORDER_COLOR = widgetutil.BLACK

# font sizes
EMBLEM_FONT_SIZE = widgetutil.font_scale_from_osx_points(11)
TITLE_FONT_SIZE = widgetutil.font_scale_from_osx_points(14)
EXTRA_INFO_FONT_SIZE = widgetutil.font_scale_from_osx_points(10)
ITEM_DESC_FONT_SIZE = widgetutil.font_scale_from_osx_points(11)
DOWNLOAD_INFO_FONT_SIZE = 0.70
DOWNLOAD_INFO_TORRENT_DETAILS_FONT_SIZE = 0.50

# Emblem shadow settings
EMBLEM_SHADOW_OPACITY = 0.6
EMBLEM_SHADOW_OFFSET = (0, 1)
EMBLEM_SHADOW_BLUR_RADIUS = 0

# text assets
REVEAL_IN_TEXT = (file_navigator_name and
        _("Reveal in %(progname)s", {"progname": file_navigator_name}) or _("Reveal File"))
SHOW_CONTENTS_TEXT = _("display contents")
DOWNLOAD_TEXT = _("Download")
DOWNLOAD_TO_MY_MIRO_TEXT = _("Download to My Miro")
DOWNLOAD_TORRENT_TEXT = _("Download Torrent")
ERROR_TEXT = _("Error")
CANCEL_TEXT = _("Cancel")
QUEUED_TEXT = _("Queued for Auto-download")
UNPLAYED_TEXT = _("Unplayed")
CURRENTLY_PLAYING_TEXT = _("Currently Playing")
NEWLY_AVAILABLE_TEXT = _("Newly Available")
SAVED_TEXT = _("Saved")
STOP_SEEDING_TEXT = _("Stop seeding")

class EmblemVisuals(object):
    """Holds the visual needed to draw an item's emblem."""
    def __init__(self, text_color_css, image_name, text_bold,
            pad_right_small=False):
        self.text_color = widgetutil.css_to_color(text_color_css)
        text_color_average = sum(self.text_color) / 3.0
        if text_color_average > 0.5:
            self.text_shadow = widgetutil.BLACK
        else:
            self.text_shadow = widgetutil.WHITE
        self.text_bold = text_bold
        self.image_name = image_name
        if pad_right_small:
            self.pad_end = EMBLEM_TEXT_PAD_END_SMALL
        else:
            self.pad_end = EMBLEM_TEXT_PAD_END

EMBLEM_VISUALS_RESUME = EmblemVisuals('#306219', 'resume', True,
        pad_right_small=True)
EMBLEM_VISUALS_UNPLAYED = EmblemVisuals('#d8ffc7', 'unplayed', True)
EMBLEM_VISUALS_EXPIRING = EmblemVisuals('#6f6c28', 'expiring', True)
EMBLEM_VISUALS_NEWLY_AVAILABLE = EmblemVisuals( '#e1efff', 'newly', True,
        pad_right_small=True)
EMBLEM_VISUALS_DRM = EmblemVisuals('#582016', 'drm', True)
EMBLEM_VISUALS_QUEUED = EmblemVisuals('#4a2c00', 'queued', False)
EMBLEM_VISUALS_FAILED = EmblemVisuals('#ffe7e7', 'failed', False)

class ItemDescription(object):
    """A description line for an item.

    Descriptions are actually a bit complicated, since they include both HTML
    links, and we sometimes preface them with info about the feed or playlist
    the order.

    attributes:
        text -- text (1st part of HTMLStripper.strip() output)
        links -- links for text (2nd part of HTMLStripper.strip() output)
        text_color -- color to draw the text with
        preface -- preface to print before text
        preface_color -- color to draw the preface with
    """
    def __init__(self, text, links, text_color, preface, preface_color):
        self.text = text
        self.links = links
        self.text_color = text_color
        self.preface = preface
        self.preface_color = preface_color

class ItemRendererSignals(signals.SignalEmitter):
    """Signal emitter for ItemRenderer.

    We could make ItemRenderer subclass SignalEmitter, but since it comes from
    widgetset that seems awkward.  Instead, this class handles the signals and
    it's set as a property of ItemRenderer

    signals:
        throbber-drawn (obj, item_info) -- a progress throbber was drawn
    """
    def __init__(self):
        signals.SignalEmitter.__init__(self, 'throbber-drawn')

_cached_images = {} # caches ImageSurface for get_image()
def get_image(image_name):
    """Get an ImageSurface to use.

    image_name is the name of the image.  All ItemRenderer images have the
    format 'item-renderer.<image_name>.png'
    """
    try:
        return _cached_images[image_name]
    except KeyError:
        _cached_images[image_name] = _load_image(image_name)
        return _cached_images[image_name]

def _load_image(image_name):
    """Create a new ImageSurface to use.

    You probably want to use get_image() for your images, which supports
    caching.
    """
    filename = 'item-renderer-%s.png' % image_name
    path = os.path.join('images', filename)
    return imagepool.get_surface(resources.path(path))

class ItemRendererBase(widgetset.InfoListRenderer):
    MIN_WIDTH = 600
    HEIGHT = 147

    def __init__(self, wide_image=False):
        widgetset.InfoListRenderer.__init__(self)
        self.canvas = ItemRendererCanvas(wide_image)

    def get_size(self, style, layout_manager):
        return self.MIN_WIDTH, self.HEIGHT

    def hotspot_test(self, style, layout_manager, x, y, width, height):
        layout = self.layout_all(layout_manager, width, height, False, None)
        hotspot_info = layout.find_hotspot(x, y)
        if hotspot_info is None:
            return None
        hotspot, x, y = hotspot_info
        if hotspot == 'description':
            url = layout.calc_description_link(x, y)
            if url is None:
                return None
            elif url == '#show-torrent-contents':
                # special link that we set up in
                # setup_torrent_folder_description()
                return 'show_contents'
            else:
                return 'description-link:%s' % url
        else:
            return hotspot

    def render(self, context, layout_manager, selected, hotspot, hover):
        layout = self.layout_all(layout_manager, context.width,
                context.height, selected, hotspot)
        layout.draw(context)

    def layout_all(self, layout_manager, width, height, selected, hotspot):
        """Create a ItemRendererLayout object for our cell."""
        raise NotImplementedError()

class ItemRenderer(ItemRendererBase):
    def __init__(self, display_channel=True, is_podcast=False,
            wide_image=False):
        ItemRendererBase.__init__(self, wide_image)
        self.signals = ItemRendererSignals()
        self.display_channel = display_channel
        self.is_podcast = is_podcast
        self.setup_torrent_folder_description()

    def setup_torrent_folder_description(self):
        text = (u'<a href="#show-torrent-contents">%s</a>' %
                SHOW_CONTENTS_TEXT)
        self.torrent_folder_description = util.HTMLStripper().strip(text)

    def layout_all(self, layout_manager, width, height, selected, hotspot):
        download_mode = (self.info.state in ('downloading', 'paused'))
        self.canvas.start_new_cell(layout_manager, width, height, selected,
                hotspot, download_mode)
        # add elements that are always present
        self.canvas.add_thumbnail(self.info.thumbnail,
                self.calc_thumbnail_hotspot())
        self.canvas.add_text(self.info.name, self.calc_description(),
                self.calc_extra_info())
        # add elements for download-mode or non-download-mode
        if download_mode:
            self.add_download_mode_elements()
        else:
            self.add_normal_mode_elements()
        return self.canvas.finish()

    def add_normal_mode_elements(self):
        """Add elements when we aren't in download mode."""
        self.add_main_button()
        self.add_emblem()
        self.add_secondary_button()
        self.add_right_buttons()

    def add_emblem(self):
        emblem_parts = self.calc_emblem_parts()
        if emblem_parts is not None:
            self.canvas.add_emblem(*emblem_parts)

    def add_main_button(self):
        if self.info.downloaded:
            if self.info.is_playable:
                playing_item = app.playback_manager.get_playing_item()
                if (playing_item and playing_item.id == self.info.id):
                    hotspot = 'play_pause'
                    if app.playback_manager.is_paused:
                        image_name = 'play'
                    else:
                        image_name = 'pause'
                else:
                    image_name = 'play'
                    hotspot = 'play'
                self.canvas.add_main_button_image(image_name, hotspot)
            else:
                self.canvas.add_main_button_text(REVEAL_IN_TEXT,
                        'show_local_file')
        else:
            if self.info.mime_type == 'application/x-bittorrent':
                text = DOWNLOAD_TORRENT_TEXT
            else:
                text = DOWNLOAD_TEXT
            self.canvas.add_main_button_text(text, 'download',
                    'download-icon')

    def add_secondary_button(self):
        button_info = self.calc_extra_button()
        if button_info is not None:
            self.canvas.add_secondary_button(*button_info)

    def add_right_buttons(self):
        self.canvas.add_menu_button()

        if ((self.info.is_external or self.info.downloaded) and 
            self.info.source_type != 'sharing'):
            self.canvas.add_remove_button(*self.remove_button_info())

        if self.info.expiration_date:
            text = displaytext.expiration_date(self.info.expiration_date)
            self.canvas.add_keep_button('keep', 'keep', text)
        elif self.attrs.get('keep-animation-alpha', 0) > 0:
            self.canvas.add_saved_emblem(SAVED_TEXT, 'saved',
                    self.attrs['keep-animation-alpha'])

    def add_download_mode_elements(self):
        """Add the download-mode specific elements.  """
        dl_info = self.info.download_info
        if dl_info.state == 'paused':
            pause_button_mode = 'resume'
        else:
            pause_button_mode = 'pause'
        if dl_info.downloaded_size == 0:
            # show empty bar before we start up
            self.canvas.add_progress_bar(0.0)
        elif dl_info.total_size < 0:
            # show throbber once we've started, but still don't know the
            # total_size
            throbber_index = self.attrs.get('throbber-value', 0) % 10
            self.canvas.add_progress_throbber(throbber_index,
                    pause_button_mode)
            self.signals.emit('throbber-drawn', self.info)
        else:
            # show regular bar otherwise
            amount = float(dl_info.downloaded_size) / dl_info.total_size
            self.canvas.add_progress_bar(amount, pause_button_mode)
        if self.info.state == 'paused':
            eta = down_rate = 0
        else:
            eta = dl_info.eta
            down_rate = dl_info.rate
        down_total = dl_info.downloaded_size
        if dl_info.torrent:
            up_rate = self.info.up_rate
            up_total = self.info.up_total
            if up_rate is None:
                # if the torrent hasn't started, we don't want None values
                # here, that causes confusion with non-torrents
                up_rate = up_total = 0
        else:
            up_rate = up_total = None
        self.canvas.add_download_info(eta, down_rate, down_total, up_rate,
                up_total)
        if dl_info.torrent and dl_info.state != 'paused':
            if dl_info.rate == 0:
                self.canvas.add_torrent_startup_info(dl_info.startup_activity)
            else:
                lines = (
                        (_('PEERS'), str(self.info.connections)),
                        (_('SEEDS'), str(self.info.seeders)),
                        (_('LEECH'), str(self.info.leechers)),
                        (_('SHARE'), "%.2f" % self.info.up_down_ratio),
                )
                self.canvas.add_torrent_info(lines)

    def calc_thumbnail_hotspot(self):
        """Decide what hotspot clicking on the thumbnail should activate."""
        if not self.info.downloaded:
            return 'thumbnail-download'
        elif self.info.is_playable:
            return 'thumbnail-play'
        else:
            return None

    def calc_description(self):
        if (self.info.download_info and self.info.download_info.torrent and
                self.info.children):
            text, links = self.torrent_folder_description
        else:
            text, links = self.info.description_stripped
        preface, preface_color = self.calc_description_preface()
        return ItemDescription(text, links, ITEM_DESC_COLOR, preface,
                preface_color)

    def calc_description_preface(self):
        if (self.display_channel and self.info.feed_name and
                not self.info.is_external):
            return ("%s: " % self.info.feed_name, FEED_NAME_COLOR)
        return '', widgetutil.WHITE

    def calc_extra_info(self):
        return (self.info.display_date, self.info.display_duration,
                self.info.display_size, self.info.file_format)

    def calc_extra_button(self):
        """Calculate the button to put to the right of the emblem.

        :returns: (text, hotspot_name) tuple, or None
        """
        if (self.info.download_info and
                self.info.download_info.state == 'uploading'):
            return (STOP_SEEDING_TEXT, 'stop_seeding')
        elif self.info.pending_auto_dl:
            return (CANCEL_TEXT, 'cancel_auto_download')
        return None

    def calc_emblem_parts(self):
        """Calculate UI details for layout_emblem().

        This returns a (text, image, visuals) tuple.  The parts mean:
            text -- text inside the emblem
            image -- image inside the emblem
            visuals -- text inside the emblem
        """

        text = image = visuals = None

        if self.info.has_drm:
            visuals = EMBLEM_VISUALS_DRM
            text = _('DRM locked')
        elif (self.info.download_info
                and self.info.download_info.state == 'failed'):
            visuals = EMBLEM_VISUALS_FAILED
            image = get_image('status-icon-alert')
            text = u"%s-%s" % (ERROR_TEXT,
                    self.info.download_info.short_reason_failed)
        elif self.info.pending_auto_dl:
            visuals = EMBLEM_VISUALS_QUEUED
            text = QUEUED_TEXT
        elif (self.info.downloaded
                and app.playback_manager.is_playing_id(self.info.id)):
            # copy the unplayed-style
            visuals = EMBLEM_VISUALS_UNPLAYED
            text = CURRENTLY_PLAYING_TEXT
        elif (self.info.downloaded and not self.info.video_watched and
                self.info.is_playable):
            visuals = EMBLEM_VISUALS_UNPLAYED
            text = UNPLAYED_TEXT
        elif self.should_resume_item():
            visuals = EMBLEM_VISUALS_RESUME
            text = _("Resume at %(resumetime)s",
                     {"resumetime": displaytext.short_time_string(self.info.resume_time)})
        elif not self.info.item_viewed and self.info.state == "new":
            visuals = EMBLEM_VISUALS_NEWLY_AVAILABLE
            text = NEWLY_AVAILABLE_TEXT
        else:
            return None
        return text, image, visuals

    def should_resume_item(self):
        if self.is_podcast:
            resume_pref = prefs.RESUME_PODCASTS_MODE
        elif self.info.file_type == u'video':
            resume_pref = prefs.RESUME_VIDEOS_MODE
        else:
            resume_pref = prefs.RESUME_MUSIC_MODE
        return (self.info.is_playable
              and self.info.item_viewed
              and self.info.resume_time > 0
              and app.config.get(resume_pref))

    def remove_button_info(self):
        """Get the image/hotspot to use for the remove button
        
        Subclasses can override this if they want different behavior/looks for
        the button.
        """
        return ('remove', 'delete')

class ItemRendererLayout(cellpack.Layout):
    """ItemRendererLayout -- Layout subclass for ItemRenderer

    This class has extra support for calculating which link was clicked on for
    hotspot_test()
    """
    def __init__(self):
        cellpack.Layout.__init__(self)

    def set_description_info(self, description, textbox, width):
        self.description = description
        self.description_textbox = textbox
        self.width = width

    def calc_description_link(self, x, y):
        """Calculate if a user clicked on the link in the description.

        :param x: x-coordinate to test
        :param y: x-coordinate to test
        :returns: url clicked on, or None
        """

        self.description_textbox.set_width(self.width)
        index = self.description_textbox.char_at(x, y)
        if index is None:
            return None
        index -= len(self.description.preface)
        if index < 0:
            return None
        for (start, end, url) in self.description.links:
            if start <= index < end:
                return url
        return None

class ItemRendererCanvas(object):
    """ItemRendererCanvas -- layout elements for ItemRenderer

    ItemRendererCanvas works with ItemRenderer to render a cell.
    ItemRendererCanvas handles the layout/drawing aspects, while ItemRenderer
    handles the logic of what should be displayed.

    ItemRendererCanvas is meant re-used multiple times.  For a single cell,
    you should call start_new_cell(), then add the elements you want with
    the layout_* methods, and finally call finish() to get the Layout object
    for the cell
    """

    def __init__(self, wide_image):
        """Create a new ItemRendererDrawer

        :param wide_image: should we draw our image with a wide aspect ratio?
        """
        if wide_image:
            self.image_width = IMAGE_WIDTH_WIDE
        else:
            self.image_width = IMAGE_WIDTH_SQUARE
    def start_new_cell(self, layout_manager, width, height, selected, hotspot,
            download_mode):
        """Prepare to render a new cell.

        This method starts a new Layout() object, and prepares to draw a cell
        inside it.

        :param layout_manager: LayoutManager to use for the cell
        :param width: width of the cell to render to
        :param height: height of the cell to rendere to
        :param selected: should we indicated that we are selected?
        :param hotspot: the currently active hotspot
        :param download_mode: draw the download_info area on the right
        """
        self.layout = ItemRendererLayout()
        # layout_above is a Layout that gets rendered above self.layout.  This
        # helps us position things like the emblem button that are added added
        # relatively early in the process, but need to be drawn after other
        # things.
        self.layout_above = cellpack.Layout()
        self.layout_manager = layout_manager
        self.selected = selected
        self.hotspot = hotspot
        self.download_mode = download_mode
        self.setup_guides(width, height)

    def setup_guides(self, width, height):
        """Setup attributes to use as guides when we lay stuff out."""
        total_rect = cellpack.LayoutRect(0, 0, width, height)
        # NOTE: background image extends a few pixels beyond the actual
        # boundaries so that it can draw shadows and other things
        background_rect = total_rect.subsection(*PADDING)
        self.layout.add_rect(background_rect, self.draw_background)
        # area inside the boundaries of the background
        inner_rect = background_rect.subsection(*PADDING_BACKGROUND)
        self.image_rect = inner_rect.left_side(self.image_width)
        if self.download_mode:
            right_width = RIGHT_WIDTH_DOWNLOAD_MODE
        else:
            right_width = RIGHT_WIDTH
        self.right_rect = inner_rect.right_side(right_width)
        self.middle_rect = inner_rect.subsection(self.image_width + 20,
                right_width + 15, 0 ,0)
        self.right_button_x = (self.right_rect.right -
                RIGHT_BUTTON_WIDTH - 20)
        if self.download_mode:
            self.download_info_rect = self.right_rect.subsection(6, 12, 8, 8)
        # emblem/progress bar should start 29px above the top of the cell
        self.emblem_bottom = total_rect.bottom - 29
        # reset coordinates that we set as we add elements
        self.download_info_bottom =  None
        self.button_right = None
        self.emblem_right = None

    def finish(self):
        """Get a Layout object for a finished cell.

        This method releases the Layout and LayoutManager objects that were
        passed into start_new_cell()

        :returns: cellpack.Layout object
        """
        rv = self.layout
        rv.merge(self.layout_above)
        self.layout = None
        self.layout_above = None
        self.layout_manager = None
        return rv

    def add_thumbnail(self, thumbnail, hotspot):
        """Add a thumbnail.

        :param thumbnail: image file to use
        :param hotspot: hotspot when the user clicks on the thumbnail.
        """

        self.thumbnail = thumbnail
        self.layout.add_rect(self.image_rect, self.draw_thumbnail, hotspot)
        self.layout.add_rect(self.image_rect.past_right(1),
                self.draw_thumbnail_separator)

    def add_text(self, title, description, extra_info_parts):
        """Add the text for our cell

        This method adds the title, description, and extra info text.

        If we are in download-mode, we also add the context-menu button to the
        right of the title.
        """
        # setup title
        self.layout_manager.set_font(TITLE_FONT_SIZE,
                family=widgetset.ITEM_TITLE_FONT, bold=True)
        self.layout_manager.set_text_color(ITEM_TITLE_COLOR)
        title = self.layout_manager.textbox(title)
        title.set_wrap_style('truncated-char')
        # setup info line
        self.layout_manager.set_font(EXTRA_INFO_FONT_SIZE,
                family=widgetset.ITEM_INFO_FONT)
        self.layout_manager.set_text_color(ITEM_DESC_COLOR)
        extra_info_drawer = ExtraInfoDrawer(self.layout_manager,
                extra_info_parts)
        # setup description
        description_textbox = self.make_description_textbox(description)
        # position the parts.
        total_height = (title.font.line_height() +
                + extra_info_drawer.height +
                description_textbox.font.line_height() + 16)
        x = self.middle_rect.x
        width = self.middle_rect.width
        # Ideally, we want to start it at 28px from the start of the top of
        # the cell.  However, if our text is big enough, don't let it overflow
        # the play button.
        text_bottom = min(25 + total_height, self.middle_rect.y + 80)
        text_top = text_bottom - total_height
        # align our right buttons just above the top of the title
        self.right_button_top = text_top - 1
        if self.download_mode:
            # quick interlude.  If we are in download mode, draw the menu on
            # the right side of the title line.
            menu_x = x + width - get_image('menu').width
            self._add_image_button(menu_x, text_top, 'menu',
                    '#show-context-menu')
            title_width = width - get_image('menu').width - 5
        else:
            title_width = width

        self.layout.add_text_line(title, x, text_top, title_width)
        y = self.layout.last_rect.bottom + 6
        self.layout.add(x, y, width, extra_info_drawer.height,
                extra_info_drawer.draw)
        y = self.layout.last_rect.bottom + 6
        self.layout.add_text_line(description_textbox, x, y, width,
                hotspot='description')
        # save description info for later use if we are testing for URL clicks
        self.layout.set_description_info(description, description_textbox,
                width)

    def make_description_textbox(self, description):
        self.layout_manager.set_font(ITEM_DESC_FONT_SIZE,
                family=widgetset.ITEM_DESC_FONT)
        self.layout_manager.set_text_color(description.text_color)
        textbox = self.layout_manager.textbox("")
        if description.preface:
            textbox.append_text(description.preface,
                    color=description.preface_color)

        pos = 0
        for start, end, url in description.links:
            textbox.append_text(description.text[pos:start])
            textbox.append_text(description.text[start:end], underline=True)
            pos = end
        if pos < len(description.text):
            textbox.append_text(description.text[pos:])
        return textbox

    def add_emblem(self, text, icon, visuals):
        """Add the emblem to our layout.

        :param text: text to display inside the emblem (or None for no emblem)
        :param icon: icon to display inside the emblem
        :param visuals: EmblemVisuals to draw with
        """
        emblem_drawer = EmblemDrawer(text, icon, visuals)
        self.emblem_right = emblem_drawer.add_to_layout(self.layout,
                self.layout_manager, self.button_middle, self.button_right +
                EMBLEM_TEXT_PAD_START, self.emblem_bottom)

    def add_main_button_text(self, text, hotspot, icon=None):
        """Add a text button as the main button for the item.

        This button is the one that gets drawn on the left of the emblem
        """
        pressed=(self.hotspot==hotspot)
        self.layout_manager.set_font(0.85)
        button = self.layout_manager.button(text, pressed, style='webby')
        if icon:
            button.set_icon(get_image(icon))
        self._add_button(button, hotspot)

    def add_main_button_image(self, image_name, hotspot):
        """Add an image as the main button for the item.

        This button is the one that gets drawn on the left of the emblem
        """
        if self.hotspot == hotspot:
            image_name += '-pressed'
        button = get_image(image_name)
        self._add_button(button, hotspot)

    def _add_button(self, button, hotspot):
        """Add the main button for the item.

        This button gets drawn to the left of emblem.
        """
        x = self.middle_rect.x
        emblem_top = self.emblem_bottom  - EMBLEM_HEIGHT
        button_width, button_height = button.get_size()
        # make the button middle aligned along the emblem
        y = emblem_top - (button_height - EMBLEM_HEIGHT) // 2
        # check if we don't have anything to put inside our emblem.  Just draw
        # the button if so
        self.layout_above.add_image(button, x, y, hotspot)
        # save button positions to help us layout the emblem
        self.button_middle = x + button_width // 2
        self.button_right = x + button_width

    def add_secondary_button(self, text, hotspot):
        """Add a secondary button.

        This button is placed to the right of the emblem.
        """
        if self.emblem_right:
            left = (self.emblem_right + EMBLEM_MARGIN_RIGHT)
        else:
            left = (self.button_right + EMBLEM_MARGIN_RIGHT)
        self.layout_manager.set_font(EMBLEM_FONT_SIZE)
        button = self.layout_manager.button(text,
                pressed=(self.hotspot==hotspot), style='webby')
        button_height = button.get_size()[1]
        y = (self.emblem_bottom - (EMBLEM_HEIGHT - button_height) // 2 -
                button_height)
        self.layout.add_image(button, left, y, hotspot)

    def add_menu_button(self):
        self._add_image_button(self.right_button_x, self.right_button_top,
                'menu', '#show-context-menu')

    def add_remove_button(self, image_name, hotspot):
        # place the remove button in the middle-aligned
        y = ((self.right_button_top + self.emblem_bottom -
            RIGHT_BUTTON_HEIGHT) // 2)
        self._add_image_button(self.right_button_x, y, image_name, hotspot)

    def add_keep_button(self, image_name, hotspot, text):
        image = self._make_image_button(image_name, hotspot)
        self.layout_expiring_and_button(text, image_name, hotspot)
        self.expire_background_alpha = 1.0

    def add_saved_emblem(self, text, image_name, alpha):
        self.layout_expiring_and_button(text, image_name,
                'non-existent-hotspot')
        self.expire_background_alpha = alpha

    def layout_expiring_and_button(self, text, image_name, hotspot):
        left = self.right_button_x
        bottom = self.emblem_bottom
        top = bottom - RIGHT_BUTTON_HEIGHT
        emblem_top = top + 1

        # add the background now so that it's underneath everything else.  We
        # don't know anything about the x dimensions yet, so just set them to
        # 0
        background_rect = self.layout.add(0, emblem_top, 0, EMBLEM_HEIGHT,
                self.draw_expire_background)
        # add text.  completely break the bounds of our layout rect and
        # position the text to the left of our rect
        textbox = self.make_expiring_textbox(text)
        text_width, text_height = textbox.get_size()
        text_x = left - EMBLEM_VISUALS_EXPIRING.pad_end - text_width
        text_y = top + (RIGHT_BUTTON_HEIGHT - text_height) // 2
        self.layout.add(text_x, text_y, text_width, text_height, textbox.draw)
        # now we can position the background, draw it to the middle of the
        # button.
        background_rect.x = round(text_x - EMBLEM_TEXT_PAD_END)
        background_rect.width = (left - background_rect.x +
                RIGHT_BUTTON_WIDTH // 2)
        # add button last so that it's drawn on top
        self._add_image_button(left, top, image_name, hotspot)

    def make_expiring_textbox(self, text):
        """Create a textbox for the text in the expiring emblem."""
        visuals = EMBLEM_VISUALS_EXPIRING
        self.layout_manager.set_font(EMBLEM_FONT_SIZE)
        self.layout_manager.set_text_color(visuals.text_color)
        shadow = widgetutil.Shadow(visuals.text_shadow, EMBLEM_SHADOW_OPACITY,
                EMBLEM_SHADOW_OFFSET, EMBLEM_SHADOW_BLUR_RADIUS)
        self.layout_manager.set_text_shadow(shadow)
        return self.layout_manager.textbox(text)

    def add_progress_throbber(self, throbber_index, pause_button_mode):
        self.throbber_index = throbber_index
        bar_rect = self.layout_progress_track(pause_button_mode)
        self.layout.add_rect(bar_rect, self.draw_progress_throbber)

    def add_progress_bar(self, amount, pause_button_mode):
        self.progress_amount = amount
        bar_rect = self.layout_progress_track(pause_button_mode)
        if amount > 0:
            self.layout.add_rect(bar_rect, self.draw_progress_bar)

    def layout_progress_track(self, pause_button_mode):
        """Layout the track behind the progress bar.

        :returns: LayoutRect containing the area for a fully filled bar
        """
        left = self.middle_rect.x
        width = self.middle_rect.width
        top = self.emblem_bottom - get_image('progress-track').height
        height = 22
        end_button_width = 47
        progress_cap_width = 10
        # figure out what button goes on the left
        if pause_button_mode == 'pause':
            left_hotspot = 'pause'
            left_button_name = 'download-pause'
        else:
            left_hotspot = 'resume'
            left_button_name = 'download-resume'

        # add ends of the bar
        self._add_image_button(left, top, left_button_name, left_hotspot)
        right_button_x = left + width - end_button_width
        self._add_image_button(right_button_x, top, 'download-stop', 'cancel')
        # add track in the middle
        track = get_image('progress-track')
        track_x = left + end_button_width
        track_rect = cellpack.LayoutRect(track_x, top, right_button_x - track_x,
                height)
        self.layout.add_rect(track_rect, track.draw)

        # add progress bar above the track
        progress_x = track_x - progress_cap_width
        bar_width_total = (right_button_x - progress_x) + progress_cap_width
        return cellpack.LayoutRect(progress_x, top, bar_width_total, height)

    def add_download_info(self, eta, down_rate, down_total, up_rate,
            up_total):
        """Add the download stats to the right side.  """
        # add some padding around the edges
        x = self.download_info_rect.x
        width = self.download_info_rect.width
        # layout top
        self.layout_manager.set_font(DOWNLOAD_INFO_FONT_SIZE)
        line_height = self.layout_manager.current_font.line_height()
        ascent = self.layout_manager.current_font.ascent()
        # generic code to layout a line at the top
        def add_line(y, image_name, text, subtext=None):
            # position image so that it's bottom is the baseline for the text
            image = get_image(image_name)
            image_y = y + ascent - image.height + 3
            # add 3 px to account for the shadow at the bottom of the icons
            self.layout.add_image(image, x, image_y)
            if text:
                self.layout_manager.set_text_color(DOWNLOAD_INFO_COLOR)
                textbox = self.layout_manager.textbox(text)
                textbox.set_alignment('right')
                self.layout.add_text_line(textbox, x, y, width)
            if subtext:
                self.layout_manager.set_text_color(DOWNLOAD_INFO_COLOR_UNEM)
                subtextbox = self.layout_manager.textbox(subtext)
                subtextbox.set_alignment('right')
                self.layout.add_text_line(subtextbox, x, y + line_height, width)

        # layout line 1
        current_y = self.right_rect.y + 10
        add_line(current_y, 'time-left', displaytext.time_string_0_blank(eta))
        current_y += max(19, line_height)
        self.layout.add(x, current_y-1, width, 1,
                self.draw_download_info_separator)
        # layout line 2
        add_line(current_y, 'dl-speed',
                displaytext.download_rate(down_rate),
                displaytext.size_string(down_total))
        current_y += max(25, line_height * 2)
        self.layout.add(x, current_y-1, width, 1,
                self.draw_download_info_separator)
        # layout line 3 if needed
        if up_rate is not None:
            add_line(current_y, 'ul-speed',
                    displaytext.download_rate(up_rate),
                    displaytext.size_string(up_total))
        current_y += max(25, line_height * 2)
        if up_total is not None:
            self.layout.add(x, current_y-1, width, 1,
                    self.draw_download_info_separator)
        self.download_info_bottom = current_y

    def add_torrent_startup_info(self, startup_info):
        """Add startup info for torrents that haven't begun downloading."""
        self.layout_manager.set_text_color(TORRENT_INFO_DATA_COLOR)
        textbox = self.layout_manager.textbox(startup_info)
        # bottom-align the textbox.
        height = textbox.get_size()[1]
        self.layout.add_rect(self.download_info_rect.bottom_side(height),
                textbox.draw)

    def add_torrent_info(self, lines):
        """Add the torrent stats to the right side.

        Call add_download_info() before calling this method so we know where
        put the top of the torrent info

        :param lines: list of (label, data) pairs to display
        """

        height = self.download_info_rect.bottom - self.download_info_bottom
        rect = self.download_info_rect.bottom_side(height)
        self.layout_manager.set_font(DOWNLOAD_INFO_TORRENT_DETAILS_FONT_SIZE,
                family=widgetset.ITEM_DESC_FONT)
        line_height = self.layout_manager.current_font.line_height()
        # check that we're not drawing more lines that we have space for.  If
        # there are extras, cut them off from the bottom
        potential_lines = int(rect.height // line_height)
        lines = lines[:potential_lines]
        total_height = line_height * len(lines)
        y = rect.bottom - total_height

        for label, value in lines:
            self.layout_manager.set_text_color(TORRENT_INFO_LABEL_COLOR)
            labelbox = self.layout_manager.textbox(label)
            self.layout_manager.set_text_color(TORRENT_INFO_DATA_COLOR)
            databox = self.layout_manager.textbox(value)
            databox.set_alignment('right')
            self.layout.add_text_line(labelbox, rect.x, y, rect.width)
            self.layout.add_text_line(databox, rect.x, y, rect.width)
            y += line_height

    def _make_image_button(self, image_name, hotspot_name):
        if self.hotspot != hotspot_name:
            return get_image(image_name)
        else:
            return get_image(image_name + '-pressed')

    def _add_image_button(self, x, y, image_name, hotspot_name):
        image = self._make_image_button(image_name, hotspot_name)
        return self.layout.add_image(image, x, y, hotspot=hotspot_name)

    def draw_background(self, context, x, y, width, height):
        if self.selected:
            left = get_image('selected-background-left')
            thumb = get_image('dl-stats-selected-middle')
            middle = get_image('selected-background-middle')
            right = get_image('selected-background-right')
        else:
            left = get_image('background-left')
            thumb = get_image('dl-stats-middle')
            middle = get_image('background-middle')
            right = get_image('background-right')

        # draw left
        left.draw(context, x, y, left.width, height)
        # draw right
        if self.download_mode:
            right_width = RIGHT_WIDTH_DOWNLOAD_MODE
            download_info_x = x + width - right_width
            self.draw_download_info_background(context, download_info_x, y,
                    right_width)
        else:
            right_width = right.width
            right.draw(context, x + width - right_width, y, right_width,
                    height)
        image_end_x = self.image_rect.right
        # draw middle
        middle_end_x = x + width - right_width
        middle_width = middle_end_x - image_end_x
        middle.draw(context, image_end_x, y, middle_width, height)

        # draw thumbnail background
        thumbnail_background_width = image_end_x - (x + left.width)
        thumb.draw(context, x + left.width, y, thumbnail_background_width,
                height)

    def draw_download_info_background(self, context, x, y, width):
        if self.selected:
            left = get_image('dl-stats-selected-left-cap')
            middle = get_image('dl-stats-selected-middle')
            right = get_image('dl-stats-selected-right-cap')
        else:
            left = get_image('dl-stats-left-cap')
            middle = get_image('dl-stats-middle')
            right = get_image('dl-stats-right-cap')
        background = widgetutil.ThreeImageSurface()
        background.set_images(left, middle, right)
        background.draw(context, x, y, width)

    def draw_download_info_separator(self, context, x, y, width, height):
        context.set_color(DOWNLOAD_INFO_SEPARATOR_COLOR,
                DOWNLOAD_INFO_SEPARATOR_ALPHA)
        context.rectangle(x, y, width, height)
        context.fill()

    def draw_thumbnail(self, context, x, y, width, height):
        icon = imagepool.get_surface(self.thumbnail, (width, height))
        icon_x = x + (width - icon.width) // 2
        icon_y = y + (height - icon.height) // 2
        # if our thumbnail is far enough to the left, we need to set a clip
        # path to take off the left corners.
        make_clip_path = (icon_x < x + CORNER_RADIUS)
        if make_clip_path:
            # save context since we are setting a clip path
            context.save()
            # make a path with rounded edges on the left side and clip to it.
            radius = CORNER_RADIUS
            context.move_to(x + radius, y)
            context.line_to(x + width, y)
            context.line_to(x + width, y + height)
            context.line_to(x + radius, y + height)
            context.arc(x + radius, y + height - radius, radius, PI/2, PI)
            context.line_to(x, y + radius)
            context.arc(x + radius, y + radius, radius, PI, PI*3/2)
            context.clip()
        # draw the thumbnail
        icon.draw(context, icon_x, icon_y, icon.width, icon.height)
        if make_clip_path:
            # undo the clip path
            context.restore()

    def draw_thumbnail_separator(self, context, x, y, width, height):
        """Draw the separator just to the right of the thumbnail."""
        # width should be 1px, just fill in our entire space with our color
        context.rectangle(x, y, width, height)
        context.set_color(THUMBNAIL_SEPARATOR_COLOR)
        context.fill()

    def draw_expire_background(self, context, x, y, width, height):
        middle_image = get_image('expiring-middle')
        cap_image = get_image('expiring-cap')
        # draw the cap at the left
        cap_image.draw(context, x, y, cap_image.width, cap_image.height,
                fraction=self.expire_background_alpha)
        # repeat the middle to be as long as we need.
        middle_image.draw(context, x + cap_image.width, y,
                width - cap_image.width, middle_image.height,
                fraction=self.expire_background_alpha)

    def draw_progress_bar(self, context, x, y, width, height):
        progress_width = round(width * self.progress_amount)
        left = get_image('progress-left-cap')
        middle = get_image('progress-middle')
        right = get_image('progress-right-cap')

        left_width = min(left.width, progress_width)
        right_width = max(0, progress_width - (width - right.width))
        middle_width = max(0, progress_width - left_width - right_width)

        left.draw(context, x, y, left_width, height)
        middle.draw(context, x + left.width, y, middle_width, height)
        right.draw(context, x + width - right.width, y, right_width, height)

    def draw_progress_throbber(self, context, x, y, width, height):
        index = self.throbber_index
        # The middle image is 10px wide, which means that we won't be drawing
        # an entire image if width isn't divisible by 10.  Adjust the right
        # image so that it matches.
        right_index = (index - width) % 10

        surface = widgetutil.ThreeImageSurface()
        surface.set_images(
            get_image('progress-throbber-%d-left' % (index + 1)),
            get_image('progress-throbber-%d-middle' % (index + 1)),
            get_image('progress-throbber-%d-right' % (right_index + 1)))
        surface.draw(context, x, y, width)

class ExtraInfoDrawer(object):
    """Layout an draw the line below the item title."""
    def __init__(self, layout_manager, text_parts):
        self.textboxes = []
        for text in text_parts:
            if text:
                self.textboxes.append(layout_manager.textbox(text))
        self.height = layout_manager.current_font.line_height()

    def draw(self, context, x, y, width, height):
        for textbox in self.textboxes:
            text_width, text_height = textbox.get_size()
            textbox.draw(context, x, y, text_width, text_height)
            # draw separator
            separator_x = round(x + text_width + 4)
            context.set_color(INFO_SEPARATOR_COLOR)
            context.rectangle(separator_x, y, 1, height)
            context.fill()
            x += text_width + 8

class EmblemDrawer(object):
    """Layout and draw emblems

    This is actually a fairly complex task, so the code is split out of
    ItemRenderer to make things more managable
    """

    def __init__(self, text, icon, visuals):
        self.text = text
        self.icon = icon
        self.visuals = visuals

    def add_to_layout(self, layout, layout_manager, background_start,
            content_start, emblem_bottom):
        """Add emblem elements to a Layout()

        :param layout: Layout to add to
        :param layout_manager: LayoutManager to use
        :param background_start: x-coordinate for the start of the emblem
        :param content_start: x-coordinate for the start of the text/icon
        :param emblem_bottom: y-coordinate for the bottom of the emblem

        :returns: rightmost x-coordinate for the emblem
        """
        emblem_top = emblem_bottom - EMBLEM_HEIGHT
        # add emblem background first, since we want it drawn on the bottom.
        # We won't know the width until we lay out the text/images, so
        # set it to 0
        emblem_rect = layout.add(background_start, emblem_top, 0,
                EMBLEM_HEIGHT, self.draw_emblem_background)
        # make a new Layout to vertically center the emblem images/text
        content_layout = cellpack.Layout()
        content_width = self._add_text_images(content_layout, layout_manager,
                content_start)
        content_layout.center_y(top=emblem_top, bottom=emblem_bottom)
        layout.merge(content_layout)
        # we know how big the emblem should be, so set it now.
        emblem_rect.right = round(content_start + content_width +
                self.visuals.pad_end)
        return emblem_rect.right

    def _add_text_images(self, emblem_layout, layout_manager, left_x):
        """Add the emblem text and/or image

        :returns: the width used
        """
        x = left_x

        if self.icon:
            emblem_layout.add_image(self.icon, x, 0)
            x += self.icon.width
        if self.text:
            layout_manager.set_font(EMBLEM_FONT_SIZE,
                    bold=self.visuals.text_bold)
            layout_manager.set_text_color(self.visuals.text_color)
            shadow = widgetutil.Shadow(self.visuals.text_shadow,
                    EMBLEM_SHADOW_OPACITY, EMBLEM_SHADOW_OFFSET,
                    EMBLEM_SHADOW_BLUR_RADIUS)
            layout_manager.set_text_shadow(shadow)
            textbox = layout_manager.textbox(self.text)
            text_width, text_height = textbox.get_size()
            emblem_layout.add(x, 0, text_width, text_height, textbox.draw)
            x += text_width
            layout_manager.set_text_shadow(None)
        return x - left_x

    def draw_emblem_background(self, context, x, y, width, height):
        middle_image = get_image(self.visuals.image_name + '-middle')
        cap_image = get_image(self.visuals.image_name + '-cap')
        # repeat the middle to be as long as we need.
        middle_image.draw(context, x, y, width - cap_image.width,
                middle_image.height)
        # draw the cap at the end
        cap_image.draw(context, x + width-cap_image.width, y, cap_image.width,
                cap_image.height)

class PlaylistItemRenderer(ItemRenderer):
    def __init__(self, playlist_sorter):
        ItemRenderer.__init__(self, display_channel=False)
        self.playlist_sorter = playlist_sorter

    def remove_button_info(self):
        return ('remove-playlist', 'remove')

    def calc_description_preface(self):
        order_number = self.playlist_sorter.sort_key(self.info) + 1
        if self.info.description_stripped[0]:
            text = "%s - " % order_number
        else:
            text = str(order_number)
        return (text, PLAYLIST_ORDER_COLOR)

class SharingItemRenderer(ItemRenderer):
    def calc_extra_button(self):
        return DOWNLOAD_TO_MY_MIRO_TEXT, 'download-sharing-item'

class DeviceItemRenderer(ItemRenderer):
    DOWNLOAD_SHARING_ITEM_TEXT = _("Download to My Miro")

    def calc_extra_button(self):
        return DOWNLOAD_TO_MY_MIRO_TEXT, 'download-device-item'

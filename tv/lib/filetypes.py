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

"""``miro.filetypes`` - functions for determining things from the
filename, enclosure, content-type, and other things.
"""

import os

# NOTE: if you change VIDEO_EXTENSIONS or AUDIO_EXTENSIONS, consider writing a
# database update so that the file_type attribute of the item table gets fixed

VIDEO_EXTENSIONS = ['.mov', '.wmv', '.mp4', '.m4v', '.ogv', '.anx',
                    '.mpg', '.avi', '.flv', '.mpeg', '.divx', '.xvid',
                    '.rmvb', '.mkv', '.m2v', '.ogm', '.webm', '.ogx']
AUDIO_EXTENSIONS = ['.mp3', '.m4a', '.wma', '.mka', '.flac', '.ogg', '.oga']
FEED_EXTENSIONS = ['.xml', '.rss', '.atom']
TORRENT_EXTENSIONS = ['.torrent']
OTHER_EXTENSIONS = ['.pdf', '.txt', '.html', '.doc', '.bmp', '.gif', '.jpg',
                    '.jpeg', '.png', '.psd', '.tif', '.tiff',]
SUBTITLES_EXTENSIONS = ['.srt', '.sub', '.ass', '.ssa', '.smil', '.cmml']


UNSUPPORTED_MIMETYPES = ("video/3gpp", "video/vnd.rn-realvideo",
                         "video/x-ms-asf")

MIMETYPES_EXT_MAP = {
    'video/quicktime':  ['.mov'],
    'video/mpeg':       ['.mpeg', '.mpg', '.m2v'],
    'video/mp4':        ['.mp4', '.m4v'],
    'video/mpeg4':      ['.mp4', '.m4v'],
    'video/flv':        ['.flv'],
    'video/x-flv':      ['.flv'],
    'video/x-ms-wmv':   ['.wmv'],
    'video/x-msvideo':  ['.avi'],
    'video/x-matroska': ['.mkv'],
    'application/ogg':  ['.ogx', '.ogm'],
    'video/ogg':        ['.ogv'],
    'video/webm':       ['.webm'],

    'audio/flac':       ['.flac'],
    'audio/mpeg':       ['.mp3'],
    'audio/mp4':        ['.m4a'],
    'audio/x-ms-wma':   ['.wma'],
    'audio/x-matroska': ['.mka'],
    'audio/ogg':        ['.oga', '.ogg'],

    'application/x-bittorrent': ['.torrent'],
    'application/x-magnet':     ['.magnet'],

    'audio/x-mpegurl':  ['.m3u'],
    'audio/x-amzxml': ['.amz'],

    'application/vnd.emusic-emusic_list': ['.emx']
}

KNOWN_MIME_TYPES = (u'audio', u'video')
KNOWN_MIME_SUBTYPES = (
    u'.mov', u'.wmv', u'.mp4', u'.mp3',
    u'.mpg', u'.mpeg', u'.avi', u'.x-flv',
    u'.x-msvideo', u'.m4v', u'.mkv', u'.m2v', u'.ogg'
    )
MIME_SUBSITUTIONS = {
    u'QUICKTIME': u'MOV',
}

EXT_MIMETYPES_MAP = {}
for (mimetype, exts) in MIMETYPES_EXT_MAP.iteritems():
    for ext in exts:
        if ext not in EXT_MIMETYPES_MAP:
            EXT_MIMETYPES_MAP[ext] = list()
        EXT_MIMETYPES_MAP[ext].append(mimetype)

def is_allowed_mimetype(mimetype):
    """
    Pass a mimetype to this method and it will return a boolean
    saying if the mimetype is something Miro can handle.
    """
    return (mimetype in MIMETYPES_EXT_MAP.keys())

def is_download_mimetype(mimetype):
    return mimetype in ('application/vnd.emusic-emusic_list',
                        'audio/x-amzxml')

def is_download_url(url):
    return False

def is_allowed_filename(filename):
    """
    Pass a filename to this method and it will return a boolean
    saying if the filename represents video, audio or torrent.
    """
    return (is_video_filename(filename)
            or is_audio_filename(filename)
            or is_torrent_filename(filename)
            or filename.endswith(('.amz', '.m3u', '.emx')))

def is_playable_filename(filename):
    """
    Pass a filename to this method and it will return a boolean
    saying if the filename represents video or audio.
    """
    return is_video_filename(filename) or is_audio_filename(filename)

def _check_filename(filename, extension_list):
    if not filename:
        return False
    filename = filename.lower()
    for ext in extension_list:
        if filename.endswith(ext):
            return True
    return False

def is_video_filename(filename):
    """
    Pass a filename to this method and it will return a boolean
    saying if the filename represents a video file.
    """
    return _check_filename(filename, VIDEO_EXTENSIONS)

def is_audio_filename(filename):
    """
    Pass a filename to this method and it will return a boolean
    saying if the filename represents an audio file.
    """
    return _check_filename(filename, AUDIO_EXTENSIONS)

def is_other_filename(filename):
    """
    Pass a filename to this method and it will return a boolean
    saying if the filename represents a non-audio, non-video file.
    """
    return _check_filename(filename, OTHER_EXTENSIONS)

def is_media_filename(filename):
    """Check if a filename is a video or audio filename"""
    return is_video_filename(filename) or is_audio_filename(filename)

def is_torrent_filename(filename):
    """
    Pass a filename to this method and it will return a boolean
    saying if the filename represents a torrent file.
    """
    return _check_filename(filename, ['.torrent'])

def is_feed_filename(filename):
    """
    Pass a filename to this method and it will return a boolean saying if the
    filename possibly represents an Atom or RSS feed URL.
    """
    return _check_filename(filename, FEED_EXTENSIONS)

def is_subtitle_filename(filename):
    """
    Pass a filename to this method and it will return a boolean saying if the
    filename possibly represents a sidecar subtitle file.
    """
    return _check_filename(filename, SUBTITLES_EXTENSIONS)

def is_video_enclosure(enclosure):
    """
    Pass an enclosure dictionary to this method and it will return a boolean
    saying if the enclosure is a video or not.
    """
    return (_has_video_type(enclosure)
            or _has_video_extension(enclosure, 'url')
            or _has_video_extension(enclosure, 'href'))

def _has_video_type(enclosure):
    return ('type' in enclosure
            and (enclosure['type'].startswith(u'video/')
                 or enclosure['type'].startswith(u'audio/')
                 or enclosure['type'] == u"application/ogg"
                 or enclosure['type'] == u"application/x-annodex"
                 or enclosure['type'] == u"application/x-bittorrent"
                 or enclosure['type'] == u"application/x-magnet")
            and (enclosure['type'] not in UNSUPPORTED_MIMETYPES))

def _has_video_extension(enclosure, key):
    from miro import download_utils
    if key in enclosure:
        elems = download_utils.parse_url(enclosure[key], split_path=True)
        return is_allowed_filename(elems[3])
    return False

def is_feed_content_type(content_type):
    """Is a content-type for a RSS feed?"""

    feed_types = [u'application/rdf+xml', u'application/atom+xml',
                  u'application/rss+xml', u'application/podcast+xml',
                  u'text/xml', u'application/xml',
                  ]
    for type_ in feed_types:
        if content_type.startswith(type_):
            return True
    return False

def is_maybe_feed_content_type(content_type):
    """Could the content type contain a feed?
    """
    return content_type.startswith(u"text/")

def is_maybe_rss(body):
    """Sniffs the body to determine whether it's a feed or not.

    this is very loosely taken from Firefox nsFeedSniffer.cpp and ideas in
    http://blogs.msdn.com/rssteam/articles/PublishersGuide.aspx
    """
    if len(body) > 512:
        body = body[0:512]

    for mem in ("<rss", "<feed", "<rdf:RDF"):
        if body.find(mem) != -1:
            return True
    return False

def is_maybe_rss_url(url):
    return (url.startswith("http")
            and (url.startswith("http://feeds.feedburner.com")
                 or "rss" in url))

def guess_extension(mimetype):
    """
    Pass a mime type to this method and it will return a corresponding
    file extension, or None if it doesn't know about the type.
    """
    possible_extensions = MIMETYPES_EXT_MAP.get(mimetype)
    if possible_extensions is None:
        return None
    return possible_extensions[0]

def guess_mime_type(filename):
    """
    Pass a filename to this method and it will return a corresponding
    mime type, or 'video/unknown' if the filename has a known video
    extension but no corresponding mime type, or None if it doesn't
    know about the file extension.
    """
    root, ext = os.path.splitext(filename)
    possible_types = EXT_MIMETYPES_MAP.get(ext)
    if possible_types is None:
        if is_video_filename(filename):
            return 'video/unknown'
        elif is_audio_filename(filename):
            return 'audio/unknown'
        else:
            return None
    return possible_types[0]

def item_file_type_for_filename(filename):
    """Returns an item file_type derived from the filename extension.

    :returns: u'video', u'audio', u'other', or None
    """
    name, ext = os.path.splitext(filename)
    if ext in VIDEO_EXTENSIONS:
        return u'video'
    if ext in AUDIO_EXTENSIONS:
        return u'audio'
    return u'other'

def calc_file_format(filename, mime_type):
    """Get a file format string for an item.

    file formats are the user text that describes a file.  Something like
    "mp3" or "mp4 video".

    :param extension: file extension.  Can be None if it's not known
    :param mime_type: mime type for the file.  Can be None if this isn't known
    :returns: file format string, or None if we cant calculate it
    """
    if filename is not None:
        extension = os.path.splitext(filename)[1].lower()
        # Hack for mp3s, "mpeg audio" isn't clear enough
        if extension == '.mp3':
            return u'.mp3'
    else:
        extension = None
    if mime_type is not None and '/' in mime_type:
        mtype, subtype = mime_type.split('/', 1)
        mtype = mtype.lower()
        if mtype in KNOWN_MIME_TYPES:
            format = subtype.split(';')[0].upper()
            if mtype == u'audio':
                format += u' AUDIO'
            if format.startswith(u'X-'):
                format = format[2:]
            return (u'.%s' %
                    MIME_SUBSITUTIONS.get(format, format).lower())
    if extension in KNOWN_MIME_SUBTYPES:
        return unicode(extension)
    return None

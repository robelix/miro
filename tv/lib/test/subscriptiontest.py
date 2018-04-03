import os

from miro import subscription
from miro import autodiscover

from miro.test.framework import MiroTestCase

# =============================================================================
# Test data
# =============================================================================

SAMPLE_RSS_SUBSCRIPTION_URL_1  = "http://www.domain-1.com/videos/rss.xml"
SAMPLE_RSS_SUBSCRIPTION_URL_2  = "http://www.domain-2.com/videos/rss.xml"
SAMPLE_ATOM_SUBSCRIPTION_URL_1 = "http://www.domain-1.com/videos/atom.xml"
SAMPLE_ATOM_SUBSCRIPTION_URL_2 = "http://www.domain-2.com/videos/atom.xml"

# -----------------------------------------------------------------------------

INVALID_CONTENT_1 = u"""
This is not XML...
"""

# -----------------------------------------------------------------------------

INVALID_CONTENT_2 = u"""\
<?xml version="1.0" encoding="UTF-8" ?>
<this-is-bogus-xml-syntax>
    yes indeed
</this-is-bogus-xml-syntax>
"""

# -----------------------------------------------------------------------------

ATOM_LINK_CONSTRUCT_IN_RSS = u"""\
<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
    <channel>
        <title>Dummy RSS Feed</title>
        <link>http://www.getdemocracy.com</link>
        <description>A dummy RSS feed to test USM subscription</description>
        <atom:link
            xmlns:atom="http://www.w3.org/2005/Atom"
            rel="self"
            type="application/rss+xml"
            title="Sample Dummy RSS Feed"
            href="%s" />
    </channel>
</rss>
""" % SAMPLE_RSS_SUBSCRIPTION_URL_1

# -----------------------------------------------------------------------------

ATOM_LINK_CONSTRUCT_IN_ATOM = u"""\
<?xml version="1.0" encoding="UTF-8" ?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <title>Dummy Atom Feed</title>
    <updated>2006-05-28T11:00:00Z</updated>
    <author><name>Luc Heinrich</name></author>
    <id>urn:uuid:D7732206-B0BF-4FAF-B2CE-FC25C6C5548F</id>
    <link
        xmlns:atom="http://www.w3.org/2005/Atom"
        rel="self"
        type="application/rss+xml"
        title="Sample Dummy Atom Feed"
        href="%s" />
</feed>
""" % SAMPLE_ATOM_SUBSCRIPTION_URL_1

# -----------------------------------------------------------------------------

REFLEXIVE_AUTO_DISCOVERY_IN_RSS = u"""\
<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
    <channel>
        <title>Dummy RSS Feed</title>
        <description>
            A dummy RSS feed to test USM Reflexive Auto Discovery
        </description>
        <link>reflexive-auto-discovery-page-rss.html</link>
    </channel>
</rss>
"""

REFLEXIVE_AUTO_DISCOVERY_PAGE_RSS_FILENAME = \
    "reflexive-auto-discovery-page-rss.html"
REFLEXIVE_AUTO_DISCOVERY_PAGE_RSS = u"""\
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
                          "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
        <head>
                <meta http-equiv="Content-type" content="text/html; \
charset=utf-8" />
                <title>Reflexive Auto Discovery Page</title>
            <link rel="alternate" type="application/rss+xml" title="RSS" \
href="%s" />
        </head>
        <body>
            This place intentionally (almost) blank... :)
        </body>
</html>
""" % SAMPLE_RSS_SUBSCRIPTION_URL_1

# -----------------------------------------------------------------------------

REFLEXIVE_AUTO_DISCOVERY_IN_ATOM = u"""\
<?xml version="1.0" encoding="UTF-8" ?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <title>Dummy Atom Feed</title>
    <updated>2006-05-28T11:00:00Z</updated>
    <author><name>Luc Heinrich</name></author>
    <id>urn:uuid:D7732206-B0BF-4FAF-B2CE-FC25C6C5548F</id>
    <link
        xmlns:atom="http://www.w3.org/2005/Atom"
        rel="alternate"
        type="application/atom+xml"
        title="Sample Dummy AutoDiscovery Feed"
        href="reflexive-auto-discovery-page-atom.html" />
</feed>
"""
REFLEXIVE_AUTO_DISCOVERY_PAGE_ATOM_FILENAME = \
    "reflexive-auto-discovery-page-atom.html"
REFLEXIVE_AUTO_DISCOVERY_PAGE_ATOM = u"""\
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
                          "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
    <head>
        <meta http-equiv="Content-type" content="text/html; charset=utf-8" />
        <title>Reflexive Auto Discovery Page</title>
        <link rel="alternate" type="application/atom+xml" title="RSS" \
href="%s" />
    </head>
    <body>
        This place intentionally (almost) blank... :)
    </body>
</html>
""" % SAMPLE_ATOM_SUBSCRIPTION_URL_1


# =============================================================================
# Test case
# =============================================================================

class TestSubscription(MiroTestCase):
    autodiscover.REFLEXIVE_AUTO_DISCOVERY_OPENER = open

    def assertDiscovered(self, subscriptions, url):
        self.assertEquals(len(subscriptions), 1)
        self.assertEquals(subscriptions[0]['type'], 'feed')
        self.assertEquals(subscriptions[0]['url'], url)

    def test_parse_content_garbage(self):
        retval = autodiscover.parse_content("")
        self.assertEquals(retval, None)
        retval = autodiscover.parse_content(1)
        self.assertEquals(retval, None)

    def test_invalid_subscriptions(self):
        retval = autodiscover.parse_file("this-file-does-not-exist.xml")
        self.assertEquals(retval, None)
        retval = autodiscover.parse_content(INVALID_CONTENT_1)
        self.assertEquals(retval, None)
        retval = autodiscover.parse_content(INVALID_CONTENT_2)
        self.assertEquals(retval, None)

    def test_atom_link_construct_in_rss(self):
        subscriptions = autodiscover.parse_content(ATOM_LINK_CONSTRUCT_IN_RSS)
        self.assertDiscovered(subscriptions, SAMPLE_RSS_SUBSCRIPTION_URL_1)

    def test_atom_link_construct_in_atom(self):
        subscriptions = autodiscover.parse_content(ATOM_LINK_CONSTRUCT_IN_ATOM)
        self.assertDiscovered(subscriptions, SAMPLE_ATOM_SUBSCRIPTION_URL_1)

    def test_reflexive_auto_discovery_in_rss(self):
        pageFile = file(REFLEXIVE_AUTO_DISCOVERY_PAGE_RSS_FILENAME, "w")
        pageFile.write(REFLEXIVE_AUTO_DISCOVERY_PAGE_RSS)
        pageFile.close()
        subscriptions = autodiscover.parse_content(
            REFLEXIVE_AUTO_DISCOVERY_IN_RSS)
        try:
            self.assertDiscovered(subscriptions, SAMPLE_RSS_SUBSCRIPTION_URL_1)
        finally:
            os.remove(REFLEXIVE_AUTO_DISCOVERY_PAGE_RSS_FILENAME)

    def test_reflexive_auto_discovery_in_atom(self):
        pageFile = file(REFLEXIVE_AUTO_DISCOVERY_PAGE_ATOM_FILENAME, "w")
        pageFile.write(REFLEXIVE_AUTO_DISCOVERY_PAGE_ATOM)
        pageFile.close()
        subscriptions = autodiscover.parse_content(
            REFLEXIVE_AUTO_DISCOVERY_IN_ATOM)
        try:
            self.assertDiscovered(subscriptions,
                                  SAMPLE_ATOM_SUBSCRIPTION_URL_1)
        finally:
            os.remove(REFLEXIVE_AUTO_DISCOVERY_PAGE_ATOM_FILENAME)

class Testfind_subscribe_links(MiroTestCase):
    def test_garbage(self):
        url = 5
        with self.allow_warnings():
            self.assertEquals(subscription.find_subscribe_links(url), [])

    def test_different_host(self):
        url = 'http://youtoob.com'
        self.assertEquals(subscription.find_subscribe_links(url), [])

    def test_no_links(self):
        url = 'http://subscribe.getdemocracy.com/'
        self.assertEquals(subscription.find_subscribe_links(url), [])

    def test_link_in_path(self):
        url = 'http://subscribe.getdemocracy.com/http%3A//www.myblog.com/rss'
        self.assertEquals(subscription.find_subscribe_links(url),
                [{'type': 'feed', 'url': 'http://www.myblog.com/rss'}])

    def test_link_in_query(self):
        url = ('http://subscribe.getdemocracy.com/' + \
               '?url1=http%3A//www.myblog.com/rss')
        self.assertEquals(subscription.find_subscribe_links(url),
                [{'type': 'feed', 'url':'http://www.myblog.com/rss'}])

    def test_multiple_links_in_query(self):
        url = ('http://subscribe.getdemocracy.com/' + \
               '?url1=http%3A//www.myblog.com/rss' + \
               '&url2=http%3A//www.yourblog.com/atom' + \
               '&url3=http%3A//www.herblog.com/scoobydoo')

        feeds = subscription.find_subscribe_links(url)
        for feed in feeds:
            self.assertEquals(feed['type'], 'feed')
        # have to sort them because they could be in any order
        links = [feed['url'] for feed in feeds]
        links.sort()
        self.assertEquals(links, ['http://www.herblog.com/scoobydoo',
                                  'http://www.myblog.com/rss',
                                  'http://www.yourblog.com/atom'])

    def test_query_garbage(self):
        url = ('http://subscribe.getdemocracy.com/' + \
               '?url1=http%3A//www.myblog.com/rss' + \
               '&url2=http%3A//www.yourblog.com/atom' + \
               '&url3=http%3A//www.herblog.com/scoobydoo' + \
               '&foo=bar' + \
               '&extra=garbage')

        feeds = subscription.find_subscribe_links(url)
        for feed in feeds:
            self.assertEquals(feed['type'], 'feed')
        # have to sort them because they could be in any order
        links = [feed['url'] for feed in feeds]
        links.sort()
        self.assertEquals(links, ['http://www.herblog.com/scoobydoo',
                                  'http://www.myblog.com/rss',
                                  'http://www.yourblog.com/atom'])

    def test_extra_keys(self):
        url = ('http://subscribe.getdemocracy.com/'
               '?url1=http%3A//www.myblog.com/rss'
               '&description1=My+Blog'
                '&title1=My+Item'
                '&length1=12345'
                '&type1=video/mp4'
                '&thumbnail1=http%3A//pculture.org/image.jpeg'
                '&feed1=http%3A//pculture.org/feed.xml'
                '&link1=http%3A//pculture.org/page.html'
                '&trackback1=http%3A//pculture.org/trackpack.cgi')
        feeds = subscription.find_subscribe_links(url)
        self.assertEquals(len(feeds), 1)
        self.assertDictEquals(feeds[0],
            {'url': u'http://www.myblog.com/rss', 'type': 'feed',
                'description': u'My Blog',
                'title': u'My Item',
                'length': u'12345',
                'mime_type': 'video/mp4',
                'thumbnail': 'http://pculture.org/image.jpeg',
                'feed': 'http://pculture.org/feed.xml',
                'link': 'http://pculture.org/page.html',
                'trackback': 'http://pculture.org/trackpack.cgi',
        })

    def test_query_encoded_wrong(self):
        # Test queries with invalid encodings (#13390)
        url = ('http://subscribe.getdemocracy.com/' + \
               '?url1=http%3A//www.myblog.com/rss' + \
               '&description1=My%A0Blog') # %A0 is not correct here

        feeds = subscription.find_subscribe_links(url)
        self.assertEquals(feeds, [
            {'url': u'http://www.myblog.com/rss', 'type': 'feed',
                'description': u'My\ufffdBlog'}] # fffd is the ? character
        )

    def test_download_links(self):
        url = ('http://subscribe.getdemocracy.com/download.php' +
               '?url1=http%3A//www.myblog.com/videos/cats.ogm')
        self.assertEquals(subscription.find_subscribe_links(url),
                [{'type': 'download',
                  'url': 'http://www.myblog.com/videos/cats.ogm'}])

class Testis_subscribe_links(MiroTestCase):
    def test_garbage(self):
        is_s_l = subscription.is_subscribe_link
        self.assertEquals(is_s_l(None), False)
        self.assertEquals(is_s_l(1), False)
        self.assertEquals(is_s_l({}), False)

    def test_negative(self):
        is_s_l = subscription.is_subscribe_link
        self.assertEquals(is_s_l('http://example.com/'), False)
        self.assertEquals(is_s_l('foobar'), False)

    def test_positive(self):
        is_s_l = subscription.is_subscribe_link
        self.assertEquals(is_s_l('http://subscribe.getdemocracy.com/'), True)

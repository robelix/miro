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

"""Sanity checks for the databases.

.. Note::

    This module is deprecated: database sanity checking is done by the
    ``check_constraints`` method on DDBObjects.  This is a better way
    to do things because it will catch errors right when we save
    objects, instead of some unknown point in the future.  We still
    have this code around, because it's used to do sanity checks on
    old databases in ``convert20database``.
"""

from miro import item
from miro import feed
from miro import signals

class DatabaseInsaneError(StandardError):
    pass

class SanityTest(object):
    """Base class for the sanity test objects."""

    def check_object(self, obj):
        """``check_object`` will be called for each object in the
        object list.  If there is an error return a string describing
        it.  If not return None (or just let the function hit the
        bottom).
        """
        raise NotImplementedError()

    def finished(self):
        """Called when we reach the end of the object list,
        ``SanityTest`` subclasses may implement additional checking
        here.
        """
        return

    def fix_if_possible(self, object_list):
        """Subclasses may implement this method if it's possible to
        fix broken databases.  The default implementation just raises
        a ``DatabaseInsaneError``.
        """
        raise DatabaseInsaneError()

class PhantomFeedTest(SanityTest):
    """Check that no items reference a Feed that isn't around anymore.
    """
    def __init__(self):
        self.feeds_in_items = set()
        self.top_level_feeds = set()
        self.parents_in_items = set()
        self.top_level_parents = set()

    def check_object(self, obj):
        if isinstance(obj, item.Item):
            if obj.feed_id is not None:
                self.feeds_in_items.add(obj.feed_id)
            if obj.parent_id is not None:
                self.parents_in_items.add(obj.parent_id)
            if obj.is_container_item in (None, True):
                self.top_level_parents.add(obj.id)
        elif isinstance(obj, feed.Feed):
            self.top_level_feeds.add(obj.id)

    def finished(self):
        if not self.feeds_in_items.issubset(self.top_level_feeds):
            phantoms = self.feeds_in_items.difference(self.top_level_feeds)
            phantoms_string = ', '.join([str(p) for p in phantoms])
            return "Phantom podcast(s) referenced in items: %s" % phantoms_string
        if not self.parents_in_items.issubset(self.top_level_parents):
            phantoms = self.parents_in_items.difference(self.top_level_parents)
            phantoms_string = ', '.join([str(p) for p in phantoms])
            return "Phantom items(s) referenced in items: %s" % phantoms_string

    def fix_if_possible(self, object_list):
        for i in reversed(xrange(len(object_list))):
            if ((isinstance(object_list[i], item.Item) and
                 object_list[i].feed_id is not None and
                 object_list[i].feed_id not in self.top_level_feeds)):
                del object_list[i]
            elif (isinstance(object_list[i], item.Item) and
                  object_list[i].parent_id is not None and
                  object_list[i].parent_id not in self.top_level_parents):
                del object_list[i]

class SingletonTest(SanityTest):
    """Check that singleton DB objects are really singletons.

    This is a baseclass for the manual feed test, etc.
    """
    singleton_name = ""

    def __init__(self):
        self.count = 0

    def object_is_singleton(self, obj):
        raise NotImplementedError()

    def check_object(self, obj):
        if self.object_is_singleton(obj):
            self.count += 1
            if self.count > 1:
                return "Extra %s in database" % self.singleton_name

    def finished(self):
        if self.count == 0:
            # For all our singletons (currently at least), we don't need to
            # create them here.  It'll happen when Miro is restarted.
            # return "No %s in database" % self.singleton_name
            pass

    def fix_if_possible(self, object_list):
        if self.count == 0:
            # For all our singletons (currently at least), we don't need to
            # create them here.  It'll happen when Miro is restarted.
            return
        else:
            seen_object = False
            for i in reversed(xrange(len(object_list))):
                if self.object_is_singleton(object_list[i]):
                    if seen_object:
                        del object_list[i]
                    else:
                        seen_object = True

class ManualFeedSingletonTest(SingletonTest):
    singleton_name = "Manual Feed"
    def object_is_singleton(self, obj):
        return (isinstance(obj, feed.Feed) and
                isinstance(obj.actualFeed, feed.ManualFeedImpl))

def check_sanity(object_list, fix_if_possible=True, quiet=False,
                 really_quiet=False):
    """Do all sanity checks on a list of objects.

    If fix_if_possible is True, the sanity checks will try to fix
    errors.  If this happens object_list will be modified.

    If fix_if_possible is False, or if it's not possible to fix the
    errors check_sanity will raise a DatabaseInsaneError.

    If quiet is True, we print to the log instead of poping up an
    error dialog on fixable problems.  We set this when we are
    converting old databases, since sanity errors are somewhat
    expected.

    If really_quiet is True, won't even print out a warning on fixable
    problems.

    Returns True if the database passed all sanity tests, false
    otherwise.
    """
    tests = set([
        PhantomFeedTest(),
        ManualFeedSingletonTest(),
    ])

    errors = []
    failed_tests = set()
    for obj in object_list:
        for test in tests:
            rv = test.check_object(obj)
            if rv is not None:
                errors.append(rv)
                failed_tests.add(test)
        tests = tests.difference(failed_tests)
    for test in tests:
        rv = test.finished()
        if rv is not None:
            errors.append(rv)
            failed_tests.add(test)

    if errors:
        error = "The database failed the following sanity tests:\n"
        error += "\n".join(errors)
        if fix_if_possible:
            if not quiet:
                signals.system.failed(when="While checking database",
                                      details=error)
            elif not really_quiet:
                print "WARNING: Database sanity error"
                print error
            for test in failed_tests:
                test.fix_if_possible(object_list)
                # fix_if_possible will throw a DatabaseInsaneError if
                # it fails, which we let get raised to our caller
        else:
            raise DatabaseInsaneError(error)
    return (errors == [])

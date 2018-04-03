from datetime import datetime
import os
import unittest
import string
import random
import time

import sqlite3

from miro import app
from miro import database
from miro import databaseupgrade
from miro import devices
from miro import dialogs
from miro import downloader
from miro import item
from miro import feed
from miro import folder
from miro import widgetstate
from miro import schema
from miro import signals
from miro import tabs
from miro import theme
from miro.fileobject import FilenameType
import shutil
from miro import storedatabase
from miro.plat import resources
from miro.plat.utils import PlatformFilenameType

from miro.test import mock
from miro.test.framework import (MiroTestCase, EventLoopTest,
                                 skip_for_platforms, MatchAny)
from miro.schema import (SchemaString, SchemaInt, SchemaFloat,
                         SchemaReprContainer, SchemaList, SchemaDict,
                         SchemaBool, SchemaFilename,
                         SchemaBinary, SchemaStringSet)

# create a dummy object schema
class Human(database.DDBObject):
    def setup_new(self, name, age, meters_tall, friends, high_scores=None,
                  **stuff):
        self.name = name
        self.age = age
        self.meters_tall = meters_tall
        self.friends = friends
        self.friend_names = [f.name for f in friends]
        if high_scores is None:
            self.high_scores = {}
        else:
            self.high_scores = high_scores
        self.stuff = stuff
        self.id_code = None
        self.favorite_colors = set([u'red', u'blue'])

    def add_friend(self, friend):
        self.friends.append(friend)
        self.friend_names.append(friend.name)

class RestorableHuman(Human):
    def setup_restored(self):
        self.iveBeenRestored = True

class DBInsertCallbackHuman(Human):
    callback = None
    def on_db_insert(self):
        if self.__class__.callback:
            self.__class__.callback(self)

class PCFProgramer(Human):
    def setup_new(self, name, age, meters_tall, friends, file, developer,
            high_scores = None):
        Human.setup_new(self, name, age, meters_tall, friends, high_scores)
        self.file = file
        self.developer = developer

class SpecialProgrammer(PCFProgramer):
    def setup_new(self):
        PCFProgramer.setup_new(self, u'I.M. Special', 44, 2.1, [],
                               PlatformFilenameType(
                               '/home/specialdude/\u1234'.encode("utf-8")),
                               True)

class HumanSchema(schema.ObjectSchema):
    klass = Human
    table_name = 'human'
    fields = [
        ('id', SchemaInt()),
        ('name', SchemaString()),
        ('age', SchemaInt()),
        ('meters_tall', SchemaFloat()),
        ('friend_names', SchemaList(SchemaString())),
        ('high_scores', SchemaDict(SchemaString(), SchemaInt())),
        ('stuff', SchemaReprContainer(noneOk=True)),
        ('id_code', SchemaBinary(noneOk=True)),
        ('favorite_colors', SchemaStringSet(delimiter='@')),
    ]

    @staticmethod
    def handle_malformed_stuff(row):
        return 'testing123'

class RestorableHumanSchema(HumanSchema):
    klass = RestorableHuman
    table_name = 'restorable_human'

class DBInsertCallbackHumanSchema(HumanSchema):
    klass = DBInsertCallbackHuman
    table_name = 'db_insert_callback_human'

class PCFProgramerSchema(schema.MultiClassObjectSchema):
    table_name = 'pcf_programmer'
    fields = HumanSchema.fields + [
        ('file', SchemaFilename()),
        ('developer', SchemaBool()),
    ]

    @classmethod
    def ddb_object_classes(cls):
        return (PCFProgramer, SpecialProgrammer)

    @classmethod
    def get_ddb_class(cls, restored_data):
        if restored_data['name'] == 'I.M. Special':
            return SpecialProgrammer
        else:
            return PCFProgramer

test_object_schemas = [HumanSchema, PCFProgramerSchema, RestorableHumanSchema,
        DBInsertCallbackHumanSchema]

def upgrade1(cursor):
    cursor.execute("UPDATE human set name='new name'")

def upgrade2(cursor):
    1 / 0

class StoreDatabaseTest(EventLoopTest):
    OBJECT_SCHEMAS = None

    def setUp(self):
        EventLoopTest.setUp(self)
        self.save_path = FilenameType(self.make_temp_path(extension=".db"))
        self.remove_database()
        self.reload_test_database()

    def reload_test_database(self, version=0):
        self.reload_database(self.save_path, schema_version=version,
                object_schemas=self.OBJECT_SCHEMAS)

    def remove_database(self):
        if os.path.exists(self.save_path):
            os.unlink(self.save_path)

    def tearDown(self):
        # need to close the db before removing it from disk
        app.db.close()
        self.remove_database()
        corrupt_path = os.path.join(os.path.dirname(self.save_path),
                                    'corrupt_database')
        if os.path.exists(corrupt_path):
            os.remove(corrupt_path)
        databaseupgrade._upgrade_overide = {}
        EventLoopTest.tearDown(self)

class EmptyDBTest(StoreDatabaseTest):
    def test_open_empty_db(self):
        self.reload_test_database()
        app.db.cursor.execute("SELECT name FROM main.sqlite_master "
                "WHERE type='table'")
        for row in app.db.cursor.fetchall():
            table = row[0]
            if table == 'dtv_variables':
                correct_count = 1
            else:
                correct_count = 0
            app.db.cursor.execute("SELECT count(*) FROM %s" % table)
            self.assertEquals(app.db.cursor.fetchone()[0], correct_count)

class DBUpgradeTest(StoreDatabaseTest):
    def setUp(self):
        StoreDatabaseTest.setUp(self)
        self.save_path2 = self.make_temp_path()

    def tearDown(self):
        try:
            os.unlink(self.save_path2)
        except OSError:
            pass
        StoreDatabaseTest.tearDown(self)

    def load_fresh_database(self):
        self.remove_database()
        self.reload_database()
        self.db = app.db

    def load_upgraded_database(self):
        shutil.copy(resources.path("testdata/olddatabase.v79"),
                    self.save_path2)
        self.reload_database(self.save_path2)
        self.db = app.db

    @skip_for_platforms('win32')
    def test_indexes_same(self):
        # this fails on windows because it's using a non-Windows
        # database
        self.load_fresh_database()
        self.db.cursor.execute("SELECT name FROM main.sqlite_master "
                               "WHERE type='index'")
        blank_db_indexes = set(self.db.cursor)
        self.load_upgraded_database()
        self.db.cursor.execute("SELECT name FROM main.sqlite_master "
                               "WHERE type='index'")
        upgraded_db_indexes = set(self.db.cursor)
        self.assertEquals(upgraded_db_indexes, blank_db_indexes)

    @skip_for_platforms('win32')
    def test_triggers_same(self):
        # this fails on windows because it's using a non-Windows
        # database
        self.load_fresh_database()
        self.db.cursor.execute("SELECT name, sql FROM main.sqlite_master "
                               "WHERE type='trigger'")
        blank_db_indexes = set(self.db.cursor)
        self.load_upgraded_database()
        self.db.cursor.execute("SELECT name, sql FROM main.sqlite_master "
                               "WHERE type='trigger'")
        upgraded_db_indexes = set(self.db.cursor)
        self.assertEquals(upgraded_db_indexes, blank_db_indexes)

    @skip_for_platforms('win32')
    def test_schema_same(self):
        # this fails on windows because it's using a non-Windows
        # database
        self.load_fresh_database()
        blank_column_types = self._get_column_types()
        self.load_upgraded_database()
        upgraded_column_types = self._get_column_types()
        self.assertEquals(set(blank_column_types.keys()),
                          set(upgraded_column_types.keys()))
        for table_name in blank_column_types:
            diff = blank_column_types[table_name].symmetric_difference(
                upgraded_column_types[table_name])
            if diff:
                raise AssertionError("different column types for %s (%s)" %
                                     (table_name, diff))

    def _get_column_types(self):
        self.db.cursor.execute("SELECT name FROM main.sqlite_master "
                              "WHERE type='table'")
        rv = {}
        for table_name in [r[0] for r in self.db.cursor.fetchall()]:
            self.db.cursor.execute('pragma table_info(%s)' % table_name)
            rv[table_name] = set((r[1], r[2].lower()) for r in self.db.cursor)
        return rv

class DeviceDBUpgradeTest(DBUpgradeTest):
    def setUp(self):
        StoreDatabaseTest.setUp(self)
        self.save_path2 = self.make_temp_path()

    def tearDown(self):
        try:
            os.unlink(self.save_path2)
        except OSError:
            pass
        StoreDatabaseTest.tearDown(self)

    def load_fresh_database(self):
        device_mount = self.make_temp_dir_path()
        os.makedirs(os.path.join(device_mount, '.miro'))
        self.db = devices.load_sqlite_database(device_mount, 1024)

    def load_upgraded_database(self):
        device_mount = self.make_temp_dir_path()
        os.makedirs(os.path.join(device_mount, '.miro'))
        shutil.copyfile(resources.path('testdata/5.x-device-database.sqlite'),
                        os.path.join(device_mount, '.miro', 'sqlite'))
        self.db = devices.load_sqlite_database(device_mount, 1024)

class FakeSchemaTest(StoreDatabaseTest):
    OBJECT_SCHEMAS = test_object_schemas

    def setUp(self):
        StoreDatabaseTest.setUp(self)
        self.lee = Human(u"lee", 25, 1.4, [], {u'virtual bowling': 212})
        self.joe = RestorableHuman(u"joe", 14, 1.4, [self.lee], car=u'toyota',
                                   dog=u'scruffy')
        self.ben = PCFProgramer(u'ben', 25, 3.4, [self.joe],
                                PlatformFilenameType(
                                '/home/ben/\u1234'.encode("utf-8")), True)
        self.db = [self.lee, self.joe, self.ben]
        databaseupgrade._upgrade_overide[1] = upgrade1
        databaseupgrade._upgrade_overide[2] = upgrade2

class DiskTest(FakeSchemaTest):
    def setUp(self):
        FakeSchemaTest.setUp(self)
        # should we handle upgrade error dialogs by clicking "start fresh"
        self.handle_upgrade_error_dialogs = False
        # should we handle database corrupt message boxes by clicking "OK?"
        self.handle_corruption_dialogs = False

    def check_database(self):
        obj_map = {}
        for klass in (PCFProgramer, RestorableHuman, Human):
            obj_map.update(dict((obj.id, obj) for obj in klass.make_view()))
        self.assertEquals(len(self.db), len(obj_map))
        for obj in self.db:
            if isinstance(obj, PCFProgramer):
                schema = PCFProgramerSchema
            elif isinstance(obj, RestorableHuman):
                schema = RestorableHumanSchema
            elif isinstance(obj, Human):
                schema = HumanSchema
            else:
                raise AssertionError("Unknown object type: %r" % obj)

            db_object = obj_map[obj.id]
            self.assertEquals(db_object.__class__, obj.__class__)
            for name, schema_item in schema.fields:
                db_value = getattr(db_object, name)
                obj_value = getattr(obj, name)
                if db_value != obj_value or type(db_value) != type(obj_value):
                    raise AssertionError("%r != %r (attr: %s)" % (db_value,
                        obj_value, name))

    def test_create(self):
        # Test that the database we set up in __init__ restores
        # correctly
        self.reload_test_database()
        self.check_database()

    def test_update(self):
        self.joe.name = u'JO MAMA'
        self.joe.signal_change()
        self.reload_test_database()
        self.check_database()

    def test_binary_reload(self):
        self.joe.id_code = 'abc'
        self.joe.signal_change()
        self.reload_test_database()
        self.check_database()

    def test_remove(self):
        self.joe.remove()
        self.db = [ self.lee, self.ben]
        self.reload_test_database()
        self.check_database()

    def test_update_then_remove(self):
        self.joe.name = u'JO MAMA'
        self.joe.remove()
        self.db = [ self.lee, self.ben]
        self.reload_test_database()
        self.check_database()

    def test_schema_repr(self):
        self.joe.stuff = {
            '1234': datetime.now(),
            # matches the fix in feedparser which explicitly converts
            # time.struct_time to a 9-tuple because of Python 2.6.
            None: tuple(time.localtime()),
            u'booya': 23.0
            }
        self.joe.signal_change()
        self.reload_test_database()
        self.check_database()

    def test_setup_restored(self):
        self.assert_(not hasattr(self.joe, 'iveBeenRestored'))
        self.reload_test_database()
        restored_joe = RestorableHuman.get_by_id(self.joe.id)
        self.assert_(restored_joe.iveBeenRestored)

    def test_single_table_inheritance(self):
        # test loading different classes based on the row data
        im_special = SpecialProgrammer()
        self.db.append(im_special)
        self.reload_test_database()
        self.check_database()
        # check deleting the different class
        im_special = self.reload_object(im_special)
        im_special.remove()
        self.db.pop()
        self.reload_test_database()
        self.check_database()

    def test_commit_without_close(self):
        app.db.finish_transaction()
        # close the database connection without giving LiveStorage the
        # oppertunity to commit when it's closed.
        app.db.connection.close()
        self.setup_new_database(self.save_path, schema_version=0,
                object_schemas=self.OBJECT_SCHEMAS)
        app.db.upgrade_database()
        database.initialize()
        self.check_database()

    def test_upgrade(self):
        self.reload_test_database(version=1)
        new_lee = Human.get_by_id(self.lee.id)
        self.assertEquals(new_lee.name, 'new name')
        # check that we created a backup file
        backup_path = os.path.join(os.path.dirname(self.save_path),
                                   'dbbackups', 'sqlitedb_backup_0')
        if not os.path.exists(backup_path):
            raise AssertionError("database backup doesn't exist")
        # check that the backup has the old data
        backup_conn = sqlite3.connect(backup_path)
        cursor = backup_conn.execute("SELECT name FROM human WHERE id=?",
                                     (self.lee.id,))
        backup_lee_name = cursor.fetchone()[0]
        self.assertEquals(backup_lee_name, 'lee')

    def test_restore_with_newer_version(self):
        self.reload_test_database(version=1)
        self.assertRaises(databaseupgrade.DatabaseTooNewError,
                self.reload_test_database, version=0)

    def test_make_new_id(self):
        # Check that when we reload the database, the id counter stays the
        # same
        org_id = app.db_info.make_new_id()
        # reload the database
        self.reload_test_database()
        self.assertEquals(app.db_info.make_new_id(), org_id)

    def check_reload_error(self, **reload_args):
        corrupt_path = os.path.join(os.path.dirname(self.save_path),
                                    'corrupt_database')
        self.assert_(not os.path.exists(corrupt_path))
        self.allow_db_load_errors(True)
        with self.allow_warnings():
            self.reload_test_database(**reload_args)
        self.allow_db_load_errors(False)
        self.assert_(os.path.exists(corrupt_path))

    def handle_dialogs(self, upgrade, corruption):
        """Handle the dialogs that we pop up when we notice database errors.

        :param upgrade: handle upgrade dialogs by clicking "start fresh"
        :param corruption: handle database corrupt message boxes
        """
        self.allow_db_upgrade_error_dialog = True
        self.handle_upgrade_error_dialogs = upgrade
        self.handle_corruption_dialogs = corruption

    def handle_new_dialog(self, obj, dialog):
        if (self.handle_upgrade_error_dialogs and
            (dialogs.BUTTON_START_FRESH in dialog.buttons)):
            # handle database upgrade dialog
            dialog.run_callback(dialogs.BUTTON_START_FRESH)
        elif (self.handle_corruption_dialogs and
              isinstance(dialog, dialogs.MessageBoxDialog)):
            # handle the load error dialog
            dialog.run_callback(dialogs.BUTTON_OK)
        else:
            return FakeSchemaTest.handle_new_dialog(self, obj, dialog)

    def test_upgrade_error(self):
        self.handle_dialogs(upgrade=True, corruption=False)
        with self.allow_warnings():
            self.check_reload_error(version=2)

    def test_corrupt_database(self):
        app.db.close()
        open(self.save_path, 'wb').write("BOGUS DATA")
        # depending on the SQLite version, we will notice the error when we
        # issup the PRAGMA journal_mode command, or when we do the upgrades.
        # Handle the dialogs for both.
        self.handle_dialogs(upgrade=True, corruption=True)
        self.check_reload_error()

    def test_database_data_error(self):
        app.db.cursor.execute("DROP TABLE human")
        self.handle_dialogs(upgrade=False, corruption=True)
        self.check_reload_error()

    def test_bulk_insert(self):
        new_humans = []
        app.bulk_sql_manager.start()
        # nothing should be inserted yet
        for x in range(10):
            name = u"lee-clone-%s" % x
            new_humans.append(Human(name, 25, 1.4, [], {u'virtual bowling':
                                                        212}))
        self.check_database()
        self.assertEquals(Human.make_view().count(), 1)
        app.bulk_sql_manager.finish()
        # calling finish() should insert the new Humans
        self.db.extend(new_humans)
        self.check_database()
        self.assertEquals(Human.make_view().count(), 11)

    def test_bulk_remove(self):
        new_humans = []
        for x in range(10):
            name = u"lee-clone-%s" % x
            new_humans.append(Human(name, 25, 1.4, [], {u'virtual bowling':
                                                        212}))
        self.assertEquals(Human.make_view().count(), 11)
        app.bulk_sql_manager.start()
        for new_dude in new_humans:
            new_dude.remove()
        self.assertEquals(Human.make_view().count(), 11)
        app.bulk_sql_manager.finish()
        self.assertEquals(Human.make_view().count(), 1)

    def test_insert_during_on_insert(self):
        # what happens if on_db_insert creates a new item (see #12680)
        def insert_callback(obj):
            Human(u'minnie', 25, 1.4, [], {})
        DBInsertCallbackHuman.callback = insert_callback
        app.bulk_sql_manager.start()
        ben = DBInsertCallbackHuman(u'janet', 25, 1.4, [], {})
        # calling finish() will invoke insert_callback and create minnie.
        # Check that this is reflected on disk
        self.assertEquals(Human.make_view().count(), 1)
        app.bulk_sql_manager.finish()
        self.assertEquals(Human.make_view().count(), 2)

    def test_bulk_insert_with_signal_change(self):
        app.bulk_sql_manager.start()
        # nothing should be inserted yet
        lee2 = Human(u'lee2', 25, 1.4, [], {u'virtual bowling': 212})
        lee2.name = u'lee2-changed'
        # calling signal_change() shouldn't throw an exception like it did in
        # ticket #12806
        lee2.signal_change()
        app.bulk_sql_manager.finish()
        # double check that the new name is the correct one.
        lee2 = self.reload_object(lee2)
        self.assertEqual(lee2.name, u'lee2-changed')

    def test_bulk_insert_and_remove(self):
        # test inserting, then removing an object while in bulk mode
        app.bulk_sql_manager.start()
        # nothing should be inserted yet
        lee = Human(u'lee', 25, 1.4, [], {u'virtual bowling': 212})
        lee.remove()
        # lee was inserted, then removed while inside a bulk transaction,
        # make sure things are cleaned up correctly (#17428)
        app.bulk_sql_manager.finish()
        self.assert_(not lee.id_exists())
        self.assert_(lee.id not in app.db._object_map)
        lee_view = Human.make_view("id=?", values=(lee.id,))
        self.assertEquals(lee_view.count(), 0)

class ObjectMemoryTest(FakeSchemaTest):
    def test_remove_remove_object_map(self):
        self.reload_test_database()
        # no objects should be loaded yet
        self.assertEquals(0, len(app.db._object_map))
        # test object loading
        lee = Human.make_view().get_singleton()
        self.assertEquals(1, len(app.db._object_map))
        joe = RestorableHuman.make_view().get_singleton()
        self.assertEquals(2, len(app.db._object_map))
        # test object removal
        joe.remove()
        self.assertEquals(1, len(app.db._object_map))
        lee.remove()
        self.assertEquals(0, len(app.db._object_map))

class ValidationTest(FakeSchemaTest):
    def assert_object_valid(self, obj):
        obj.signal_change()

    def assert_object_invalid(self, obj):
        with self.allow_warnings():
            self.assertRaises(schema.ValidationError, obj.signal_change)

    def test_none_values(self):
        self.lee.age = None
        self.assert_object_invalid(self.lee)
        self.lee.age = 25
        self.lee.stuff = None
        self.assert_object_valid(self.lee)

    def test_int_validation(self):
        self.lee.age = '25'
        self.assert_object_invalid(self.lee)
        self.lee.age = 25L
        self.assert_object_valid(self.lee)

    def test_string_validation(self):
        self.lee.name = 133
        self.assert_object_invalid(self.lee)
        self.lee.name = u'lee'
        self.assert_object_valid(self.lee)

    def test_binary_validation(self):
        self.lee.id_code = u'abc'
        self.assert_object_invalid(self.lee)
        self.lee.id_code = 'abc'
        self.assert_object_valid(self.lee)

    def test_float_validation(self):
        self.lee.meters_tall = 3
        self.assert_object_invalid(self.lee)

    def test_list_validation(self):
        self.lee.friend_names = [1234]
        self.assert_object_invalid(self.lee)

    def test_dict_validation(self):
        self.joe.high_scores['pong'] = u"One Million"
        self.assert_object_invalid(self.joe)
        del self.joe.high_scores['pong']
        self.joe.high_scores[1943] = 1234123
        self.assert_object_invalid(self.joe)

class CorruptReprTest(FakeSchemaTest):
    # Test what happens when SchemaReprContainer objects have bad data
    # (#12028)
    def test_repr_failure(self):
        app.db.cursor.execute("UPDATE human SET stuff='{baddata' "
                              "WHERE name='lee'")
        with self.allow_warnings():
            restored_lee = self.reload_object(self.lee)
        self.assertEqual(restored_lee.stuff, 'testing123')
        app.db.cursor.execute("SELECT stuff from human WHERE name='lee'")
        row = app.db.cursor.fetchone()
        self.assertEqual(row[0], "'testing123'")

    def test_repr_failure_no_handler(self):
        app.db.cursor.execute("UPDATE pcf_programmer SET stuff='{baddata' "
                              "WHERE name='ben'")
        with self.allow_warnings():
            self.assertRaises(SyntaxError, self.reload_object, self.ben)

class ConverterTest(StoreDatabaseTest):
    def test_convert_repr(self):
        converter = storedatabase.SQLiteConverter()
        # _repr_to_sql ignores the schema_item parameter, so we can just pass
        # in None
        schema_item = None

        test1 = """{'updated_parsed': (2009, 6, 5, 1, 30, 0, 4, 156, 0)}"""
        val = converter._repr_from_sql(test1, schema_item)
        self.assertEquals(val, {"updated_parsed":
                                (2009, 6, 5, 1, 30, 0, 4, 156, 0)})

        test2 = """{'updated_parsed': time.struct_time(tm_year=2009, \
tm_mon=6, tm_mday=5, tm_hour=1, tm_min=30, tm_sec=0, tm_wday=4, tm_yday=156, \
tm_isdst=0)}"""
        val = converter._repr_from_sql(test2, schema_item)
        self.assertEquals(val, {"updated_parsed":
                                (2009, 6, 5, 1, 30, 0, 4, 156, 0)})

class CorruptDDBObjectReprTest(StoreDatabaseTest):
    # test corrupt SchemaReprContainer columns in real DDBObjects
    def setUp(self):
        StoreDatabaseTest.setUp(self)
        self.feed = feed.Feed(u"dtv:savedsearch/all?q=dogs")
        self.item = item.Item(item.FeedParserValues({'title': u'item1'}),
                       feed_id=self.feed.id)
        self.downloader = downloader.RemoteDownloader(
            u'http://example.com/1/item1/movie.mpeg', self.item)
        self.item.set_downloader(self.downloader)
        self.tab_order = tabs.TabOrder(u'channel')
        self.theme_hist = theme.ThemeHistory()
        self.view_state = widgetstate.ViewState((u'testtype', u'testid', 0))

    def check_fixed_value(self, obj, column_name, value, disk_value=None):
        with self.allow_warnings():
            obj = self.reload_object(obj)
        self.assertEquals(getattr(obj, column_name), value)
        # make sure the values stored on disk are correct as well
        if disk_value is None:
            disk_value = value
        obj_schema = app.db._schema_map[obj.__class__]
        app.db.cursor.execute("SELECT %s FROM %s WHERE id=?" % (column_name,
            obj_schema.table_name), (obj.id,))
        row = app.db.cursor.fetchone()
        for name, schema_item in obj_schema.fields:
            if name == column_name:
                break
        sql_value = app.db._converter.to_sql(obj_schema, column_name,
                schema_item, disk_value)
        self.assertEqual(row[0], sql_value)

    def test_corrupt_etag(self):
        app.db.cursor.execute("UPDATE saved_search_feed_impl "
                "SET etag='{baddata' WHERE ufeed_id=?", (self.feed.id,))
        self.check_fixed_value(self.feed.actualFeed, 'etag', {})

    def test_corrupt_modified(self):
        app.db.cursor.execute("UPDATE saved_search_feed_impl "
                "SET modified='{baddata' WHERE ufeed_id=?", (self.feed.id,))
        self.check_fixed_value(self.feed.actualFeed, 'modified', {})

    def test_corrupt_tab_ids(self):
        app.db.cursor.execute("UPDATE taborder_order "
                "SET tab_ids='[1, 2; 3 ]' WHERE id=?", (self.tab_order.id,))
        with self.allow_warnings():
            reloaded = self.reload_object(self.tab_order)
        self.check_fixed_value(reloaded, 'tab_ids', [])
        # check that restore_tab_list() re-adds the tab ids
        reloaded.restore_tab_list()
        self.check_fixed_value(reloaded, 'tab_ids', [self.feed.id])

    def test_corrupt_past_themes(self):
        app.db.cursor.execute("UPDATE theme_history "
                "SET pastThemes='[1, 2; 3 ]' WHERE id=?",
                              (self.theme_hist.id,))
        self.check_fixed_value(self.theme_hist, 'pastThemes', [])

    def test_corrupt_view_state(self):
        app.db.cursor.execute("UPDATE view_state SET "
                "columns_enabled=?, column_widths=? WHERE id=?",
                ('{baddata', '{baddata', self.view_state.id))
        self.check_fixed_value(self.view_state, 'columns_enabled', None)
        self.check_fixed_value(self.view_state, 'column_widths', None)

    def test_corrupt_link_history(self):
        # TODO: should test ScraperFeedIpml.linkHistory, but it's not so easy
        # to create a ScraperFeedIpml in the unit tests.
        pass

class BadTabOrderTest(StoreDatabaseTest):
    # Test TabOrder objects with the wrong order
    def setUp(self):
        StoreDatabaseTest.setUp(self)
        self.f1 = feed.Feed(u"http://example.com/1")
        self.f2 = feed.Feed(u"http://example.com/2")
        self.folder = folder.ChannelFolder(u'test channel folder')
        self.tab_order = tabs.TabOrder(u'channel')

    def screw_with_tab_order(self, *tab_ids):
        app.db.cursor.execute("UPDATE taborder_order "
                "SET tab_ids=? WHERE id=?",
                (repr(list(tab_ids)), self.tab_order.id,))

    def check_order(self, *tab_ids):
        self.tab_order = self.reload_object(self.tab_order)
        self.tab_order.restore_tab_list()
        self.assertEqual(self.tab_order.tab_ids, list(tab_ids))

    def test_missing_tab_ids(self):
        self.screw_with_tab_order(self.f1.id, self.folder.id)
        self.check_order(self.f1.id, self.folder.id, self.f2.id)

    def test_missing_folder_ids(self):
        self.screw_with_tab_order(self.f1.id, self.f2.id)
        self.check_order(self.f1.id, self.f2.id, self.folder.id)

    def test_extra_tab_ids(self):
        self.screw_with_tab_order(self.f1.id, self.f2.id, self.folder.id, 123)
        with self.allow_warnings():
            self.check_order(self.f1.id, self.f2.id, self.folder.id)

    def test_order_wrong(self):
        self.f1.set_folder(self.folder)
        self.check_order(self.f2.id, self.folder.id, self.f1.id)
        # f1 should follow it's parent, check that we fix things if that's not
        # true
        self.screw_with_tab_order(self.f1.id, self.f2.id, self.folder.id)
        self.check_order(self.f2.id, self.folder.id, self.f1.id)

class PreallocateTest(MiroTestCase):
    def check_preallocate_size(self, path, preallocate_size):
        disk_size = os.stat(path).st_size
        # allow some variance for the disk size, we just need to be in the
        # ballpark
        self.assertClose(disk_size, preallocate_size)

    def test_preallocate(self):
        # test preallocating space
        preallocate = 512 * 1024 # 512KB
        path = os.path.join(self.tempdir, 'testdb')
        storage = storedatabase.LiveStorage(path, preallocate=preallocate)
        # check while open
        self.check_preallocate_size(path, preallocate)
        # check that it remains that big after close
        storage.close()
        self.check_preallocate_size(path, preallocate)

class TemporaryModeTest(MiroTestCase):
    # test getting an error when opening a new database and using an
    # in-memory database to work around it

    def setUp(self):
        MiroTestCase.setUp(self)
        self.save_path = os.path.join(self.tempdir, 'test-db')
        # set up an error handler that tells LiveStorage to use temporary
        # storage if it fails to open a new database
        use_temp = storedatabase.LiveStorageErrorHandler.ACTION_USE_TEMPORARY
        self.error_handler = mock.Mock()
        self.error_handler.handle_open_error.return_value = use_temp

        self.row_data = []

        self.mock_add_timeout = mock.Mock()
        self.patch_function('miro.eventloop.add_timeout',
                            self.mock_add_timeout)

        self.real_sqlite3_connect = sqlite3.connect
        self.patch_function('sqlite3.connect', self.mock_sqlite3_connect)

    def force_temporary_database(self):
        """Open a new database and force it to fail.

        After this we should be using an in-memory database and trying to save
        it to disk every so often.
        """

        self.force_next_connect_to_fail = True
        with self.allow_warnings():
            self.reload_database(self.save_path,
                                 object_schemas=test_object_schemas,
                                 error_handler=self.error_handler)

    def test_error_handler_called(self):
        # Test that our error handler was called when storedatabase could'nt
        # open the database
        handle_open_error = self.error_handler.handle_open_error
        self.force_temporary_database()
        handle_open_error.assert_called_once_with()

    def test_use_memory(self):
        # Test that we use an in-memory database after failing to open a real
        # one
        self.force_temporary_database()
        self.assertEquals(self.last_connect_path, ':memory:')
        self.assert_(not os.path.exists(self.save_path))

    def test_try_save_scheduling(self):
        # test that we call add_timeout to schedule trying to save to the
        # database
        self.force_temporary_database()
        delay = 300
        self.mock_add_timeout.assert_called_once_with(
            delay, app.db._try_save_temp_to_disk, MatchAny())
        # Make the timeout run and fail.  Check that we schedule another try
        self.mock_add_timeout.reset_mock()
        self.force_next_connect_to_fail = True
        with self.allow_warnings():
            app.db._try_save_temp_to_disk()
        self.mock_add_timeout.assert_called_once_with(
            delay, app.db._try_save_temp_to_disk, MatchAny())
        # make the timeout succeed.  Check that we don't schedule anymore
        self.mock_add_timeout.reset_mock()
        app.db._try_save_temp_to_disk()
        self.assertEquals(self.mock_add_timeout.called, False)

    def add_data(self, row_count):
        for i in range(row_count):
            age = 40
            meters_tall = 2.5
            name = u"Name-%s" % i
            password = u"x" * i
            Human(name, age, meters_tall, [], password=password)
            self.row_data.append((name, age, meters_tall, password))

    def check_data(self):
        view = Human.make_view(order_by="name")
        self.row_data.sort() # name is the 1st column, so this sorts by name
        self.assertEquals(view.count(), len(self.row_data))
        for i, h in enumerate(view):
            self.assertEquals(h.name, self.row_data[i][0])
            self.assertEquals(h.age, self.row_data[i][1])
            self.assertEquals(h.meters_tall, self.row_data[i][2])
            self.assertEquals(h.stuff, {'password': self.row_data[i][3]})

    def test_data(self):
        # test storing data in the temp database
        self.force_temporary_database()
        # add a bunch of fake data to the database
        self.add_data(100)
        # make the database save to its real path
        with self.allow_warnings():
            app.db._try_save_temp_to_disk()
        # check that the data got saved to disk
        self.assertEquals(self.last_connect_path, self.save_path)
        self.assert_(os.path.exists(self.save_path))
        # test that the data is correct immediately after change_path
        self.check_data()
        # add some more data
        self.add_data(100)
        # re-open the database and check that everything is correct
        self.reload_database(self.save_path, object_schemas=test_object_schemas)
        self.check_data()

    def mock_sqlite3_connect(self, path, *args, **kwargs):
        """Force the next call to sqlite3.connect to raise an exception.  """
        if self.force_next_connect_to_fail:
            self.force_next_connect_to_fail = False
            raise sqlite3.OperationalError()
        else:
            self.last_connect_path = path
            return self.real_sqlite3_connect(path, *args, **kwargs)

if __name__ == '__main__':
    unittest.main()

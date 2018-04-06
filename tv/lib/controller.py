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

"""controller.py -- Contains Controller class.  It handles application
crashes and shutdown.
"""

import logging
import os
import threading
import locale

from miro import app
from miro import crashreport
from miro import downloader
from miro import eventloop
from miro.gtcache import gettext as _
from miro import httpauth
from miro import httpclient
from miro import messages
from miro import prefs
from miro import signals
from miro import conversions
from miro import util
from miro import workerprocess
from miro.plat.utils import exit_miro

BOGON_URL = "http://bogondeflector.pculture.org/index.php"

class Controller:
    """High-level controller object for the backend.
    """
    def __init__(self):
        self.bug_report_senders = set()
        self._quit_after_bug_reports = False

    @eventloop.as_urgent
    def shutdown(self):
        if app.local_metadata_manager is not None:
            logging.info("Sending pending metadata updates")
            app.local_metadata_manager.run_updates()
        logging.info("Shutting down video conversions manager")
        conversions.conversion_manager.shutdown()
        logging.info("Shutting down Downloader...")
        if app.download_state_manager is not None:
            app.download_state_manager.shutdown_downloader(
                self.downloader_shutdown)
            wait_for_downloader = True
        else:
            wait_for_downloader = False
        try:
            logging.info("Shutting down worker process.")
            workerprocess.shutdown()
            if app.device_manager is not None:
                logging.info("Shutting down device manager")
                app.device_manager.shutdown()
            if app.sharing_manager is not None:
                logging.info("Shutting down Sharing Manager")
                app.sharing_manager.shutdown()
            if app.sharing_tracker is not None:
                logging.info("Shutting down Sharing Tracker")
                app.sharing_tracker.stop_tracking()
        except StandardError:
            signals.system.failed_exn("while shutting down")
            # don't abort - it's not "fatal" and we can still shutdown
        if not wait_for_downloader:
            self.downloader_shutdown()

    def downloader_shutdown(self):
        logging.info("Shutting down libCURL thread")
        httpclient.stop_thread()
        httpclient.cleanup_libcurl()
        logging.info("Writing HTTP passwords")
        httpauth.write_to_file()
        logging.info("Shutting down event loop thread")
        eventloop.shutdown()
        logging.info("Saving cached ItemInfo objects")
        logging.info("Commiting DB changes")
        app.db.finish_transaction()
        logging.info("Closing Database...")
        if app.db is not None:
            app.db.close()
        signals.system.shutdown()

    def failed_soft(self, when, details, with_exception=False):
        """Handle a recoverable error

        Call this when an error occurs, but we were able to catch it and
        recover from it.  In production mode, this will be logged as a
        warning.  For dev builds, this will kick up the crash report.
        """
        if app.debugmode:
            signals.system.failed(when, with_exception, details)
        else:
            crashreport.issue_failure_warning(when, details, with_exception)

    def on_shutdown(self):
        try:
            if app.icon_cache_updater is not None:
                logging.info("Shutting down icon cache updates")
                app.icon_cache_updater.shutdown()
            logging.info("Shutting down movie data updates")
            if app.movie_data_updater is not None:
                app.movie_data_updater.shutdown()

            logging.info("Joining event loop ...")
            eventloop.join()
            logging.info("Saving preferences...")
            app.config.save()

            logging.info("Done shutting down.")
            logging.info("Remaining threads are:")
            for thread in threading.enumerate():
                logging.info("%s", thread)

        except StandardError:
            signals.system.failed_exn("while shutting down")
            exit_miro(1)

    def is_sending_crash_report(self):
        return len(self.bug_report_senders) > 0

    def send_bug_report(self, report, description, send_database,
            quit_after=False):
        sender = BugReportSender(report, description, send_database)
        self.bug_report_senders.add(sender)
        sender.connect("finished", self._bug_report_sent)
        if quit_after:
            self._quit_after_bug_reports = True
            eventloop.add_timeout(0.5, self._start_send_bug_report_progress,
                    'bug report progress')
        else:
            eventloop.add_timeout(0.5, self._log_bug_report_progress,
                    'log bug report progress', args=(sender,))

    def _log_bug_report_progress(self, sender):
        if sender.is_done:
            logging.info("Crash report progress: done.")
            return

        current, total = sender.progress()
        if current < total:
            logging.info("Crash report progress: %0.1f",
                    current * 100.0 / total)
            eventloop.add_timeout(1.0, self._log_bug_report_progress,
                    'log bug report progress', args=(sender,))

    def _bug_report_sent(self, sender):
        self.bug_report_senders.remove(sender)
        if (self._quit_after_bug_reports and not
                self.is_sending_crash_report()):
            messages.ProgressDialogFinished().send_to_frontend()
            messages.FrontendQuit().send_to_frontend()

    def _start_send_bug_report_progress(self):
        m = messages.ProgressDialogStart(_('Sending Crash Report'))
        m.send_to_frontend()
        self._send_bug_report_progress()

    def _send_bug_report_progress(self):
        current_sent = 0
        total_to_send = 0
        for sender in self.bug_report_senders:
            sent, to_send = sender.progress()
            if to_send == 0:
                # this sender doesn't know it's total data, we can't calculate
                # things.
                current_sent = total_to_send = 0
                break
            else:
                current_sent += sent
                total_to_send += to_send
        if total_to_send > 0:
            progress = float(current_sent) / total_to_send
        else:
            progress = -1
        text = _('Sending Crash Report (%(progress)d%%)',
                 {"progress": progress * 100})
        messages.ProgressDialog(text, progress).send_to_frontend()
        eventloop.add_timeout(0.1, self._send_bug_report_progress,
                'bug report progress')

class BugReportSender(signals.SignalEmitter):
    """Helper class that sends bug reports."""
    def __init__(self, report, description, send_database):
        signals.SignalEmitter.__init__(self)
        self.create_signal('finished')

        self.is_done = False

        backupfile = None
        if send_database:
            try:
                logging.info("Sending entire database")
                backupfile = self._backup_support_dir()
            except StandardError:
                logging.exception("Failed to backup database")

        if isinstance(report, str):
            report = report.decode(locale.getpreferredencoding())
        report = report.encode("utf-8", "ignore")
        if isinstance(description, str):
            description = description.decode(locale.getpreferredencoding())
        description = description.encode("utf-8", "ignore")
        post_vars = {"description": description,
                     "app_name": app.config.get(prefs.LONG_APP_NAME),
                     "log": report}
        if backupfile:
            post_files = {"databasebackup":
                              {"filename": "databasebackup.zip",
                               "mimetype": "application/octet-stream",
                               "handle": backupfile,
                               }}
        else:
            post_files = None
        logging.info("Sending crash report....")
        self.client = httpclient.grab_url(BOGON_URL,
                           self.callback, self.errback,
                           post_vars=post_vars, post_files=post_files)

    def callback(self, result):
        if result['status'] != 200 or result['body'] != 'OK':
            logging.warning(
                "Failed to submit crash report.  Server returned %r",
                result)
        else:
            logging.info("Crash report submitted successfully")
        self.is_done = True
        self.emit("finished")

    def errback(self, error):
        logging.warning("Failed to submit crash report %r", error)
        self.is_done = True
        self.emit("finished")

    def progress(self):
        progress = self.client.get_stats()
        return progress.uploaded, progress.upload_total

    def _backup_support_dir(self):
        """Back up the support directory.

        :returns: handle of a file for the archive
        """
        skip_dirs = [
            app.config.get(prefs.ICON_CACHE_DIRECTORY),
            app.config.get(prefs.COVER_ART_DIRECTORY),
        ]
        app.db.close()
        try:
            support_dir = app.config.get(prefs.SUPPORT_DIRECTORY)
            max_size = 100000000 # 100 MB
            backup = util.SupportDirBackup(support_dir, skip_dirs, max_size)
            return backup.fileobj()
        finally:
            app.db.open_connection()

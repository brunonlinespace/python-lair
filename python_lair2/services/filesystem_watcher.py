# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Asynchronous filesystem scanning and change watching."""

from __future__ import annotations

from pathlib import Path
from time import monotonic
from typing import Callable
from threading import Event

from PyQt6.QtCore import (
    QObject,
    QFileSystemWatcher,
    QThread,
    QTimer,
    pyqtSignal,
)

from python_lair2.models.module_repository import ModuleRepository
from python_lair2.services.module_scanner import (
    ModuleScanner,
    ScanCancelled,
    ScanSnapshot,
)


MAX_WATCHED_DIRECTORIES = 2048


class _ScanThread(QThread):
    """Run a cooperatively cancellable filesystem traversal."""

    snapshot_ready = pyqtSignal(object)
    scan_failed = pyqtSignal(str)
    scan_cancelled = pyqtSignal()

    def __init__(self, scanner: ModuleScanner, parent: QObject | None = None):
        super().__init__(parent)
        self.scanner = scanner
        self._cancel_event = Event()

    def cancel(self) -> None:
        self._cancel_event.set()
        self.requestInterruption()

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set() or self.isInterruptionRequested()

    def run(self) -> None:
        try:
            snapshot = self.scanner.scan_snapshot(self.is_cancelled)
            if self.is_cancelled():
                self.scan_cancelled.emit()
                return
            self.snapshot_ready.emit(snapshot)
        except ScanCancelled:
            self.scan_cancelled.emit()
        except Exception as error:
            if self.is_cancelled():
                self.scan_cancelled.emit()
            else:
                self.scan_failed.emit(str(error))


class FilesystemWatcher(QObject):
    """
    Watch relevant workspace folders and perform debounced background scans.

    Startup no longer walks the workspace synchronously. One scanner result is
    reused for modules, real folder nodes and watcher installation.
    """

    scan_started = pyqtSignal()
    scan_finished = pyqtSignal(int)
    scan_failed = pyqtSignal(str)
    folders_discovered = pyqtSignal(object)
    scan_details = pyqtSignal(int, float)

    def __init__(
        self,
        root: str | Path,
        repository: ModuleRepository,
        *,
        debounce_ms: int = 500,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.root = Path(root).expanduser().resolve(strict=False)
        self.repository = repository
        self.scanner = ModuleScanner(self.root)

        self._watcher = QFileSystemWatcher(self)
        self._watcher.directoryChanged.connect(self._schedule_scan)
        self._watcher.fileChanged.connect(self._schedule_scan)

        self._scan_timer = QTimer(self)
        self._scan_timer.setSingleShot(True)
        self._scan_timer.setInterval(max(100, debounce_ms))
        self._scan_timer.timeout.connect(self.rescan)

        self._scan_thread: _ScanThread | None = None
        self._rescan_pending = False
        self._stopping = False

    def start(self, *, initial_scan: bool = True) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._replace_watch_paths((self.root,))
        if initial_scan:
            # Let the main window finish painting before work begins.
            QTimer.singleShot(0, self.rescan)

    def stop(
        self,
        *,
        timeout_ms: int = 2000,
        pump_events: Callable[[], None] | None = None,
    ) -> bool:
        """
        Cancel active scanning while allowing shutdown UI to repaint.

        QFileSystemWatcher releases native watches during process teardown, so
        the close path only needs to stop timers/signals and join an active
        scanner thread.
        """
        self._stopping = True
        self._rescan_pending = False
        self._scan_timer.stop()
        self._watcher.blockSignals(True)

        thread = self._scan_thread
        if thread is None or not thread.isRunning():
            return True

        thread.cancel()
        deadline = monotonic() + max(0, timeout_ms) / 1000.0
        while thread.isRunning() and monotonic() < deadline:
            thread.wait(40)
            if pump_events is not None:
                pump_events()

        stopped = not thread.isRunning()
        if stopped:
            self._scan_thread = None
        return stopped

    def request_rescan(self) -> None:
        self._schedule_scan()

    def rescan(self) -> None:
        if self._stopping:
            return

        if self._scan_thread is not None and self._scan_thread.isRunning():
            self._rescan_pending = True
            return

        self.scan_started.emit()
        thread = _ScanThread(self.scanner, self)
        self._scan_thread = thread
        thread.snapshot_ready.connect(self._apply_snapshot)
        thread.scan_failed.connect(self._handle_failure)
        thread.scan_cancelled.connect(self._handle_cancelled)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._thread_finished)
        thread.start()

    def _apply_snapshot(self, snapshot: ScanSnapshot) -> None:
        if self._stopping:
            return

        # Folder information is emitted before module updates so navigation
        # can create parent nodes before script items arrive.
        self.folders_discovered.emit(snapshot.folders)
        self.repository.replace_all(snapshot.modules)
        self._replace_watch_paths(snapshot.watch_directories)

        self.scan_details.emit(
            snapshot.scanned_entries,
            snapshot.elapsed_seconds,
        )
        self.scan_finished.emit(len(snapshot.modules))

    def _handle_failure(self, message: str) -> None:
        if not self._stopping:
            self.scan_failed.emit(message)

    def _handle_cancelled(self) -> None:
        """Cancellation during shutdown is expected."""
        return

    def _thread_finished(self) -> None:
        self._scan_thread = None
        if self._rescan_pending and not self._stopping:
            self._rescan_pending = False
            self._scan_timer.start()

    def _schedule_scan(self, *_args: object) -> None:
        if not self._stopping:
            self._scan_timer.start()

    def _replace_watch_paths(self, paths) -> None:
        """
        Watch only directories relevant to Python scripts, capped to avoid
        exhausting the operating system's inotify watch limit.
        """
        desired = [str(Path(path)) for path in paths]
        desired = list(dict.fromkeys(desired))

        if len(desired) > MAX_WATCHED_DIRECTORIES:
            # Keep shallower paths first; root and parents provide the broadest
            # useful coverage when the workspace exceeds the watch limit.
            desired.sort(key=lambda value: (len(Path(value).parts), value))
            desired = desired[:MAX_WATCHED_DIRECTORIES]

        desired_set = set(desired)
        active_set = set(self._watcher.directories())

        remove = sorted(active_set - desired_set)
        add = sorted(desired_set - active_set)

        if remove:
            self._watcher.removePaths(remove)
        if add:
            self._watcher.addPaths(add)

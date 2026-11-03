# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
"""
Python Lair 2
services/process_manager.py

Qt-native process management for Python scripts.

This service replaces subprocess.Popen with QProcess so process startup,
output, errors, completion, and application shutdown integrate cleanly with
the Qt event loop.
"""

from __future__ import annotations

import json
import os
import signal
import stat
import time
import secrets
from functools import partial
from pathlib import Path
from typing import Callable
from uuid import uuid4

from PyQt6.QtCore import QObject, QProcess, QTimer, pyqtSignal

from python_lair2.models.module import Module
from python_lair2.models.module_repository import ModuleRepository
from python_lair2.models.module_state_store import ModuleStateStore
from python_lair2.services.runtime_launcher import RuntimeLauncher


class ProcessManager(QObject):
    """Launches and supervises scripts known to the repository."""

    process_started = pyqtSignal(object)
    process_stopped = pyqtSignal(object, int, object)
    process_error = pyqtSignal(object, str)
    output_available = pyqtSignal(object, str, bool)
    status_message = pyqtSignal(str)

    def __init__(
        self,
        repository: ModuleRepository,
        states: ModuleStateStore,
        runtime_launcher: RuntimeLauncher,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.repository = repository
        self.states = states
        self.runtime_launcher = runtime_launcher

        self._terminal_sessions: dict[Path, dict[str, object]] = {}
        repository.module_removed.connect(self._on_module_removed)

    def launch(
        self,
        path: str | Path,
        *,
        extra_arguments: tuple[str, ...] = (),
        interpreter_override: str | None = None,
        working_directory: str | Path | None = None,
        environment: dict[str, str] | None = None,
    ) -> bool:
        """
        Launch a script with the runtime-selected Python interpreter.

        Returns True when startup was requested and False when validation
        failed or the script is already running.
        """
        module = self.repository.get(path)
        if module is None:
            self.status_message.emit("Cannot launch: the script is not in the workspace.")
            return False

        if not module.path.exists():
            self._report_error(module, f"Script not found: {module.path}")
            return False

        state = self.states.ensure(module.path)
        existing = state.process
        if existing is not None and existing.state() != QProcess.ProcessState.NotRunning:
            self.status_message.emit(f"{module.filename} is already running.")
            return False

        command = self.runtime_launcher.script_command(
            module.path,
            extra_arguments=extra_arguments,
            interpreter_override=interpreter_override,
            working_directory=working_directory,
            environment=environment,
        )
        if command is None:
            self._report_error(
                module,
                "No host Python interpreter was found. Install python3 or "
                "set PYTHON_LAIR_PYTHON to the desired interpreter.",
            )
            return False

        process = QProcess(self)
        self.runtime_launcher.configure_process(process, command)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)

        process.started.connect(partial(self._on_started, module.path, process))
        process.finished.connect(partial(self._on_finished, module.path, process))
        process.errorOccurred.connect(
            partial(self._on_error_occurred, module.path, process)
        )
        process.readyReadStandardOutput.connect(
            partial(self._read_output, module.path, process, False)
        )
        process.readyReadStandardError.connect(
            partial(self._read_output, module.path, process, True)
        )

        state.process = process
        process.start()
        self.status_message.emit(f"Starting {module.filename}…")
        return True

    def launch_in_terminal(
        self,
        path: str | Path,
        *,
        elevated: bool = False,
        extra_arguments: tuple[str, ...] = (),
        interpreter_override: str | None = None,
        working_directory: str | Path | None = None,
        environment: dict[str, str] | None = None,
    ) -> bool:
        """Launch a script in a terminal using Sheepy-derived run settings."""
        module = self.repository.get(path)
        if module is None:
            self.status_message.emit("Cannot launch: the script is not in the workspace.")
            return False

        if not module.path.exists():
            self._report_error(module, f"Script not found: {module.path}")
            return False

        if self.is_running(module.path):
            self.status_message.emit(f"{module.filename} is already running.")
            return False

        session_dir = (
            self.runtime_launcher.runtime_paths.config_root
            / "terminal-sessions"
        )
        try:
            session_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            details = os.lstat(session_dir)
            if not stat.S_ISDIR(details.st_mode):
                raise OSError("Terminal-session storage is not a directory.")
            if hasattr(os, "getuid") and details.st_uid != os.getuid():
                raise OSError("Terminal-session storage is not owned by the current user.")
            try:
                os.chmod(session_dir, 0o700)
            except OSError:
                pass
        except OSError as error:
            self._report_error(
                module,
                f"Could not prepare terminal-session storage: {error}",
            )
            return False
        state_path = session_dir / f"{uuid4().hex}.json"
        session_token = secrets.token_hex(32)
        command = self.runtime_launcher.script_terminal_command(
            module.path,
            None if elevated else state_path,
            None if elevated else session_token,
            elevated=elevated,
            extra_arguments=extra_arguments,
            interpreter_override=interpreter_override,
            working_directory=working_directory,
            environment=environment,
        )
        if command is None:
            self._report_error(
                module,
                "No supported terminal emulator or host Python interpreter "
                "was found.",
            )
            return False

        started, terminal_pid = (
            self.runtime_launcher.start_detached_with_pid(command)
        )
        if not started:
            self._report_error(
                module,
                f"Could not start terminal: {command.program}",
            )
            return False

        if elevated:
            self.status_message.emit(
                f"Launched {module.filename} as administrator in {Path(command.program).name}."
            )
            return True

        timer = QTimer(self)
        timer.setInterval(400)
        session = {
            "state_path": state_path,
            "token": session_token,
            "script": str(module.path.expanduser().resolve(strict=False)),
            "runner": str(
                self.runtime_launcher.runtime_paths.config_root
                / "runtime"
                / "terminal_session_runner.py"
            ),
            "terminal_program": command.program,
            "timer": timer,
            "started_at": time.monotonic(),
            "observed": False,
            "wrapper_pid": None,
            "child_pid": None,
            "child_pgid": None,
            "wrapper_start_time": None,
            "child_start_time": None,
            "terminal_pid": terminal_pid,
            "terminal_start_time": (
                self._process_start_time(terminal_pid)
                if isinstance(terminal_pid, int)
                else None
            ),
        }
        self._terminal_sessions[module.path] = session
        timer.timeout.connect(
            partial(self._poll_terminal_session, module.path)
        )
        timer.start()
        self.repository.set_running(module.path, True)
        self.status_message.emit(
            f"Launched {module.filename} in {Path(command.program).name}."
        )
        return True

    def stop(self, path: str | Path, *, kill_after_ms: int = 2000) -> bool:
        """Request graceful termination, then force-kill after a timeout."""
        module = self.repository.get(path)
        if module is None:
            return False

        state = self.states.get(module.path)
        process = state.process if state is not None else None
        if process is None or process.state() == QProcess.ProcessState.NotRunning:
            return self._stop_terminal_session(module.path, signal.SIGTERM)

        process.terminate()
        self.status_message.emit(f"Stopping {module.filename}…")

        QTimer.singleShot(
            max(0, kill_after_ms),
            partial(self._kill_if_running, process),
        )
        return True

    def force_stop(self, path: str | Path) -> bool:
        """Immediately kill a managed script that is not responding."""
        module = self.repository.get(path)
        if module is None:
            return False

        state = self.states.get(module.path)
        process = state.process if state is not None else None
        if process is None or process.state() == QProcess.ProcessState.NotRunning:
            return self._stop_terminal_session(module.path, signal.SIGKILL)

        process.kill()
        self.status_message.emit(f"Force-stopping {module.filename}…")
        return True

    def stop_all(self, *, kill_after_ms: int = 2000) -> None:
        """Stop every process managed by this service."""
        for module in tuple(self.repository.running):
            self.stop(module.path, kill_after_ms=kill_after_ms)

    def shutdown(
        self,
        *,
        timeout_ms: int = 1500,
        pump_events: Callable[[], None] | None = None,
    ) -> None:
        """Stop active processes while keeping shutdown feedback responsive."""
        for path in tuple(self._terminal_sessions):
            self._stop_terminal_session(path, signal.SIGTERM)
            if pump_events is not None:
                pump_events()

        processes: list[QProcess] = []
        for module in tuple(self.repository.running):
            state = self.states.get(module.path)
            process = state.process if state is not None else None
            if (
                process is not None
                and process.state() != QProcess.ProcessState.NotRunning
            ):
                processes.append(process)
                process.terminate()

        if not processes:
            return

        deadline = time.monotonic() + max(0, timeout_ms) / 1000.0
        while time.monotonic() < deadline:
            remaining = [
                item
                for item in processes
                if item.state() != QProcess.ProcessState.NotRunning
            ]
            if not remaining:
                return
            for item in remaining:
                item.waitForFinished(40)
            if pump_events is not None:
                pump_events()

        for item in processes:
            if item.state() != QProcess.ProcessState.NotRunning:
                item.kill()
                item.waitForFinished(100)
                if pump_events is not None:
                    pump_events()

    def is_running(self, path: str | Path) -> bool:
        """Return the live QProcess state rather than relying only on metadata."""
        module = self.repository.get(path)
        if module is None:
            return False

        state = self.states.get(module.path)
        managed = bool(
            state is not None
            and state.process is not None
            and state.process.state() != QProcess.ProcessState.NotRunning
        )
        return managed or module.path in self._terminal_sessions

    def _poll_terminal_session(self, path: Path) -> None:
        session = self._terminal_sessions.get(path)
        if session is None:
            return

        state_path = session.get("state_path")
        token = session.get("token")
        script = session.get("script")
        if (
            not isinstance(state_path, Path)
            or not isinstance(token, str)
            or not isinstance(script, str)
        ):
            self._finish_terminal_session(path)
            return

        if state_path.exists():
            payload = self._read_terminal_state(
                state_path,
                token=token,
                script=script,
            )
            if payload is not None:
                session["observed"] = True
                for key in (
                    "wrapper_pid",
                    "child_pid",
                    "child_pgid",
                    "wrapper_start_time",
                    "child_start_time",
                ):
                    try:
                        value = int(payload.get(key, 0))
                    except (TypeError, ValueError, OverflowError):
                        value = 0
                    session[key] = value if value > 0 else None
                return

        elapsed = time.monotonic() - float(session.get("started_at", 0.0))
        if bool(session.get("observed")) or elapsed > 8.0:
            if state_path.exists() and not bool(session.get("observed")):
                try:
                    state_path.unlink()
                except OSError:
                    pass
            self._finish_terminal_session(path)

    @staticmethod
    def _read_terminal_state(
        state_path: Path,
        *,
        token: str,
        script: str,
    ) -> dict[str, object] | None:
        descriptor: int | None = None
        try:
            flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
            flags |= getattr(os, "O_NOFOLLOW", 0)
            flags |= getattr(os, "O_NONBLOCK", 0)
            flags |= getattr(os, "O_NOCTTY", 0)
            descriptor = os.open(state_path, flags)
            details = os.fstat(descriptor)
            if not stat.S_ISREG(details.st_mode) or details.st_size > 4096:
                return None
            if hasattr(os, "getuid") and details.st_uid != os.getuid():
                return None
            raw = os.read(descriptor, 4097)
            if len(raw) > 4096:
                return None
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                return None
            if payload.get("token") != token or payload.get("script") != script:
                return None
            return payload
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass

    def _finish_terminal_session(self, path: Path) -> None:
        session = self._terminal_sessions.pop(path, None)
        if session is not None:
            timer = session.get("timer")
            if isinstance(timer, QTimer):
                timer.stop()
                timer.deleteLater()
        self.repository.set_running(path, False)
        module = self.repository.get(path)
        if module is not None:
            self.status_message.emit(f"{module.filename} terminal run finished.")

    @staticmethod
    def _process_start_time(process_id: int) -> int | None:
        """Return Linux /proc start ticks for PID-reuse protection."""
        if process_id <= 0 or not Path("/proc").is_dir():
            return None
        descriptor: int | None = None
        try:
            flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
            descriptor = os.open(Path("/proc") / str(process_id) / "stat", flags)
            raw = os.read(descriptor, 4097)
            if len(raw) > 4096:
                return None
            closing = raw.rfind(b")")
            if closing < 0:
                return None
            fields = raw[closing + 1 :].split()
            if len(fields) <= 19:
                return None
            return int(fields[19])
        except (OSError, ValueError):
            return None
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass

    @classmethod
    def _process_command_matches(
        cls,
        process_id: int,
        expected_values: tuple[str, ...],
        *,
        expected_start_time: int | None = None,
        allow_program_basename: bool = False,
    ) -> bool:
        if expected_start_time is not None:
            if cls._process_start_time(process_id) != expected_start_time:
                return False
        if not Path("/proc").is_dir():
            return False
        descriptor: int | None = None
        try:
            flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
            descriptor = os.open(
                Path("/proc") / str(process_id) / "cmdline",
                flags,
            )
            raw = os.read(descriptor, 65_537)
            if len(raw) > 65_536:
                return False
        except OSError:
            return False
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        arguments = [
            value.decode("utf-8", errors="surrogateescape")
            for value in raw.split(b"\0")
            if value
        ]
        if not arguments:
            return False
        for index, expected in enumerate(expected_values):
            if not expected:
                continue
            if expected in arguments:
                continue
            if (
                allow_program_basename
                and index == 0
                and Path(expected).name == Path(arguments[0]).name
            ):
                continue
            return False
        return True

    @classmethod
    def _signal_process(
        cls,
        process_id: object,
        sig: int,
        *,
        expected_values: tuple[str, ...] = (),
        expected_start_time: int | None = None,
        allow_program_basename: bool = False,
    ) -> bool:
        if not isinstance(process_id, int) or process_id <= 0:
            return False
        if expected_values and not cls._process_command_matches(
            process_id,
            expected_values,
            expected_start_time=expected_start_time,
            allow_program_basename=allow_program_basename,
        ):
            return False
        try:
            os.kill(process_id, sig)
            return True
        except (OSError, ProcessLookupError, PermissionError):
            return False

    def _stop_terminal_session(self, path: Path, sig: int) -> bool:
        session = self._terminal_sessions.get(path)
        if session is None:
            self.repository.set_running(path, False)
            return False

        module = self.repository.get(path)
        child_pid = session.get("child_pid")
        child_pgid = session.get("child_pgid")
        wrapper_pid = session.get("wrapper_pid")
        terminal_pid = session.get("terminal_pid")
        terminal_start_time = session.get("terminal_start_time")
        child_start_time = session.get("child_start_time")
        wrapper_start_time = session.get("wrapper_start_time")
        script = session.get("script")
        runner = session.get("runner")
        token = session.get("token")
        terminal_program = session.get("terminal_program")
        sent_signal = False

        close_terminal = sig == signal.SIGKILL or (
            not isinstance(child_pgid, int)
            and not isinstance(wrapper_pid, int)
        )
        if close_terminal:
            expected_terminal = (
                (terminal_program,)
                if isinstance(terminal_program, str)
                else ()
            )
            sent_signal = self._signal_process(
                terminal_pid,
                signal.SIGTERM,
                expected_values=expected_terminal,
                expected_start_time=(
                    terminal_start_time
                    if isinstance(terminal_start_time, int)
                    else None
                ),
                allow_program_basename=True,
            )

        child_expected = (script,) if isinstance(script, str) else ()
        if (
            isinstance(child_pid, int)
            and isinstance(child_pgid, int)
            and child_pid > 0
            and child_pgid == child_pid
            and self._process_command_matches(
                child_pid,
                child_expected,
                expected_start_time=(
                    child_start_time
                    if isinstance(child_start_time, int)
                    else None
                ),
            )
        ):
            try:
                if hasattr(os, "killpg"):
                    os.killpg(child_pgid, sig)
                else:
                    os.kill(child_pgid, sig)
                sent_signal = True
            except (OSError, ProcessLookupError, PermissionError):
                pass

        wrapper_expected = tuple(
            value
            for value in (runner, token)
            if isinstance(value, str)
        )
        if isinstance(wrapper_pid, int) and wrapper_pid > 0:
            wrapper_signal = (
                signal.SIGKILL if sig == signal.SIGKILL else signal.SIGTERM
            )
            sent_signal = self._signal_process(
                wrapper_pid,
                wrapper_signal,
                expected_values=wrapper_expected,
                expected_start_time=(
                    wrapper_start_time
                    if isinstance(wrapper_start_time, int)
                    else None
                ),
            ) or sent_signal

        state_path = session.get("state_path")
        if isinstance(state_path, Path):
            try:
                state_path.unlink()
            except OSError:
                pass

        self._finish_terminal_session(path)
        if module is not None:
            self.status_message.emit(
                f"{'Force-stopped' if sig == signal.SIGKILL else 'Stopped'} "
                f"{module.filename} terminal session."
            )
        return sent_signal

    def _on_started(self, path: Path, process: QProcess) -> None:
        module = self.repository.get(path)
        if module is None or not self._is_current_process(path, process):
            return

        self.repository.set_running(path, True)
        self.process_started.emit(module)
        self.status_message.emit(f"Launched {module.filename}.")

    def _on_finished(
        self,
        path: Path,
        process: QProcess,
        exit_code: int,
        exit_status: QProcess.ExitStatus,
    ) -> None:
        module = self.repository.get(path)

        # Drain anything written just before process exit.
        self._read_output(path, process, False)
        self._read_output(path, process, True)

        state = self.states.get(path)
        if state is not None and state.process is process:
            state.clear_process()

        if module is not None:
            self.repository.set_running(path, False)
            self.process_stopped.emit(module, exit_code, exit_status)

            if exit_status == QProcess.ExitStatus.CrashExit:
                self._report_error(
                    module,
                    f"{module.filename} crashed (exit code {exit_code}).",
                )
            elif exit_code != 0:
                self._report_error(
                    module,
                    f"{module.filename} exited with code {exit_code}.",
                )
            else:
                self.status_message.emit(f"{module.filename} finished.")

        process.deleteLater()

    def _on_error_occurred(
        self,
        path: Path,
        process: QProcess,
        error: QProcess.ProcessError,
    ) -> None:
        module = self.repository.get(path)
        if module is None or not self._is_current_process(path, process):
            return

        message = process.errorString() or self._process_error_name(error)
        self._report_error(module, f"Could not run {module.filename}: {message}")

        # FailedToStart may not produce a normal finished signal.
        if error == QProcess.ProcessError.FailedToStart:
            state = self.states.get(path)
            if state is not None and state.process is process:
                state.clear_process()
            self.repository.set_running(path, False)
            process.deleteLater()

    def _read_output(
        self,
        path: Path,
        process: QProcess,
        is_stderr: bool,
    ) -> None:
        module = self.repository.get(path)
        if module is None:
            return

        raw = (
            process.readAllStandardError()
            if is_stderr
            else process.readAllStandardOutput()
        )
        text = bytes(raw).decode("utf-8", errors="replace")
        if text:
            self.output_available.emit(module, text, is_stderr)

    def _on_module_removed(self, module: Module) -> None:
        # ModuleStateStore also terminates removed processes. Calling stop first
        # gives this manager a chance to update status consistently.
        state = self.states.get(module.path)
        process = state.process if state is not None else None
        if process is not None and process.state() != QProcess.ProcessState.NotRunning:
            process.terminate()

    def _is_current_process(self, path: Path, process: QProcess) -> bool:
        state = self.states.get(path)
        return state is not None and state.process is process

    @staticmethod
    def _kill_if_running(process: QProcess) -> None:
        try:
            if process.state() != QProcess.ProcessState.NotRunning:
                process.kill()
        except RuntimeError:
            # The process may have finished and had its C++ object deleted.
            return

    def _report_error(self, module: Module, message: str) -> None:
        self.process_error.emit(module, message)
        self.status_message.emit(message)

    @staticmethod
    def _process_error_name(error: QProcess.ProcessError) -> str:
        names = {
            QProcess.ProcessError.FailedToStart: "failed to start",
            QProcess.ProcessError.Crashed: "process crashed",
            QProcess.ProcessError.Timedout: "operation timed out",
            QProcess.ProcessError.WriteError: "write error",
            QProcess.ProcessError.ReadError: "read error",
            QProcess.ProcessError.UnknownError: "unknown process error",
        }
        return names.get(error, "process error")

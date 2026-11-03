# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Small, testable helpers for safe Python-source file I/O."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path

_READ_CHUNK_SIZE = 1024 * 1024
_MAX_STABILITY_ATTEMPTS = 2


class UnsupportedFileError(OSError):
    """Raised when a selected path is not a regular file."""


class FileTooLargeError(OSError):
    """Raised when a file exceeds Python Lair's configured size limit."""


class FileStateChangedError(OSError):
    """Raised when a path changes while Python Lair is reading or saving it."""


@dataclass(frozen=True, slots=True)
class FileState:
    """Filesystem identity used to detect replacement and retargeting races."""

    path_device: int
    path_inode: int
    path_type: int
    path_mode: int
    target_device: int
    target_inode: int
    target_type: int
    target_mode: int
    size: int
    mtime_ns: int
    ctime_ns: int

    @property
    def is_symlink(self) -> bool:
        return self.path_type == stat.S_IFLNK


@dataclass(frozen=True, slots=True)
class FileSnapshot:
    """A stable file state plus a content digest."""

    state: FileState
    digest: str


def absolute_user_path(value: str | os.PathLike[str]) -> Path:
    """Return an absolute path without resolving the user's final symlink."""
    expanded = Path(value).expanduser()
    return Path(os.path.abspath(os.fspath(expanded)))


def path_lexists(path: Path) -> bool:
    """Like Path.exists(), but also report dangling symbolic links."""
    return os.path.lexists(os.fspath(path))


def path_identity_matches(path: Path, expected: FileState) -> bool:
    """Return whether *path* still names the same filesystem object."""
    try:
        details = os.lstat(path)
    except OSError:
        return False
    return (
        details.st_dev == expected.path_device
        and details.st_ino == expected.path_inode
        and stat.S_IFMT(details.st_mode) == expected.path_type
    )


def ensure_private_directory(directory: Path) -> Path:
    """Create and validate a user-private, non-symlink directory."""
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    details = os.lstat(directory)
    if not stat.S_ISDIR(details.st_mode):
        raise OSError(f"Not a private directory: {directory}")
    if hasattr(os, "getuid") and details.st_uid != os.getuid():
        raise OSError(f"Directory is not owned by the current user: {directory}")
    try:
        os.chmod(directory, 0o700)
    except OSError:
        # Permission normalization may be unavailable on non-POSIX filesystems.
        pass
    return directory


def _file_state(path_stat: os.stat_result, target_stat: os.stat_result) -> FileState:
    return FileState(
        path_device=path_stat.st_dev,
        path_inode=path_stat.st_ino,
        path_type=stat.S_IFMT(path_stat.st_mode),
        path_mode=path_stat.st_mode,
        target_device=target_stat.st_dev,
        target_inode=target_stat.st_ino,
        target_type=stat.S_IFMT(target_stat.st_mode),
        target_mode=target_stat.st_mode,
        size=target_stat.st_size,
        mtime_ns=target_stat.st_mtime_ns,
        ctime_ns=target_stat.st_ctime_ns,
    )


def _validate_path_entry(path_state: os.stat_result) -> None:
    """Reject directories/devices before opening them."""
    if stat.S_ISREG(path_state.st_mode) or stat.S_ISLNK(path_state.st_mode):
        return
    raise UnsupportedFileError("The selected path is not a regular file.")


def _open_read_only(path: Path, *, follow_symlinks: bool = True) -> int:
    # O_NONBLOCK prevents a raced symlink-to-FIFO or FIFO path from hanging the
    # GUI thread before fstat() can reject it. It has no effect on regular files.
    flags = os.O_RDONLY
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    flags |= getattr(os, "O_NOCTTY", 0)
    if not follow_symlinks:
        flags |= getattr(os, "O_NOFOLLOW", 0)
    return os.open(path, flags)


def current_file_state(path: Path) -> FileState:
    """Read a stable path/target identity without loading file contents."""
    last_error: OSError | None = None
    for _attempt in range(_MAX_STABILITY_ATTEMPTS):
        descriptor: int | None = None
        try:
            path_before = os.lstat(path)
            _validate_path_entry(path_before)
            descriptor = _open_read_only(path)
            target_state = os.fstat(descriptor)
            path_after = os.lstat(path)
            state = _file_state(path_after, target_state)
            if not stat.S_ISREG(target_state.st_mode):
                raise UnsupportedFileError("The selected path is not a regular file.")
            if (
                path_before.st_dev == path_after.st_dev
                and path_before.st_ino == path_after.st_ino
                and stat.S_IFMT(path_before.st_mode) == state.path_type
            ):
                return state
            last_error = FileStateChangedError(
                "The file path changed while Python Lair was checking it."
            )
        except UnsupportedFileError:
            raise
        except OSError as error:
            last_error = error
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
    assert last_error is not None
    raise last_error


def read_regular_file(
    path: Path,
    max_size: int,
    *,
    follow_symlinks: bool = True,
) -> tuple[bytes, FileSnapshot]:
    """Open and read one stable regular file with a strict byte-size cap."""
    last_error: OSError | None = None
    for _attempt in range(_MAX_STABILITY_ATTEMPTS):
        descriptor: int | None = None
        try:
            path_before = os.lstat(path)
            _validate_path_entry(path_before)
            if not follow_symlinks and stat.S_ISLNK(path_before.st_mode):
                raise UnsupportedFileError(
                    "Symbolic links are not accepted for this private file."
                )
            descriptor = _open_read_only(
                path,
                follow_symlinks=follow_symlinks,
            )
            target_before = os.fstat(descriptor)
            if not stat.S_ISREG(target_before.st_mode):
                raise UnsupportedFileError("The selected path is not a regular file.")
            if target_before.st_size > max_size:
                raise FileTooLargeError(
                    f"The file exceeds the {max_size // (1024 * 1024)} MiB limit."
                )

            chunks: list[bytes] = []
            digest = hashlib.sha256()
            total = 0
            while True:
                chunk = os.read(descriptor, _READ_CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_size:
                    raise FileTooLargeError(
                        f"The file exceeds the {max_size // (1024 * 1024)} MiB limit."
                    )
                digest.update(chunk)
                chunks.append(chunk)

            target_after = os.fstat(descriptor)
            path_after = os.lstat(path)
            state = _file_state(path_after, target_after)
            stable_path = (
                path_before.st_dev == path_after.st_dev
                and path_before.st_ino == path_after.st_ino
                and stat.S_IFMT(path_before.st_mode) == state.path_type
            )
            stable_target = (
                target_before.st_dev == target_after.st_dev
                and target_before.st_ino == target_after.st_ino
                and target_before.st_size == target_after.st_size
                and target_before.st_mtime_ns == target_after.st_mtime_ns
                and target_before.st_ctime_ns == target_after.st_ctime_ns
            )
            if stable_path and stable_target:
                data = b"".join(chunks)
                return data, FileSnapshot(
                    state=state,
                    digest=digest.hexdigest(),
                )
            last_error = FileStateChangedError(
                "The file changed while Python Lair was reading it. Try again."
            )
        except (UnsupportedFileError, FileTooLargeError):
            raise
        except OSError as error:
            last_error = error
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
    assert last_error is not None
    raise last_error


def validated_symlink_target(path: Path, expected: FileState) -> Path:
    """Resolve an unchanged symlink to a regular target for atomic saving."""
    if not expected.is_symlink:
        raise FileStateChangedError("The save target is no longer a symbolic link.")
    if current_file_state(path) != expected:
        raise FileStateChangedError(
            "The symbolic-link save target changed before Python Lair could write it."
        )
    try:
        target = path.resolve(strict=True)
    except OSError as error:
        raise FileStateChangedError(
            "The symbolic-link save target cannot be resolved."
        ) from error
    target_state = os.stat(target)
    if not stat.S_ISREG(target_state.st_mode):
        raise UnsupportedFileError(
            "The symbolic link does not point to a regular file."
        )
    if (
        target_state.st_dev != expected.target_device
        or target_state.st_ino != expected.target_inode
    ):
        raise FileStateChangedError(
            "The symbolic-link target changed before Python Lair could save it."
        )
    return target


def install_new_file_from_temp(temporary: Path, destination: Path) -> None:
    """Install a synchronized temporary file without overwriting a raced path."""
    try:
        os.link(temporary, destination, follow_symlinks=False)
    except FileExistsError as error:
        raise FileStateChangedError(
            "A file appeared at the save location. Saving was cancelled."
        ) from error
    except (AttributeError, NotImplementedError, TypeError, OSError):
        # Some non-POSIX filesystems do not support hard links. Fall back to an
        # exclusive destination open, which preserves the no-clobber guarantee.
        descriptor: int | None = None
        created = False
        try:
            source_mode = temporary.stat().st_mode & 0o7777
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            flags |= getattr(os, "O_CLOEXEC", 0)
            descriptor = os.open(destination, flags, source_mode)
            created = True
            if hasattr(os, "fchmod"):
                os.fchmod(descriptor, source_mode)
            with temporary.open("rb") as source, os.fdopen(descriptor, "wb") as target:
                descriptor = None
                shutil.copyfileobj(source, target, length=_READ_CHUNK_SIZE)
                target.flush()
                os.fsync(target.fileno())
        except FileExistsError as error:
            raise FileStateChangedError(
                "A file appeared at the save location. Saving was cancelled."
            ) from error
        except OSError:
            if created:
                try:
                    destination.unlink()
                except OSError:
                    pass
            raise
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
    try:
        temporary.unlink()
    except OSError:
        # The destination is already complete and synchronized. A leftover
        # hidden temporary file is preferable to reporting a false save failure.
        pass



def rename_path_no_replace(source: Path, destination: Path) -> None:
    """Rename a file path without overwriting a destination that raced in."""
    try:
        os.link(source, destination, follow_symlinks=False)
    except FileExistsError as error:
        raise FileStateChangedError(
            "A file appeared at the rename destination. Rename was cancelled."
        ) from error
    except (AttributeError, NotImplementedError, TypeError, OSError):
        # Portable fallback. Recheck immediately before rename; POSIX/Linux uses
        # the hard-link path above, which provides the strict no-clobber result.
        if path_lexists(destination):
            raise FileStateChangedError(
                "A file appeared at the rename destination. Rename was cancelled."
            )
        os.rename(source, destination)
        return

    try:
        source.unlink()
    except OSError:
        try:
            destination.unlink()
        except OSError:
            pass
        raise


def toggle_executable_permission(
    path: Path,
    expected: FileState | None = None,
) -> FileState:
    """Toggle execute bits through an open descriptor with identity checks."""
    if not hasattr(os, "fchmod"):
        raise OSError("Descriptor-based permission changes are unavailable.")

    descriptor: int | None = None
    try:
        path_before = os.lstat(path)
        _validate_path_entry(path_before)
        descriptor = _open_read_only(path)
        target_before = os.fstat(descriptor)
        if not stat.S_ISREG(target_before.st_mode):
            raise UnsupportedFileError(
                "Executable permission applies to regular files only."
            )
        path_after_open = os.lstat(path)
        state_before = _file_state(path_after_open, target_before)
        stable_path = (
            path_before.st_dev == path_after_open.st_dev
            and path_before.st_ino == path_after_open.st_ino
            and stat.S_IFMT(path_before.st_mode) == state_before.path_type
        )
        if not stable_path or (expected is not None and state_before != expected):
            raise FileStateChangedError(
                "The file changed before its executable permission could be updated."
            )

        permissions = target_before.st_mode & 0o7777
        new_permissions = (
            permissions & ~0o111
            if permissions & 0o111
            else permissions | 0o111
        )
        os.fchmod(descriptor, new_permissions)

        target_after = os.fstat(descriptor)
        path_final = os.lstat(path)
        state_after = _file_state(path_final, target_after)
        stable_after = (
            path_after_open.st_dev == path_final.st_dev
            and path_after_open.st_ino == path_final.st_ino
            and state_before.path_type == state_after.path_type
            and target_before.st_dev == target_after.st_dev
            and target_before.st_ino == target_after.st_ino
        )
        if not stable_after:
            raise FileStateChangedError(
                "The file path changed while its executable permission was updated."
            )
        return state_after
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass

def snapshot_from_payload(path: Path, payload: bytes) -> FileSnapshot:
    """Capture the post-save state without rereading content just written."""
    return FileSnapshot(
        state=current_file_state(path),
        digest=hashlib.sha256(payload).hexdigest(),
    )


def fsync_directory(directory: Path) -> None:
    """Best-effort persistence for a directory entry after atomic replacement."""
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(directory, flags)
        os.fsync(descriptor)
    except OSError:
        # Some filesystems do not support directory fsync. The file itself has
        # already been synchronized, so failure here is non-fatal.
        pass
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass

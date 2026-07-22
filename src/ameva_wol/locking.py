"""Single-instance process locking using file locking to prevent duplicate processes."""

import os
import sys
from pathlib import Path
from typing import Optional, TextIO


class InstanceLockError(Exception):
    """Raised when another instance of AMEVA-WoL is already running on the same data directory."""


class InstanceLock:
    """Portable non-blocking PID lock for data directory single-instance enforcement."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.lock_file_path = self.data_dir / ".lock"
        self._file_handle: Optional[TextIO] = None

    def acquire(self) -> None:
        """Acquire non-blocking lock on data directory.

        Raises:
            InstanceLockError: If lock is held by another process.
        """
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Open lockfile for writing
            self._file_handle = open(self.lock_file_path, "a+")
        except Exception as err:
            raise InstanceLockError(f"Failed to open lock file '{self.lock_file_path}': {err}")

        # Attempt platform-specific non-blocking file locking
        if sys.platform == "win32":
            import msvcrt
            try:
                self._file_handle.seek(0)
                msvcrt.locking(self._file_handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                self.release()
                raise InstanceLockError(
                    f"Another AMEVA-WoL instance is already running in '{self.data_dir}'."
                )
        else:
            import fcntl
            try:
                fcntl.flock(self._file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (OSError, IOError):
                self.release()
                raise InstanceLockError(
                    f"Another AMEVA-WoL instance is already running in '{self.data_dir}'."
                )

        # Write current PID into lock file for diagnostic inspection
        try:
            self._file_handle.seek(0)
            self._file_handle.truncate()
            self._file_handle.write(f"{os.getpid()}\n")
            self._file_handle.flush()
        except Exception:
            pass  # Non-fatal if writing PID fails after lock acquisition

    def release(self) -> None:
        """Release lock and close handle."""
        if self._file_handle is not None:
            try:
                if sys.platform == "win32":
                    import msvcrt
                    try:
                        self._file_handle.seek(0)
                        msvcrt.locking(self._file_handle.fileno(), msvcrt.LK_UNLCK, 1)
                    except Exception:
                        pass
                else:
                    import fcntl
                    try:
                        fcntl.flock(self._file_handle.fileno(), fcntl.LOCK_UN)
                    except Exception:
                        pass
                self._file_handle.close()
            except Exception:
                pass
            finally:
                self._file_handle = None

    def __enter__(self) -> "InstanceLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()

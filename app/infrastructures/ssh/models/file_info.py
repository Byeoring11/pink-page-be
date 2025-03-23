from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from enum import Flag, auto


class FilePermission(Flag):
    """Flag-based representation of file permissions."""
    NONE = 0

    # User permissions
    USER_READ = auto()
    USER_WRITE = auto()
    USER_EXECUTE = auto()

    # Group permissions
    GROUP_READ = auto()
    GROUP_WRITE = auto()
    GROUP_EXECUTE = auto()

    # Other permissions
    OTHER_READ = auto()
    OTHER_WRITE = auto()
    OTHER_EXECUTE = auto()

    # Special bits
    SETUID = auto()
    SETGID = auto()
    STICKY = auto()

    @classmethod
    def from_mode(cls, mode: int) -> 'FilePermission':
        """Create FilePermission from unix mode (e.g., 0o755)."""
        result = cls.NONE

        # User permissions
        if mode & 0o400:
            result |= cls.USER_READ
        if mode & 0o200:
            result |= cls.USER_WRITE
        if mode & 0o100:
            result |= cls.USER_EXECUTE

        # Group permissions
        if mode & 0o040:
            result |= cls.GROUP_READ
        if mode & 0o020:
            result |= cls.GROUP_WRITE
        if mode & 0o010:
            result |= cls.GROUP_EXECUTE

        # Other permissions
        if mode & 0o004:
            result |= cls.OTHER_READ
        if mode & 0o002:
            result |= cls.OTHER_WRITE
        if mode & 0o001:
            result |= cls.OTHER_EXECUTE

        # Special bits
        if mode & 0o4000:
            result |= cls.SETUID
        if mode & 0o2000:
            result |= cls.SETGID
        if mode & 0o1000:
            result |= cls.STICKY

        return result

    def to_mode(self) -> int:
        """Convert FilePermission to unix mode (e.g., 0o755)."""
        mode = 0

        # User permissions
        if self & self.USER_READ:
            mode |= 0o400
        if self & self.USER_WRITE:
            mode |= 0o200
        if self & self.USER_EXECUTE:
            mode |= 0o100

        # Group permissions
        if self & self.GROUP_READ:
            mode |= 0o040
        if self & self.GROUP_WRITE:
            mode |= 0o020
        if self & self.GROUP_EXECUTE:
            mode |= 0o010

        # Other permissions
        if self & self.OTHER_READ:
            mode |= 0o004
        if self & self.OTHER_WRITE:
            mode |= 0o002
        if self & self.OTHER_EXECUTE:
            mode |= 0o001

        # Special bits
        if self & self.SETUID:
            mode |= 0o4000
        if self & self.SETGID:
            mode |= 0o2000
        if self & self.STICKY:
            mode |= 0o1000

        return mode

    def to_string(self) -> str:
        """Convert to string representation (e.g., 'rwxr-xr--')."""
        result = ""

        # User permissions
        result += "r" if self & self.USER_READ else "-"
        result += "w" if self & self.USER_WRITE else "-"
        if self & self.SETUID:
            result += "s" if self & self.USER_EXECUTE else "S"
        else:
            result += "x" if self & self.USER_EXECUTE else "-"

        # Group permissions
        result += "r" if self & self.GROUP_READ else "-"
        result += "w" if self & self.GROUP_WRITE else "-"
        if self & self.SETGID:
            result += "s" if self & self.GROUP_EXECUTE else "S"
        else:
            result += "x" if self & self.GROUP_EXECUTE else "-"

        # Other permissions
        result += "r" if self & self.OTHER_READ else "-"
        result += "w" if self & self.OTHER_WRITE else "-"
        if self & self.STICKY:
            result += "t" if self & self.OTHER_EXECUTE else "T"
        else:
            result += "x" if self & self.OTHER_EXECUTE else "-"

        return result


class FileInfo(BaseModel):
    """파일 정보 모델"""
    path: str
    name: str
    size: int
    permissions: FilePermission
    is_directory: bool
    is_file: bool
    is_symlink: bool
    uid: int
    gid: int
    owner: Optional[str] = None
    group: Optional[str] = None
    last_modified: datetime
    last_accessed: Optional[datetime] = None
    created: Optional[datetime] = None
    symlink_target: Optional[str] = None

    @property
    def permission_string(self) -> str:
        """Return the unix-style permission string."""
        prefix = "d" if self.is_directory else ("l" if self.is_symlink else "-")
        return prefix + self.permissions.to_string()

    @property
    def permission_mode(self) -> int:
        """Return the permission as an octal mode."""
        return self.permissions.to_mode()

    @property
    def formatted_size(self) -> str:
        """Return human-readable file size."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if self.size < 1024 or unit == "TB":
                return f"{self.size:.2f} {unit}" if unit != "B" else f"{self.size} {unit}"
            self.size /= 1024

    class Config:
        arbitrary_types_allowed = True

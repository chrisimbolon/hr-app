"""shared/enums/attendance.py"""
import enum


class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    LATE = "late"
    ALPHA = "alpha"          # absent without reason
    LEAVE = "leave"
    HOLIDAY = "holiday"
    INCOMPLETE = "incomplete" # checked in, no checkout


class CheckType(str, enum.Enum):
    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"


class LocationType(str, enum.Enum):
    WFO = "wfo"   # Work From Office
    WFH = "wfh"   # Work From Home
    WFA = "wfa"   # Work From Anywhere


class AttendanceSource(str, enum.Enum):
    MOBILE = "mobile"
    WEB = "web"
    ADMIN_OVERRIDE = "admin_override"
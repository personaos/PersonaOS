"""
Clock module for PersonaOS - provides time and date functionality.

This module offers various time and date utilities for the PersonaOS system,
designed to be used as a plugin tool. All functions are stateless and use
only Python standard libraries.
"""

import datetime
from typing import Literal, Optional


def get_current_time(format: Literal['natural', 'iso', '24h'] = 'natural') -> str:
    """
    Get the current local time in the specified format.
    
    # intent: inform_time
    
    Args:
        format: Output format - 'natural', 'iso', or '24h'
        
    Returns:
        Formatted time string
        
    Examples:
        natural: "3:45 PM"
        iso: "15:45:32"
        24h: "15:45"
    """
    now = datetime.datetime.now()
    
    if format == 'natural':
        return now.strftime("%I:%M %p").lstrip('0')
    elif format == 'iso':
        return now.strftime("%H:%M:%S")
    elif format == '24h':
        return now.strftime("%H:%M")
    else:
        raise ValueError(f"Unsupported format: {format}")


def get_current_date(format: Literal['natural', 'iso', 'short'] = 'natural') -> str:
    """
    Get the current local date in the specified format.
    
    # intent: inform_date
    
    Args:
        format: Output format - 'natural', 'iso', or 'short'
        
    Returns:
        Formatted date string
        
    Examples:
        natural: "Friday, July 26, 2025"
        iso: "2025-07-26"
        short: "Jul 26, 2025"
    """
    now = datetime.datetime.now()
    
    if format == 'natural':
        return now.strftime("%A, %B %d, %Y")
    elif format == 'iso':
        return now.strftime("%Y-%m-%d")
    elif format == 'short':
        return now.strftime("%b %d, %Y")
    else:
        raise ValueError(f"Unsupported format: {format}")


def get_time_info(format: Literal['natural', 'iso', 'mixed'] = 'natural') -> str:
    """
    Get both current time and date in a combined format.
    
    # intent: inform_datetime
    
    Args:
        format: Output format - 'natural', 'iso', or 'mixed'
        
    Returns:
        Formatted datetime string
        
    Examples:
        natural: "It's 3:45 PM on Friday, July 26, 2025"
        iso: "2025-07-26T15:45:32"
        mixed: "3:45 PM, July 26, 2025"
    """
    now = datetime.datetime.now()
    
    if format == 'natural':
        time_str = get_current_time('natural')
        date_str = get_current_date('natural')
        return f"It's {time_str} on {date_str}"
    elif format == 'iso':
        return now.isoformat()
    elif format == 'mixed':
        time_str = get_current_time('natural')
        date_str = get_current_date('short')
        return f"{time_str}, {date_str}"
    else:
        raise ValueError(f"Unsupported format: {format}")


def get_weekday() -> str:
    """
    Get the current day of the week.
    
    # intent: inform_weekday
    
    Returns:
        Full weekday name (e.g., "Friday")
    """
    return datetime.datetime.now().strftime("%A")


def get_timezone_info() -> dict:
    """
    Get timezone information for the current system.
    
    # intent: inform_timezone
    
    Returns:
        Dictionary with timezone details
    """
    now = datetime.datetime.now()
    local_tz = now.astimezone().tzinfo
    
    return {
        'timezone_name': str(local_tz),
        'utc_offset': now.astimezone().strftime('%z'),
        'is_dst': bool(now.astimezone().dst())
    }


def format_duration(seconds: int) -> str:
    """
    Format a duration in seconds to human-readable format.
    
    # intent: format_time_duration
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Human-readable duration string
        
    Examples:
        "2 hours, 30 minutes"
        "45 seconds"
        "1 day, 3 hours"
    """
    if seconds < 0:
        return "Invalid duration"
    
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    
    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    else:
        return f"{', '.join(parts[:-1])}, and {parts[-1]}"


# Plugin interface for PersonaOS
class ClockTool:
    """
    Clock tool plugin interface for PersonaOS.
    Provides time and date functionality through a unified interface.
    """
    
    def __init__(self):
        self.name = "clock"
        self.description = "Provides current time, date, and related utilities"
        self.version = "1.0.0"
    
    def get_time(self, format: str = 'natural') -> str:
        """Get current time - plugin interface wrapper."""
        return get_current_time(format)
    
    def get_date(self, format: str = 'natural') -> str:
        """Get current date - plugin interface wrapper."""
        return get_current_date(format)
    
    def get_datetime(self, format: str = 'natural') -> str:
        """Get current date and time - plugin interface wrapper."""
        return get_time_info(format)
    
    def get_info(self) -> dict:
        """Get comprehensive time information."""
        return {
            'current_time': get_current_time('natural'),
            'current_date': get_current_date('natural'),
            'datetime_natural': get_time_info('natural'),
            'datetime_iso': get_time_info('iso'),
            'weekday': get_weekday(),
            'timezone': get_timezone_info()
        }


# Factory function for plugin loading
def create_tool():
    """Factory function to create the clock tool instance."""
    return ClockTool()


# Future expansion areas:
# TODO: Add alarm functionality - set_alarm(), list_alarms(), cancel_alarm()
# TODO: Add timer functionality - start_timer(), get_timer_status()
# TODO: Add world clock support for multiple timezones
# TODO: Add meeting/appointment scheduling helpers
# TODO: Add time-based reminders integration
# TODO: Add work hours/business time calculations
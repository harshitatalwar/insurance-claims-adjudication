"""
Robust Date Parsing Utilities

Handles various date formats from LLM/OCR output:
- ISO 8601: "2023-12-22", "2023-12-22T10:30:00"
- US Format: "12/22/2023", "12-22-2023"
- EU Format: "22/12/2023", "22-12-2023"
- Natural: "December 22, 2023", "22 Dec 2023"
- Indian: "22-12-2023", "22/12/2023"

Prevents 500 errors from fragile date parsing.
"""
from datetime import datetime, date
from typing import Optional, Union
import logging
from dateutil import parser as dateutil_parser

logger = logging.getLogger(__name__)


def parse_date_robust(
    date_str: Optional[str],
    default: Optional[datetime] = None
) -> Optional[datetime]:
    """
    Robustly parse date string in various formats
    
    Handles:
    - ISO 8601: "2023-12-22", "2023-12-22T10:30:00Z"
    - US Format: "12/22/2023"
    - EU Format: "22/12/2023"
    - Natural: "December 22, 2023"
    - Timestamps: "1703260800"
    
    Args:
        date_str: Date string to parse
        default: Default value if parsing fails
        
    Returns:
        Parsed datetime or default value
        
    Examples:
        >>> parse_date_robust("2023-12-22")
        datetime(2023, 12, 22, 0, 0)
        
        >>> parse_date_robust("12/22/2023")
        datetime(2023, 12, 22, 0, 0)
        
        >>> parse_date_robust("December 22, 2023")
        datetime(2023, 12, 22, 0, 0)
        
        >>> parse_date_robust("invalid", default=datetime.now())
        datetime(...)  # Returns default
    """
    if not date_str:
        return default
    
    # Clean the string
    date_str = str(date_str).strip()
    
    if not date_str:
        return default
    
    try:
        # Try dateutil parser (handles most formats automatically)
        # dayfirst=False assumes US format by default (MM/DD/YYYY)
        # But will auto-detect if day > 12
        parsed = dateutil_parser.parse(date_str, dayfirst=False, fuzzy=True)
        return parsed
        
    except (ValueError, TypeError, dateutil_parser.ParserError) as e:
        logger.warning(f"Failed to parse date '{date_str}': {e}")
        return default


def parse_date_strict(
    date_str: Optional[str],
    formats: list[str] = None
) -> Optional[datetime]:
    """
    Parse date with strict format validation
    
    Args:
        date_str: Date string to parse
        formats: List of allowed formats (default: ISO 8601 variants)
        
    Returns:
        Parsed datetime or None
        
    Raises:
        ValueError: If date doesn't match any allowed format
    """
    if not date_str:
        return None
    
    if formats is None:
        # Default: ISO 8601 variants only
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%fZ"
        ]
    
    date_str = str(date_str).strip()
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # None of the formats matched
    raise ValueError(
        f"Date '{date_str}' does not match any allowed format: {formats}"
    )


def safe_date_to_iso(
    date_value: Union[str, datetime, date, None]
) -> Optional[str]:
    """
    Safely convert any date value to ISO 8601 string
    
    Args:
        date_value: Date in any format
        
    Returns:
        ISO 8601 string (YYYY-MM-DD) or None
        
    Examples:
        >>> safe_date_to_iso("12/22/2023")
        "2023-12-22"
        
        >>> safe_date_to_iso(datetime(2023, 12, 22))
        "2023-12-22"
        
        >>> safe_date_to_iso("invalid")
        None
    """
    if not date_value:
        return None
    
    # Already a datetime
    if isinstance(date_value, datetime):
        return date_value.strftime("%Y-%m-%d")
    
    # Already a date
    if isinstance(date_value, date):
        return date_value.strftime("%Y-%m-%d")
    
    # String - parse it
    if isinstance(date_value, str):
        parsed = parse_date_robust(date_value)
        if parsed:
            return parsed.strftime("%Y-%m-%d")
    
    return None


def validate_date_range(
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    allow_same_day: bool = True
) -> bool:
    """
    Validate that end_date is after start_date
    
    Args:
        start_date: Start date
        end_date: End date
        allow_same_day: Whether same day is valid
        
    Returns:
        True if valid range, False otherwise
    """
    try:
        start = parse_date_robust(start_date) if isinstance(start_date, str) else start_date
        end = parse_date_robust(end_date) if isinstance(end_date, str) else end_date
        
        if not start or not end:
            return False
        
        if allow_same_day:
            return end >= start
        else:
            return end > start
            
    except Exception as e:
        logger.error(f"Date range validation error: {e}")
        return False


def get_days_between(
    date1: Union[str, datetime],
    date2: Union[str, datetime]
) -> Optional[int]:
    """
    Get number of days between two dates
    
    Args:
        date1: First date
        date2: Second date
        
    Returns:
        Number of days (positive if date2 > date1) or None if parsing fails
    """
    try:
        d1 = parse_date_robust(date1) if isinstance(date1, str) else date1
        d2 = parse_date_robust(date2) if isinstance(date2, str) else date2
        
        if not d1 or not d2:
            return None
        
        delta = d2 - d1
        return delta.days
        
    except Exception as e:
        logger.error(f"Days calculation error: {e}")
        return None

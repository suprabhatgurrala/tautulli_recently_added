from datetime import UTC, datetime


def format_ranges(numbers: list[int]) -> str:
    """
    Converts a list of integers into a human-readable string with ranges.

    Args:
        numbers: A list of integers. The list will be sorted before processing.

    Returns:
        A string representing the numbers, with contiguous ranges collapsed.
        Example: [1, 2, 3, 5, 6, 8] -> "1-3, 5-6, 8"
    """
    # Handle the edge case of an empty list.
    if not numbers:
        return ""

    # Sort the list and remove duplicates to ensure proper range detection.
    # Using a set is an efficient way to handle duplicates.
    sorted_unique_numbers = sorted(list(set(numbers)))

    result_parts = []
    i = 0
    # Iterate through the sorted list to find contiguous ranges.
    while i < len(sorted_unique_numbers):
        start = sorted_unique_numbers[i]
        end = start

        # Check for a contiguous sequence.
        # The loop continues as long as the next number is one greater than the current.
        while (
            i + 1 < len(sorted_unique_numbers)
            and sorted_unique_numbers[i + 1] == sorted_unique_numbers[i] + 1
        ):
            end = sorted_unique_numbers[i + 1]
            i += 1

        # If the start and end are the same, it's a single number.
        if start == end:
            result_parts.append(str(start))
        # Otherwise, it's a range.
        else:
            result_parts.append(f"{start}-{end}")

        # Move to the next number after the current range has been processed.
        i += 1

    # Join the individual parts with a comma and space.
    return ", ".join(result_parts)


def epoch_to_iso8601(epoch_s: str) -> str:
    """Convert the seconds since epoch format provided by Tautulli to ISO 8601 format supported by Discord."""
    utc_date = datetime.fromtimestamp(int(epoch_s)).astimezone(UTC)
    utc_date.replace(
        tzinfo=None
    )  # convert to naive datetime for formatting, Discord assumes UTC
    return utc_date.isoformat()


def duration_to_str(duration: int) -> str:
    """Convert a duration in seconds to a human-readable string."""
    dur = int(duration) / (1000 * 60)
    dur_hrs = dur // 60
    dur_min = dur % 60

    if dur_hrs == 0:
        dur_str = f"{dur_min:.0f}m"
    else:
        dur_str = f"{dur_hrs:.0f}h {dur_min:.0f}m"
    return dur_str


def format_originally_available_date(date: [str, datetime]) -> str:
    """Format the originally available date from Tautulli to a more readable format."""
    if date is None:
        return ""
    if isinstance(date, datetime):
        parsed_release_dt = date
    else:
        parsed_release_dt = datetime.fromisoformat(date)

    return parsed_release_dt.strftime("%B %d, %Y")

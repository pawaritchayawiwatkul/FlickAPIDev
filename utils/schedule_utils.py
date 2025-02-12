from django.utils import timezone
from datetime import datetime, timedelta
import pytz
import bisect
import string
import random

gmt7 = pytz.timezone('Asia/Bangkok')


def merge_schedule(validated_data, unavailables):
    new_start = validated_data['start']
    new_stop = validated_data['stop']
    overlap = []
    for interval in unavailables:
        start = interval.start
        stop = interval.stop
        _ = False
        if start > new_stop:
            # print('1')
            continue
        elif stop < new_start:
            # print('2')
            continue
        if start <= new_start:
            # print('3')
            new_start = start
            _ = True
        if stop >= new_stop:
            # print('4')
            new_stop = stop
            _ = True
        overlap.append(interval)

    validated_data['start'] = new_start
    validated_data['stop'] = new_stop
    return validated_data, overlap

def compute_available_time(unavailables, lessons, date, start, stop, duration, interval, gap):
    duration_td = timedelta(minutes=duration)
    interval_td = timedelta(minutes=interval)
    gap_td = timedelta(minutes=gap)
    
    # Convert start and stop into aware datetime objects once
    current_time = timezone.make_aware(datetime.combine(date, start), timezone=gmt7)
    stop_time = timezone.make_aware(datetime.combine(date, stop), timezone=gmt7)
    
    # Convert unavailables and lessons into sorted lists of tuples (start, stop)
    unavailable_intervals = sorted(
        [(timezone.make_aware(datetime.combine(date, u.start), timezone=gmt7),
          timezone.make_aware(datetime.combine(date, u.stop), timezone=gmt7)) 
         for u in unavailables if u.date == date]
    )
    
    lesson_intervals = sorted(
        [(l.datetime, l.datetime + duration_td + gap_td) for l in lessons if l.datetime.date() == date]
    )
    
    # Extract just the start times for binary search
    unavailable_starts = [start for start, _ in unavailable_intervals]
    lesson_starts = [start for start, _ in lesson_intervals]
    
    available_times = []
    
    while current_time + duration_td <= stop_time:
        end_time = current_time + duration_td
        _is_available = True

        # Use binary search to check overlapping unavailable times
        i = bisect.bisect_right(unavailable_starts, current_time) - 1
        if i >= 0 and unavailable_intervals[i][0] <= current_time < unavailable_intervals[i][1]:
            _is_available = False

        # Use binary search to check overlapping lessons
        j = bisect.bisect_right(lesson_starts, current_time) - 1
        if j >= 0 and lesson_intervals[j][0] <= current_time < lesson_intervals[j][1]:
            _is_available = False

        if _is_available:
            available_times.append({"start": current_time, "end": end_time})

        current_time += interval_td
    # Print start, stop, and unavailables if start is 17th February
    if date == datetime(2025, 2, 17).date():
        print(f"Una: {unavailable_intervals}, \n\nLessons: {lesson_intervals}, \n\nAvailables: {available_times}")
    print()
    return available_times

def generate_unique_code(existing_codes, length=8):
    """Generate a unique random code ensuring no duplicates."""
    characters = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choices(characters, k=length))
        if code not in existing_codes:
            existing_codes.add(code)  # Append new code to prevent duplicates
            return code
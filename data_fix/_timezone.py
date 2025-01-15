from teacher.models import School, UnavailableTimeOneTime, UnavailableTimeRegular
from student.models import GuestLesson
from datetime import timedelta, datetime

def subtract_time_from_time(original_time, hours=0, minutes=0, seconds=0):
    """
    Subtracts a given duration from a datetime.time object.
    
    Args:
        original_time (datetime.time): The original time.
        hours (int): Hours to subtract.
        minutes (int): Minutes to subtract.
        seconds (int): Seconds to subtract.

    Returns:
        datetime.time: The resulting time after subtraction.
    """
    # Convert datetime.time to datetime.datetime for subtraction
    today = datetime.combine(datetime.today(), original_time)
    # Create a timedelta for subtraction
    time_delta = timedelta(hours=hours, minutes=minutes, seconds=seconds)
    # Perform the subtraction
    new_time = today - time_delta
    # Convert back to datetime.time
    return new_time.time()

schools = list(School.objects.all())
for school in schools:
    school.start = subtract_time_from_time(school.start, hours=7) 
    school.stop =  subtract_time_from_time(school.stop, hours=7) 
School.objects.bulk_update(schools, ["start", "stop"])

uots = list(UnavailableTimeOneTime.objects.all())
for uot in uots:
    uot.start =  subtract_time_from_time(uot.start, hours=7) 
    uot.stop =  subtract_time_from_time(uot.stop, hours=7) 
UnavailableTimeOneTime.objects.bulk_update(uots, ["start", "stop"])

utrs = list(UnavailableTimeRegular.objects.all())
for utr in utrs:
    utr.start = subtract_time_from_time(utr.start, hours=7) 
    utr.stop = subtract_time_from_time(utr.stop, hours=7) 
UnavailableTimeRegular.objects.bulk_update(utrs, ["start", "stop"])

guest_lessons = list(GuestLesson.objects.all())
for gles in guest_lessons:
    gles.datetime = gles.datetime - timedelta(hours=7)
GuestLesson.objects.bulk_update(guest_lessons, ["datetime"])

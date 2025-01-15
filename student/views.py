from rest_framework.views import Response
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from student.models import GuestLesson, CourseRegistration, Student, Lesson, StudentTeacherRelation
from teacher.models import UnavailableTimeOneTime, UnavailableTimeRegular, Teacher
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import  Prefetch
from datetime import datetime
from django.core.exceptions import ValidationError
from student.serializers import GuestLessonSerializer, ListLessonSerializer, CourseRegistrationSerializer, LessonSerializer, ListTeacherSerializer, ListCourseRegistrationSerializer, ListLessonDateTimeSerializer, ProfileSerializer
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from utils import compute_available_time, is_available, send_notification, create_calendar_event, delete_google_calendar_event, send_lesson_requested_email
from django.core.mail import send_mail
import pytz
from dateutil.parser import isoparse  # Use this for ISO 8601 parsing


_timezone =  timezone.get_current_timezone()
gmt7 = pytz.timezone('Asia/Bangkok')

@permission_classes([IsAuthenticated])
class ProfileViewSet(ViewSet):
    def retrieve(self, request):
        try:
            user = request.user
            ser = ProfileSerializer(instance=user)
            return Response(ser.data)
        except Student.DoesNotExist:
            return Response(status=404)
    
    def update(self, request):
        user = request.user
        ser = ProfileSerializer(data=request.data)
        if ser.is_valid():
            user = ser.update(user, ser.validated_data)
            return Response(status=200)
        else:
            return Response(ser.errors, status=400)
        
    def add(self, request, teacher_uuid):
        user = request.user
        teacher = get_object_or_404(Teacher, user__uuid=teacher_uuid)
        student = get_object_or_404(Student, user_id=user.id)
        if not student.teacher.filter(id=teacher.id).exists():
            student.teacher.add(teacher)
            student.school.add(teacher.school_id)        
        return Response(status=200)
    
    def destroy(self, request):
        request.user.delete()
        return Response(status=200)
    
@permission_classes([IsAuthenticated])
class TeacherViewset(ViewSet):
    def list(self, request):
        user = request.user
        teacher = StudentTeacherRelation.objects.select_related("teacher__school", "teacher__user").order_by("favorite_teacher").filter(student__user_id=user.id)
        ser = ListTeacherSerializer(instance=teacher, many=True)
        return Response(ser.data)
    
    def favorite(self, request, code):
        fav = request.GET.get("fav", None)
        if fav in ["0", "1"]:
            fav = bool(int(fav))
            student = get_object_or_404(StudentTeacherRelation, teacher__user__uuid=code, student__user_id=request.user.id)
            student.favorite_teacher = bool(int(fav))
            student.save()
            return Response({"favorite": fav}, status=200)
        else:
            return Response({"error_messages": ["Invalid Request"]}, status=400)
    
@permission_classes([IsAuthenticated])
class CourseViewset(ViewSet):
    def favorite(self, request, code):
        fav = request.GET.get("fav", None)
        if fav in ["0", "1"]:
            fav = bool(int(fav))
            regis = CourseRegistration.objects.get(uuid=code, student__user_id=request.user.id)
            regis.student_favorite = bool(int(fav))
            regis.save()
            return Response({"favorite": fav}, status=200)
        else:
            return Response({"error_messages": ["Invalid Request"]}, status=400)
    
    def list(self, request):
        teacher_uuid = request.GET.get("teacher_uuid")
        if not teacher_uuid:
            return Response({"error_messages": ["Please Techer ID"]}, status=400)
        filters = {
            'student__user_id': request.user.id,
        }

        if teacher_uuid:
            # Assuming you have a Teacher model with a UUID field
            teacher = get_object_or_404(Teacher, user__uuid=teacher_uuid)
            filters['teacher'] = teacher

        courses = CourseRegistration.objects.select_related("course").filter(**filters)
        ser = ListCourseRegistrationSerializer(instance=courses, many=True)
        return Response(ser.data)

    def get_available_time(self, request, code):
        date_str = request.GET.get("date", None)
        if not date_str:
            return Response({"error_messages": ["Please Provide Date"]}, status=400)
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return Response({"error_message": ["Invalid Date Format"]}, status=400)
        day_number = date_obj.weekday() + 1
        try:
            regis = CourseRegistration.objects.select_related('course', 'teacher__school').prefetch_related(
                Prefetch(
                    "teacher__unavailable_reg",
                    queryset=UnavailableTimeRegular.objects.filter(
                        day=str(day_number)
                    ).only("start", "stop"),
                    to_attr="regular"
                ),
                Prefetch(
                    "teacher__unavailable_once",
                    queryset=UnavailableTimeOneTime.objects.filter(
                        date=date_obj
                    ).only("start", "stop"),
                    to_attr="once"
                ),
            ).get(uuid=code)
        except CourseRegistration.DoesNotExist:
            return Response({"error": "Can't Find Course Registration"}, status=400)
        previous_date = date_obj - timedelta(days=1)
        booked_lessons = Lesson.objects.filter(
            status__in=["CON", "PENTE", "PENST"],
            registration__teacher=regis.teacher,
            booked_datetime__date__in=[previous_date, date_obj]
        )

        unavailables = regis.teacher.regular + regis.teacher.once
        duration = regis.course.duration
        start = regis.teacher.school.start
        stop = regis.teacher.school.stop
        guest_lessons = GuestLesson.objects.filter(
            teacher=regis.teacher,
            datetime__date=date_obj
        )
        available_times = compute_available_time(unavailables, booked_lessons, guest_lessons, date_obj, start, stop, duration)

        return Response(data={
            "availables":available_times
        })
    
    def retrieve(self, request, code):
        filters = {
            "registration__uuid": code,
            "registration__student__user_id": request.user.id
        }
        lessons = Lesson.objects.filter(**filters)
        ser = ListLessonDateTimeSerializer(instance=lessons, many=True)
        return Response(ser.data, status=200)
    
    def create(self, request):
        data = dict(request.data)
        data["student_id"] = request.user.id
        ser = CourseRegistrationSerializer(data=data)
        if ser.is_valid():
            obj = ser.create(validated_data=ser.validated_data)
            return Response({"registration_id": obj.uuid}, status=200)
        else:
            return Response(ser.errors, status=400)

@permission_classes([IsAuthenticated])
class LessonViewset(ViewSet):
    def cancel(self, request, code):
        # Fetch the lesson object ensuring it belongs to the requesting user
        try:
            lesson = Lesson.objects.select_related("registration__teacher__user", "registration__course").get(code=code, registration__student__user__id=request.user.id)
        except Lesson.DoesNotExist:
            return Response({'success': "No Course Registration matches the given query."}, status=200)
        # Calculate the difference between now and the lesson's booked datetime
        now = timezone.now()
        time_difference = lesson.booked_datetime - now

        # Ensure the cancellation is at least 24 hours before the class
        if time_difference.total_seconds() >= 24 * 60 * 60:
            lesson.registration.used_lessons -= 1
            lesson.registration.save()
        lesson.status = 'CAN'
        lesson.save()

        gmt_time = lesson.booked_datetime.astimezone(gmt7)
        send_notification(
            lesson.registration.teacher.user_id, 
            "Lesson Canceled", 
            f'{request.user.first_name} on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.'
            )
        
        if lesson.student_event_id:
            delete_google_calendar_event(request.user, lesson.student_event_id)
        if lesson.teacher_event_id:
            delete_google_calendar_event(lesson.registration.teacher.user, lesson.teacher_event_id)
        
        return Response({'success': 'Lesson canceled successfully.'}, status=200)

    def confirm(self, request, code):
        try:
            lesson = Lesson.objects.select_related("registration__course", "registration__teacher__user").get(code=code, registration__student__user__id=request.user.id, status="PENST")
        except Lesson.DoesNotExist:
            return Response({'failed': "No Lesson matches the given query."}, status=200)
        lesson.status = 'CON'


        finished = lesson.booked_datetime + timedelta(minutes=lesson.registration.course.duration)
        start_time_str = lesson.booked_datetime.strftime("%Y-%m-%dT%H:%M:%S%z")
        end_time_str = finished.strftime("%Y-%m-%dT%H:%M:%S%z")
        gmt_time = lesson.booked_datetime.astimezone(gmt7)

        s_title = lesson.generate_title(is_teacher=False)
        t_title = lesson.generate_title(is_teacher=True)
        t_description = lesson.generate_description(is_teacher=True)
        s_description = lesson.generate_description(is_teacher=False)
        s_event_id = create_calendar_event(request.user, summary=s_title, description=s_description, start=start_time_str, end=end_time_str)
        t_event_id = create_calendar_event(lesson.registration.teacher.user, summary=t_title, description=t_description, start=start_time_str, end=end_time_str)

        if s_event_id:
            lesson.student_event_id = s_event_id
        if t_event_id:
            lesson.teacher_event_id = t_event_id
        lesson.save()
        
        gmt_time = lesson.booked_datetime.astimezone(gmt7)
        send_notification(
            lesson.registration.teacher.user_id, 
            "Lesson Confirmed", 
            f'{request.user.first_name} on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.'
            )
        
        return Response({'success': 'Lesson confirmed successfully.'}, status=200)
    
    def status(self, request, status):
        filters = {
            "registration__student__user_id": request.user.id,
            "booked_datetime__gte": datetime.now().date()
        }
        if status == "pending":
            filters['status__in'] = ["PENTE", "PENST"]
        elif status == "confirm":
            filters['status'] = "CON"
        _is_bangkok_time = request.GET.get("bangkok_time", "true")
        if _is_bangkok_time == "true":
            is_bangkok_time = True
        else:
            is_bangkok_time = False
        try:
            lessons = Lesson.objects.select_related("registration__teacher__user", "registration__course").filter(**filters).order_by("booked_datetime")
        except ValidationError as e:
            return Response({"error_message": e}, status=400)

        ser = ListLessonSerializer(instance=lessons, many=True)
        if is_bangkok_time:
            for data in ser.data:
                dt = isoparse(data["booked_datetime"])
                bangkok_time = timezone.make_naive(dt).astimezone(gmt7)
                data["booked_datetime"] = bangkok_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        return Response(ser.data, status=200)

    def recent(self, request):
        filters = {
            "registration__student__user_id": request.user.id
        }
        teacher_uuid = request.GET.get("teacher_uuid")
        if teacher_uuid:
            # Assuming you have a Teacher model with a UUID field
            teacher = get_object_or_404(Teacher, user__uuid=teacher_uuid)
            filters['registration__teacher_id'] = teacher.id
        lessons = Lesson.objects.select_related("registration__teacher__user", "registration__course").filter(**filters).order_by("booked_datetime")
        ser = ListLessonSerializer(instance=lessons, many=True)
        return Response(ser.data, status=200)

    def week(self, request):
        date = request.GET.get('date', None)
        if not date:
            return Response(status=400)
        date = datetime.strptime(date, '%Y-%m-%d')
        sw = date - timedelta(days=date.weekday())

        filters = {
            "registration__student__user_id": request.user.id,
            "booked_datetime__range": [sw, sw + timedelta(days=6)],
            }
        status = request.GET.get('status', None)
        if status == "pending":
            filters['status__in'] = ["PENTE", "PENST"]
        elif status == "confirm":
            filters['status'] = "CON"
        value = {}
        lessons = Lesson.objects.select_related("registration__student__user").filter(
                **filters
            ).order_by("booked_datetime")
        for i in range(7):
            filtlessons = [lesson for lesson in lessons if lesson.booked_datetime.date() == sw.date()]
            ser = ListLessonSerializer(instance=filtlessons, many=True)        
            value[sw.strftime('%Y-%m-%d')] = ser.data
            sw += timedelta(days=1)
        return Response(value)
    
    def day(self, request):
        date = request.GET.get('date', None)
        if not date:
            return Response(status=400)
        status = request.GET.get('status', None)
        filters = {
            "registration__student__user_id": request.user.id,
            "booked_datetime__date": date,
            }
        _is_bangkok_time = request.GET.get("bangkok_time", "true")
        if _is_bangkok_time == "true":
            is_bangkok_time = True
        else:
            is_bangkok_time = False
        if status == "pending":
            filters['status__in'] = ["PENTE", "PENST"]
        elif status == "confirm":
            filters['status'] = "CON"
        lessons = Lesson.objects.select_related("registration__teacher__user", "registration__course").filter(
            **filters
        ).order_by("booked_datetime")
        ser = ListLessonSerializer(instance=lessons, many=True)
        if is_bangkok_time:
            for data in ser.data:
                dt = isoparse(data["booked_datetime"])
                bangkok_time = timezone.make_naive(dt).astimezone(gmt7)
                data["booked_datetime"] = bangkok_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        return Response(ser.data, status=200)
    
    def create(self, request):
        data = dict(request.data)
        data["student_id"] = request.user.id
        _is_bangkok_time = data.get("bangkok_time", True)
        try:
            booked_date = datetime.strptime(data["booked_datetime"], "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return Response({"error_message": "Invalid Time Input"}, status=200)
        if _is_bangkok_time:
            booked_date = timezone.make_aware(booked_date, timezone=gmt7)
            data["booked_datetime"] = booked_date
        else:
            booked_date = timezone.make_aware(booked_date, timezone=_timezone)
            data["booked_datetime"] = booked_date
        registration_id = data.pop("registration_id")
        day_number = booked_date.weekday() + 1
        try:
            regis = CourseRegistration.objects.select_related('course', 'teacher__school').prefetch_related(
                    Prefetch(
                        "teacher__unavailable_reg",
                        queryset=UnavailableTimeRegular.objects.filter(
                            day=str(day_number)
                        ).only("start", "stop"),
                        to_attr="regular"
                    ),
                    Prefetch(
                        "teacher__unavailable_once",
                        queryset=UnavailableTimeOneTime.objects.filter(
                            date=booked_date
                        ).only("start", "stop"),
                        to_attr="once"
                    ),
                ).get(uuid=registration_id, student__user_id=request.user.id)
            data['registration'] = regis.pk
        except CourseRegistration.DoesNotExist:
            return Response({"error": "Invalid Course UUID"}, status=400)
        ser = LessonSerializer(data=data)
        if ser.is_valid():
            previous_date = booked_date - timedelta(days=1)
            booked_lessons = Lesson.objects.filter(
                status__in=["CON", "PENTE", "PENST"],
                registration__teacher=regis.teacher,
                booked_datetime__date__in=[previous_date, booked_date]
            )
            guest_lessons = GuestLesson.objects.filter(
                teacher=regis.teacher,
                datetime__date__in=[previous_date, booked_date]
            )
            unavailables = regis.teacher.regular + regis.teacher.once
            if not is_available(unavailables, booked_lessons, guest_lessons, booked_date, regis.course.school.start, regis.course.school.stop, regis.course.duration):
                return Response({"error": "Invalid Time s"}, status=400)
            obj = ser.create(validated_data=ser.validated_data)

            gmt_time = obj.booked_datetime.astimezone(gmt7)
            send_notification(
                regis.teacher.user_id, 
                "Lesson Requested!", 
                f'{request.user.first_name} on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.'
                )
            return Response({"booked_date": obj.booked_datetime}, status=200)
        else:
            return Response(ser.errors, status=400)
        
class GuestViewset(ViewSet):
    def booking_screen(self, request, code):
        return render(request, "booking.html", {"uuid": code})

    def create_guest_lesson(self, request, code):
        data = dict(request.data)
        ser = GuestLessonSerializer(data=data)
        booked_date = datetime.strptime(data["datetime"], "%Y-%m-%dT%H:%M:%SZ")
        booked_date = timezone.make_aware(booked_date, timezone=gmt7)
        data["datetime"] = booked_date
        if ser.is_valid():
            day_number = booked_date.weekday() + 1
            try:
                teacher = Teacher.objects.select_related("school", "user").prefetch_related(
                    Prefetch(
                        "unavailable_reg",
                        queryset=UnavailableTimeRegular.objects.filter(
                            day=str(day_number)
                        ).only("start", "stop"),
                        to_attr="regular"
                    ),
                    Prefetch(
                        "unavailable_once",
                        queryset=UnavailableTimeOneTime.objects.filter(
                            date=booked_date
                        ).only("start", "stop"),
                        to_attr="once"
                    ),
                ).get(user__uuid=code)
                ser.validated_data['teacher_id'] = teacher.pk
            except Teacher.DoesNotExist:
                return Response({"Invalid": "UUID"}, status=400)
            name = ser.validated_data.get("name")
            duration = ser.validated_data.get("duration")
            mode = "Online" if ser.validated_data.get("online", False) else "Onsite"  

            previous_date = booked_date - timedelta(days=1)
            booked_lessons = Lesson.objects.filter(
                status__in=["CON", "PENTE", "PENST"],
                registration__teacher=teacher,
                booked_datetime__date__in=[previous_date, booked_date]
            )
            guest_lessons = GuestLesson.objects.filter(
                teacher=teacher,
                datetime__date__in=[previous_date, booked_date]
            )
            unavailables = teacher.regular + teacher.once
            start = teacher.school.start
            stop = teacher.school.stop

            if not is_available(unavailables, booked_lessons, guest_lessons, booked_date, start, stop, duration):
                return Response({"error": "Invalid Time"}, status=400)

            lesson = ser.create(validated_data=ser.validated_data)
            email = lesson.email
            if email != "":
                localized_datetime = lesson.datetime.astimezone(gmt7)
                formatted_datetime = localized_datetime.strftime("%Y-%m-%d %H:%M")
                send_lesson_requested_email(
                    student_name=name,
                    tutor_name=teacher.user.first_name,
                    requested_date=formatted_datetime.split(" ")[0],  # Date part
                    requested_time=formatted_datetime.split(" ")[1],  # Time part
                    duration=duration,
                    mode=mode,
                    student_email=email,
                )
            send_notification(teacher.user_id, "Lesson Requested!", f'{name} on {localized_datetime.strftime("%Y-%m-%d")} at {localized_datetime.strftime("%H:%M")}.')

            return Response({"booked_date": booked_date}, status=200)
        else:
            return Response(ser.errors, status=400)
        
    def get_available_time(self, request, code):
        start_date_str = request.GET.get("start_date", None)
        end_date_str = request.GET.get("end_date", None)
        duration = request.GET.get("duration", None)

        # Validate inputs
        if not start_date_str or not end_date_str:
            return Response({"error_messages": ["Please Provide Start and End Dates"]}, status=400)
        if not duration:
            return Response({"error_messages": ["Please Provide Duration"]}, status=400)

        try:
            duration = int(duration)
        except ValueError:
            return Response({"error_messages": ["Invalid Duration"]}, status=400)

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error_messages": ["Invalid Date Format"]}, status=400)

        if end_date < start_date:
            return Response({"error_messages": ["End Date Cannot Be Before Start Date"]}, status=400)

        try:
            teacher = Teacher.objects.select_related("school").prefetch_related(
                Prefetch(
                    "unavailable_reg",
                    queryset=UnavailableTimeRegular.objects.only("day", "start", "stop"),
                    to_attr="regular"
                ),
                Prefetch(
                    "unavailable_once",
                    queryset=UnavailableTimeOneTime.objects.filter(
                        date__range=(start_date, end_date)
                    ).only("start", "stop", "date"),
                    to_attr="once"
                ),
            ).get(user__uuid=code)
        except Teacher.DoesNotExist:
            return Response({"error_messages": "Teacher Doesn't Exist"}, status=400)

        # Prepare results
        results = {}
        current_date = start_date

        while current_date <= end_date:
            day_number = current_date.weekday() + 1

            # Filter booked lessons and guest lessons for the current date
            previous_date = current_date - timedelta(days=1)
            booked_lessons = Lesson.objects.filter(
                status__in=["CON", "PENTE", "PENST"],
                registration__teacher=teacher,
                booked_datetime__date__in=[previous_date, current_date]
            )
            guest_lessons = GuestLesson.objects.filter(
                teacher=teacher,
                datetime__date__in=[previous_date, current_date]
            )
            
            # Get regular and one-time unavailabilities for the current day
            unavailables = [
                *[u for u in teacher.regular if u.day == str(day_number)],
                *[u for u in teacher.once if u.date == current_date]
            ]

            # Compute available times for the current day
            start = teacher.school.start
            stop = teacher.school.stop
            available_times = compute_available_time(
                unavailables, booked_lessons, guest_lessons, current_date, start, stop, duration
            )

            # Add to results
            results[current_date.strftime("%Y-%m-%d")] = available_times

            # Move to the next day
            current_date += timedelta(days=1)

        return Response(data={"available_times": results})

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from teacher.models import Teacher, TeacherCourses
from teacher.serializers import TeacherStudentUpdateSerializer, ListGuestLessonSerializer, StudentSearchSerializer, SchoolSerializer, UnavailableTimeSerializer, LessonSerializer, TeacherCourseDetailwithStudentSerializer, TeacherCourseDetailSerializer, RegularUnavailableSerializer, OnetimeUnavailableSerializer, UnavailableTimeOneTime, UnavailableTimeRegular, TeacherCourseListSerializer, CourseSerializer, ProfileSerializer, ListStudentSerializer, ListCourseRegistrationSerializer, CourseRegistrationSerializer, ListLessonSerializer
from student.models import Student, StudentTeacherRelation, CourseRegistration, Lesson, GuestLesson
from django.core.exceptions import ValidationError
from rest_framework.views import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from django.db.models import Prefetch
from utils import merge_schedule, compute_available_time, is_available, send_notification, create_calendar_event, delete_google_calendar_event, send_lesson_confirmation_email, send_cancellation_email_html
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Prefetch
from django.core.mail import send_mail
import pytz
from dateutil.parser import isoparse  # Use this for ISO 8601 parsing

_timezone =  timezone.get_current_timezone()
gmt7 = pytz.timezone('Asia/Bangkok')
print(_timezone)
@permission_classes([IsAuthenticated])
class UnavailableTimeViewset(ViewSet):
    def one_time(self, request):
        data = request.data
        data['user_id'] = request.user.id
        ser = OnetimeUnavailableSerializer(data=data)
        if ser.is_valid():
            date = ser.validated_data['date']
            teacher_id = ser.validated_data['teacher_id']
            unavailables = list(UnavailableTimeOneTime.objects.filter(date=date, teacher_id=teacher_id).only("start", "stop"))
            validated_data, overlap = merge_schedule(ser.validated_data, unavailables)
            ids_to_delete = [int(instance.id) for instance in overlap]
            UnavailableTimeOneTime.objects.filter(id__in=ids_to_delete).delete()
            ser.create(validated_data)
            return Response(ser.data, status=200)
        return Response(ser.errors, status=400)
    
    def regular(self, request):
        data = request.data
        data['user_id'] = request.user.id
        days = data['day']
        for day in days:
            data['day'] = day
            ser = RegularUnavailableSerializer(data=data)
            if ser.is_valid():
                day = ser.validated_data['day']
                teacher_id = ser.validated_data['teacher_id']
                unavailables = list(UnavailableTimeRegular.objects.filter(day=day, teacher_id=teacher_id).only("start", "stop"))
                validated_data, overlap = merge_schedule(ser.validated_data, unavailables)
                ids_to_delete = [int(instance.id) for instance in overlap]
                UnavailableTimeRegular.objects.filter(id__in=ids_to_delete).delete()
                ser.create(validated_data)
            else:
                return Response(ser.errors, status=400)
        return Response(status=200)

    def retrieve(self, request):
        date = request.GET.get("date", None)
        if not date:
            return Response(status=400)
        date = datetime.strptime(date, '%Y-%m-%d')
        day_number = date.weekday() + 1
        print(day_number)
        teacher = Teacher.objects.prefetch_related(
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
                    date=date
                ).only("start", "stop"),
                to_attr="once"
            ),
        ).get(user__id=request.user.id)

        unavailable_regular = UnavailableTimeSerializer(teacher.regular, many=True).data
        unavailable_times = UnavailableTimeSerializer(teacher.once, many=True).data
        return Response(data={
            "unavailable": list(unavailable_regular) + list(unavailable_times),
        })

    def remove(self, request, code):
        try:
            unavailable = UnavailableTimeRegular.objects.get(code=code, teacher__user_id=request.user.id)
        except UnavailableTimeRegular.DoesNotExist:
            try:
                unavailable = UnavailableTimeOneTime.objects.get(code=code, teacher__user_id=request.user.id)
            except UnavailableTimeOneTime.DoesNotExist:
                return Response(status=400)
        unavailable.delete()
        return Response()
    
@permission_classes([IsAuthenticated])
class CourseViewset(ViewSet):
    def favorite(self, request, code):
        fav = request.GET.get("fav", None)
        if fav in ["0", "1"]:
            fav = bool(int(fav))
            regis = get_object_or_404(TeacherCourses, course__uuid=code, teacher__user_id=request.user.id)
            regis.favorite = bool(int(fav))
            regis.save()
            return Response({"favorite": fav}, status=200)
        else:
            return Response({"error_messages": ["Invalid Request"]}, status=400)
        
    def list(self, request):
        teacher_course = TeacherCourses.objects.select_related("course").filter(teacher__user_id=request.user.id)
        ser = TeacherCourseListSerializer(instance=teacher_course, many=True)
        return Response(ser.data)
    
    def create(self, request):
        data = dict(request.data)
        data["user_id"] = request.user.id
        ser = CourseSerializer(data=data)
        if ser.is_valid():
            ser.create(validated_data=ser.validated_data)
            return Response(ser.data, status=200)
        else:
            return Response(ser.errors, status=400)
    
    def remove(self, request, code):
        try:
            tcourse = TeacherCourses.objects.get(teacher__user_id=request.user.id, course__uuid=code)
            tcourse.delete()
        except TeacherCourses.DoesNotExist:
            return Response({"error_messages": ["Invalid UUID"]}, status=400)
        return Response(status=200)

    def retrieve(self, request, code):
        try:
            tcourse = TeacherCourses.objects.select_related("course").prefetch_related(Prefetch('course__registration')).get(teacher__user_id=request.user.id, course__uuid=code)
        except TeacherCourses.DoesNotExist:
            return Response({"error_messages": ["Invalid UUID"]}, status=400)
        ser = TeacherCourseDetailSerializer(instance=tcourse)
        return Response(ser.data)

    def retrieve_with_student(self, request, code):
        try:
            tcourse = TeacherCourses.objects.select_related("course").prefetch_related(Prefetch('course__registration')).get(teacher__user_id=request.user.id, course__uuid=code)
        except TeacherCourses.DoesNotExist:
            return Response({"error_messages": ["Invalid UUID"]}, status=400)
        ser = TeacherCourseDetailwithStudentSerializer(instance=tcourse)
        return Response(ser.data)
    
@permission_classes([IsAuthenticated])
class ProfileViewSet(ViewSet):
    def retrieve(self, request):
        user = request.user
        try:
            ser = ProfileSerializer(instance=user)
            return Response(ser.data)
        except Teacher.DoesNotExist:
            return Response(status=404)
    
    def update(self, request):
        user = request.user
        ser = ProfileSerializer(data=request.data)
        if ser.is_valid():
            user = ser.update(user, ser.validated_data)
            return Response(status=200)
        else:
            return Response(ser.errors, status=400)

    def destroy(self, request):
        request.user.delete()
        return Response(status=200)
        
@permission_classes([IsAuthenticated])
class SchoolViewSet(ViewSet):
    def retrieve(self, request):
        user = request.user
        try:
            teacher = Teacher.objects.select_related("school").get(user_id=user.id)
            ser = SchoolSerializer(instance=teacher.school)
            return Response(ser.data)
        except Teacher.DoesNotExist:
            return Response(status=404)
        
    def update(self, request):
        ser = SchoolSerializer(data=request.data)

        if ser.is_valid():        
            try:
                teacher = Teacher.objects.select_related("school").get(user_id=request.user.id).school
            except Teacher.DoesNotExist:
                return Response(status=400)
            school = ser.update(teacher, ser.validated_data)
            return Response(ser.data, status=200)
        else: 
            return Response(ser.errors, status=400)
        

@permission_classes([IsAuthenticated])
class StudentViewset(ViewSet):
    def update(self, request, code):
        ser = TeacherStudentUpdateSerializer(data=request.data)
        if ser.is_valid():
            try:
                student_relation = StudentTeacherRelation.objects.get(
                    student__user__uuid=code,
                    teacher__user_id=request.user.id,
                )
            except StudentTeacherRelation.DoesNotExist:
                return Response(status=400)
            ser.update(student_relation, ser.validated_data)
            return Response(status=200)
        else:
            return Response(ser.errors, status=400)
    
    def add(self, request, code):
        try:
            student = Student.objects.select_related("user").get(user__uuid=code)
        except:
            return Response({"error_messages": "Student not found"}, status=400)
        user = request.user
        teacher = get_object_or_404(Teacher, user_id=user.id)
        if not student.teacher.filter(id=student.id).exists():
            try:
                StudentTeacherRelation.objects.get(student=student, teacher=teacher)
                return Response({"error_messages": "Already Add"}, status=400)
            except StudentTeacherRelation.DoesNotExist:
                StudentTeacherRelation.objects.create(
                    student=student,
                    teacher=teacher,
                    student_first_name=student.user.first_name,
                    student_last_name=student.user.last_name,
                )
        return Response(status=200)
    
    def search(self, request):
        phonenumber = request.GET.get("phone_number", None)
        if not phonenumber:
            return Response({"error": "Phone Number Not Given"}, status=400)
        try:
            student = Student.objects.get(user__phone_number=phonenumber)
        except Student.DoesNotExist:
            return Response({"error": "Student Not Found"}, status=400)
        ser = StudentSearchSerializer(instance=student)
        return Response(ser.data, status=200)
    
    def list(self, request):
        students = StudentTeacherRelation.objects.select_related("student__user").filter(teacher__user_id=request.user.id)
        ser = ListStudentSerializer(instance=students, many=True)
        return Response(ser.data)
    
    def favorite(self, request, code):
        fav = request.GET.get("fav", None)
        if fav in ["0", "1"]:
            fav = bool(int(fav))
            rel = get_object_or_404(StudentTeacherRelation, student__user__uuid=code, teacher__user_id=request.user.id)
            rel.favorite_student = bool(int(fav))
            rel.save()
            return Response({"favorite": fav}, status=200)
        else:
            return Response({"error_messages": ["Invalid Request"]}, status=400)
    
@permission_classes([IsAuthenticated]) 
class RegistrationViewset(ViewSet):
    def favorite(self, request, code):
        fav = request.GET.get("fav", None)
        if fav in ["0", "1"]:
            fav = bool(int(fav))
            regis = get_object_or_404(CourseRegistration, uuid=code, teacher__user_id=request.user.id)
            regis.teacher_favorite = bool(int(fav))
            regis.save()
            return Response({"favorite": fav}, status=200)
        else:
            return Response({"error_messages": ["Invalid Request"]}, status=400)
        
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
        
        guest_lessons = GuestLesson.objects.filter(
            teacher=regis.teacher,
            datetime__date=date_obj
        )

        unavailables = regis.teacher.regular + regis.teacher.once
        duration = regis.course.duration
        start = regis.teacher.school.start
        stop = regis.teacher.school.stop
        available_times = compute_available_time(unavailables, booked_lessons, guest_lessons, date_obj, start, stop, duration)

        return Response(data={
            "availables":available_times
        })
    

    def list(self, request):
        filters = {
            'teacher__user_id': request.user.id,
        }
        student_uuid = request.GET.get("student_uuid")
        if student_uuid:
            # Assuming you have a Teacher model with a UUID field
            student = get_object_or_404(Student, user__uuid=student_uuid)
            filters['student'] = student

        courses = CourseRegistration.objects.select_related("course").filter(**filters)
        ser = ListCourseRegistrationSerializer(instance=courses, many=True)
        return Response(ser.data)
    
    def retrieve(self, request, code):
        filters = {
            "registration__uuid": code,
            "registration__teacher__user_id": request.user.id
        }
        lessons = Lesson.objects.select_related("registration__student__user", "registration__course").filter(**filters)
        ser = ListLessonSerializer(instance=lessons, many=True)
        return Response(ser.data, status=200)
    
    def create(self, request):
        data = dict(request.data)
        data["teacher_id"] = request.user.id
        ser = CourseRegistrationSerializer(data=data)
        if ser.is_valid():
            obj = ser.create(validated_data=ser.validated_data)
            return Response({"registration_id": obj.uuid}, status=200)
        else:
            return Response(ser.errors, status=400)

@permission_classes([IsAuthenticated])
class LessonViewset(ViewSet):
    def cancel(self, request, code):
        try:
            lesson = Lesson.objects.select_related("registration").get(code=code, registration__teacher__user__id=request.user.id)
        except Lesson.DoesNotExist:
            return Response({'failed': "No Lesson matches the given query."}, status=400)

        now = timezone.now()
        time_difference = lesson.booked_datetime - now

        if time_difference.total_seconds() >= 24 * 60 * 60:
            lesson.registration.used_lessons -= 1
            lesson.registration.save()
        lesson.status = 'CAN'
        lesson.save()

        gmt_time = lesson.booked_datetime.astimezone(gmt7)
        send_notification(lesson.registration.student.user_id, "Lesson Canceled!", f'{request.user.first_name} on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.')
        if lesson.student_event_id:
            delete_google_calendar_event(lesson.registration.student, lesson.student_event_id)
        if lesson.teacher_event_id:
            delete_google_calendar_event(request.user, lesson.teacher_event_id)
        
        return Response({'success': 'Lesson canceled successfully.'}, status=200)

    def confirm(self, request, code):
        try:
            lesson = Lesson.objects.select_related("registration__course", "registration__student__user").get(code=code, registration__teacher__user__id=request.user.id, status="PENTE")
        except Lesson.DoesNotExist:
            return Response({'failed': "No Lesson matches the given query."}, status=200)
        lesson.status = 'CON'
        
        finished = lesson.booked_datetime + timedelta(minutes=lesson.registration.course.duration)
        start_time_str = lesson.booked_datetime.strftime("%Y-%m-%dT%H:%M:%S%z")
        end_time_str = finished.strftime("%Y-%m-%dT%H:%M:%S%z")

        s_title = lesson.generate_title(is_teacher=False)
        t_title = lesson.generate_title(is_teacher=True)
        t_description = lesson.generate_description(is_teacher=True)
        s_description = lesson.generate_description(is_teacher=False)
        s_event_id = create_calendar_event(lesson.registration.student.user, summary=s_title, description=s_description, start=start_time_str, end=end_time_str)
        t_event_id = create_calendar_event(request.user, summary=t_title, description=t_description, start=start_time_str, end=end_time_str)

        if s_event_id:
            lesson.student_event_id = s_event_id
        if t_event_id:
            lesson.teacher_event_id = t_event_id
        lesson.save()

        gmt_time = lesson.booked_datetime.astimezone(gmt7)
        send_notification(
            lesson.registration.student.user_id, 
            "Lesson Confirmed!", 
            f'{request.user.first_name} on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.'
            )
        
        return Response({'success': 'Lesson confirmed successfully.'}, status=200)
    
    def attended(self, request, code):
        try:
            lesson = Lesson.objects.select_related("registration__course", "registration__student").get(code=code, registration__teacher__user__id=request.user.id, status="CON")
        except Lesson.DoesNotExist:
            return Response({'failed': "No Lesson matches the given query."}, status=200)
    
        if lesson.booked_datetime >= timezone.now():
            return Response({'failed': "Has Not passed Booked Datetime."}, status=200)
        
        lesson.status = 'COM'
        lesson.save()
        lesson.registration.used_lessons += 1
        lesson.registration.save()
        
        gmt_time = lesson.booked_datetime.astimezone(gmt7)
        send_notification(
            lesson.registration.student.user_id, 
            "Lesson Attended!", 
            f'{request.user.first_name} on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.'
            )
        
        return Response({'success': 'Lesson attended successfully.'}, status=200)
    
    def missed(self, request, code):
        try:
            lesson = Lesson.objects.select_related("registration__course", "registration__student").get(code=code, registration__teacher__user__id=request.user.id, status="CON")
        except Lesson.DoesNotExist:
            return Response({'failed': "No Lesson matches the given query."}, status=200)
    
        if lesson.booked_datetime >= timezone.now():
            return Response({'failed': "Has Not passed Booked Datetime."}, status=200)

        lesson.status = 'MIS'
        lesson.save()

        gmt_time = lesson.booked_datetime.astimezone(gmt7)
        send_notification(
            lesson.registration.student.user_id, 
            "Lesson Missed!", 
            f'{request.user.first_name} on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.'
            )

        
        return Response({'success': 'Lesson marked as missed.'}, status=200)
        
    def status(self, request, status):
        filters = {
            "registration__teacher__user_id": request.user.id,
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
            lessons = Lesson.objects.select_related(
                "registration__student__user", "registration__course"
                ).filter(**filters).order_by("booked_datetime")
        except ValidationError as e:
            return Response({"error_message": e}, status=400)
        ser = ListLessonSerializer(instance=lessons, many=True)
        if is_bangkok_time:
            for data in ser.data:
                dt = isoparse(data["booked_datetime"])
                bangkok_time = timezone.make_naive(dt).astimezone(gmt7)
                data["booked_datetime"] = bangkok_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        return Response(ser.data, status=200)
    

    def day(self, request):
        date = request.GET.get('date', None)
        if not date:
            return Response(status=400)
        status = request.GET.get('status', None)
        filters = {
            "registration__teacher__user_id": request.user.id,
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
        lessons = Lesson.objects.select_related("registration__student__user").filter(
            **filters
        ).order_by("booked_datetime")
        ser = ListLessonSerializer(instance=lessons, many=True)
        if is_bangkok_time:
            for data in ser.data:
                dt = isoparse(data["booked_datetime"])
                bangkok_time = timezone.make_naive(dt).astimezone(gmt7)
                data["booked_datetime"] = bangkok_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        return Response(ser.data)

    def create(self, request):
        data = dict(request.data)
        data["teacher_id"] = request.user.id
        _is_bangkok_time = data.get("bangkok_time", True)
        try:
            booked_date = datetime.strptime(data["booked_datetime"], "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return Response({"error_message": "Invalid Time Input"})
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
                ).get(uuid=registration_id, teacher__user_id=request.user.id)
            data['registration'] = regis.pk
        except CourseRegistration.DoesNotExist:
            return Response({"error": "Invalid Course UUID"})
        
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
            start = regis.course.school.start
            stop = regis.course.school.stop
            duration = regis.course.duration
            if not is_available(unavailables, booked_lessons, guest_lessons, booked_date, start, stop, duration):
                return Response({"error": "Invalid Time"}, status=400)
            obj = ser.create(validated_data=ser.validated_data)

            gmt_time = obj.booked_datetime.astimezone(gmt7)
            send_notification(
                regis.student.user_id,
                "Lesson Requested!", 
                f'{request.user.first_name} on {gmt_time.strftime("%Y-%m-%d")} at {gmt_time.strftime("%H:%M")}.'
            )

            return Response({"booked_date": obj.booked_datetime}, status=200)
        else:
            return Response(ser.errors, status=400)

@permission_classes([IsAuthenticated])   
class GuestViewset(ViewSet):
    def cancel(self, request, code):
        try:
            lesson = GuestLesson.objects.get(code=code, teacher__user__id=request.user.id)
        except GuestLesson.DoesNotExist:
            return Response({'failed': "No Lesson matches the given query."}, status=200)
        
        lesson.status = 'CAN'
        lesson.save()
        
        if lesson.email != "":
            localized_datetime = lesson.datetime.astimezone(gmt7)
            lesson_date = localized_datetime.strftime("%Y-%m-%d")
            lesson_time = localized_datetime.strftime("%H:%M")

            send_cancellation_email_html(
                student_name=lesson.name,  # Assuming `name` is the student name in the GuestLesson model
                tutor_name=request.user.first_name,  # Teacher's first name
                lesson_date=lesson_date,
                lesson_time=lesson_time,
                duration=lesson.duration,
                mode="Online" if lesson.online else "Onsite",  # Adjust based on the lesson mode
                student_email=lesson.email
            )

        if lesson.teacher_event_id:
            delete_google_calendar_event(request.user, lesson.teacher_event_id)
        
        return Response({'success': 'Lesson canceled successfully.'}, status=200)
    
    def confirm(self, request, code):
        try:
            lesson = GuestLesson.objects.get(code=code, teacher__user__id=request.user.id, status="PEN")
        except GuestLesson.DoesNotExist:
            return Response({'failed': "No Lesson matches the given query."}, status=400)
        
        lesson.status = 'CON'

        # Calculate the lesson's start and end times
        finished = lesson.datetime + timedelta(minutes=lesson.duration)
        start_time_str = lesson.datetime.strftime("%Y-%m-%dT%H:%M:%S%z")
        end_time_str = finished.strftime("%Y-%m-%dT%H:%M:%S%z")

        # Dynamically create the summary using student and course info
        if lesson.online:
            summary = f"{lesson.name} - {lesson.duration} min (Online)"
        else:
            summary = f"{lesson.name} - {lesson.duration} min"

        # Optionally, create a detailed description
        description = lesson.generate_description()

        # Create a calendar event for the teacher
        t_event_id = create_calendar_event(
            user=request.user, 
            summary=summary, 
            description=description, 
            start=start_time_str, 
            end=end_time_str
        )

        if t_event_id:
            lesson.teacher_event_id = t_event_id
        lesson.save()

        # Send confirmation email
        if lesson.email:
            localized_datetime = lesson.datetime.astimezone(gmt7)
            formatted_date = localized_datetime.strftime("%Y-%m-%d")
            formatted_time = localized_datetime.strftime("%H:%M")

            send_lesson_confirmation_email(
                user_name=lesson.name,  # Assuming the guest lesson has a `name` field
                tutor_name=request.user.first_name,  # Teacher's first name
                student_name=lesson.name,  # Guest student's name
                lesson_date=formatted_date,
                lesson_time=formatted_time,
                lesson_duration=lesson.duration,
                mode="Online" if lesson.online else "Onsite",  # Adjust based on the lesson mode
                user_email=lesson.email
            )

        return Response({'success': 'Lesson confirmed successfully.'}, status=200)
    
    def status(self, request, status):
        filters = {
            "teacher__user_id": request.user.id,
            "datetime__gte": datetime.now().date()
        }

        _is_bangkok_time = request.GET.get("bangkok_time", "true")
        if _is_bangkok_time == "true":
            is_bangkok_time = True
        else:
            is_bangkok_time = False

        if status == "pending":
            filters['status'] = "PEN"
        elif status == "confirm":
            filters['status'] = "CON"
        try:
            lessons = GuestLesson.objects.filter(**filters).order_by("datetime")
        except ValidationError as e:
            return Response({"error_message": e}, status=400)
        ser = ListGuestLessonSerializer(instance=lessons, many=True)
        if is_bangkok_time:
            for data in ser.data:
                dt = isoparse(data["datetime"])
                bangkok_time = timezone.make_naive(dt).astimezone(gmt7)
                data["datetime"] = bangkok_time.strftime('%Y-%m-%dT%H:%M:%SZ')       
        return Response(ser.data, status=200)
    
    def list(self, request):
        filters = {
            "teacher__user_id": request.user.id,
            }

        date = request.GET.get('date', None)
        if date:
            date = datetime.strptime(date, '%Y-%m-%d')
            filters['datetime__date'] = date

        _is_bangkok_time = request.GET.get("bangkok_time", "true")
        if _is_bangkok_time == "true":
            is_bangkok_time = True
        else:
            is_bangkok_time = False

        status = request.GET.get('status', None)
        if status == "pending":
            filters['status'] = "PEN"
        elif status == "confirm":
            filters['status'] = "CON"
        
        lessons = GuestLesson.objects.filter(
                **filters
            ).order_by("datetime")
        ser = ListGuestLessonSerializer(instance=lessons, many=True) 
        if is_bangkok_time:
            for data in ser.data:
                dt = isoparse(data["datetime"])
                bangkok_time = timezone.make_naive(dt).astimezone(gmt7)
                data["datetime"] = bangkok_time.strftime('%Y-%m-%dT%H:%M:%SZ')       
        return Response(ser.data)
    


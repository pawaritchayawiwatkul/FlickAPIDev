from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from django.db.models import Prefetch
from datetime import datetime, timedelta
from student.models import Lesson, CourseRegistration, StudentTeacherRelation, Student
from school.models import School, Course  # Ensure Admin model is imported
from teacher.models import Teacher
from manager.models import Admin
from manager.serializers import CourseRegistrationSerializer, CourseSerializer
from rest_framework.decorators import action
from core.models import User
from core.serializers import CreateUserSerializer, UserUpdateSerializer
from rest_framework import status

class CalendarViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def month(self, request):
        # Get the month parameter
        month = request.GET.get("month", None)
        if not month:
            return Response({"error": "Month parameter is required."}, status=400)

        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError:
            return Response({"error": "Invalid month format. Use 'YYYY-MM'."}, status=400)

        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)

        # Prefetch data for the admin's school
        school = School.objects.prefetch_related(
            Prefetch(
                'teacher__registration__lesson',
                queryset=Lesson.objects.prefetch_related(
                    Prefetch('registration', queryset=CourseRegistration.objects.prefetch_related(
                        'course', 'student__user'
                    ))
                ), # .filter(booked_datetime__startswith=month)
            ),
            Prefetch(
                'teacher__guestlesson',
                to_attr="guestlessons"
            ),
        ).filter(id=admin.school.id).first()

        if not school:
            return Response({"error": "School not found."}, status=404)

        # Construct response data
        lessons = []
        guest_lessons = []
        for teacher in school.teacher.all():
            registrations = teacher.__dict__["_prefetched_objects_cache"]["registration"]
            for registration in registrations:
                lessons = registration.__dict__["_prefetched_objects_cache"]["lesson"]
                for lesson in lessons:
                    start_time = lesson.booked_datetime
                    finish_time = lesson.booked_datetime + timedelta(minutes=lesson.registration.course.duration)
                    lessons.append({
                        "code": lesson.code,
                        "start_time": start_time.isoformat(),
                        "end_time": finish_time.isoformat(),
                        "course_name": registration.course.name,
                        "course_uuid": registration.course.uuid,
                        "student_first_name": registration.student.user.first_name,
                        "student_last_name": registration.student.user.last_name,
                        "student_uuid": registration.student.user.uuid,
                        "teacher_first_name": teacher.user.first_name,
                        "teacher_last_name": teacher.user.last_name,
                        "teacher_uuid": teacher.user.uuid,
                    })
            for lesson in teacher.guestlessons:
                guest_lessons.append({
                    "code": lesson.code,
                    "status": lesson.status,  
                })
                

        response_data = {
            "lesson": lessons,
            # "guest_lesson": 
        }

        return Response(response_data, status=200)

class CourseRegistrationViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)

        # Prefetch data for the admin's school, including registration and related student/course data
        school = School.objects.prefetch_related(
            Prefetch(
                'teacher__registration',  # Prefetch student for each registration
                queryset=CourseRegistration.objects.prefetch_related('course', 'student')
            ),
        ).filter(id=admin.school.id).first()

        if not school:
            return Response({"error": "School not found."}, status=404)

        # Prepare the response data for purchases
        purchases = []
        for teacher in school.teacher.all():
            registrations = teacher.__dict__["_prefetched_objects_cache"].get("registration", [])
            for registration in registrations:
                student = registration.student  # Accessing student data
                course = registration.course    # Accessing course data

                # Format the purchase details
                purchases.append({
                    "id": registration.id,  # Assuming the ID of registration is needed
                    "student_first_name": student.user.first_name,
                    "student_last_name": student.user.last_name,
                    # "avatar_url": student.avatar_url if student.avatar_url else "default-avatar-url",  # Handle missing avatar
                    "student_uuid": student.user.uuid,
                    "registered_date": registration.registered_date.isoformat(),  # Use booked datetime for the purchase time
                    "course_name": course.name,
                    "course_uuid": course.uuid,
                    "amount": f"${registration.paid_price:.2f}" if registration.paid_price else 0.0  # Assuming the `amount` field is on registration and formatted as needed
                })

        # Return the formatted response with purchases
        return Response({"purchases": purchases})

class StaffViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.select_related('school').filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)

        # Ensure the admin is associated with a school
        school = admin.school
        if not school:
            return Response({"error": "Admin is not associated with any school."}, status=404)

        # Prefetch teachers and their user data for the school
        school = School.objects.prefetch_related(
            Prefetch(
                'teacher',
                queryset=Teacher.objects.select_related('user')
            )
        ).filter(id=school.id).first()

        if not school:
            return Response({"error": "School not found."}, status=404)

        # Format the response data for employees
        employees = [
            {
                "first_name": teacher.user.first_name,
                "last_name": teacher.user.last_name,
                "uuid": teacher.user.uuid
            }
            for teacher in school.teacher.all()
        ]

        return Response({"employees": employees})
    
    def retrieve(self, request, uuid=None):
        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)

        # Retrieve the teacher by primary key (id)
        teacher = Teacher.objects.get(user__uuid=uuid, school_id=admin.school.id)
        if not teacher:
            return Response({"error": "Teacher not found."}, status=404)

        # Accessing the related user model for the teacher
        user = teacher.user

        # Prepare address (defaults to empty if not available)
        # address = {
        #     "street": user.address.street if user.address and user.address.street else "",
        #     "city": user.address.city if user.address and user.address.city else "",
        #     "state": user.address.state if user.address and user.address.state else "",
        #     "post_code": user.address.post_code if user.address and user.address.post_code else "",
        #     "country": user.address.country if user.address and user.address.country else ""
        # }

        # Prepare the detailed response for the teacher
        teacher_details = {
            "id": user.uuid,  # Using UUID as a unique identifier
            # "profile_picture": user.profile_image.url,
            "first_name": user.first_name,
            "last_name": user.last_name,  # Full name
            "email": user.email,
            "phone": user.phone_number,
        }

        return Response({"teacher": teacher_details})
        
    def client(self, request, uuid=None):
        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.select_related('school').filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)

        # Retrieve the teacher by their UUID and ensure they belong to the admin's school
        try:
            teacher = Teacher.objects.get(user__uuid=uuid, school_id=admin.school.id)
        except Teacher.DoesNotExist:
            return Response({"error": "Teacher not found."}, status=404)

        # Retrieve all students related to the teacher via the StudentTeacherRelation model
        student_relations = StudentTeacherRelation.objects.prefetch_related(
            Prefetch('student', queryset=Student.objects.select_related('user'))
        ).filter(teacher=teacher)

        # Format the response data
        clients = [
            {
                "uuid": relation.student.user.uuid,
                "name": f"{relation.student_first_name} {relation.student_last_name}",
                "phone": relation.student.user.phone_number,
            }
            for relation in student_relations
        ]

        return Response({"clients": clients})

    def edit(self, request, uuid):
        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.select_related('school').filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)

        # Retrieve the teacher by their UUID and ensure they belong to the admin's school
        try:
            teacher = Teacher.objects.get(user__uuid=uuid, school_id=admin.school.id)
        except Teacher.DoesNotExist:
            return Response({"error": "Teacher not found."}, status=404)

        # Use the UserUpdateSerializer to validate and update the user data
        serializer = UserUpdateSerializer(teacher.user, data=request.data, partial=True)  # partial=True allows partial updates
        
        if serializer.is_valid():
            serializer.save()  # Save the updated data
            return Response({"message": "User info updated successfully."}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)    
    
    def create(self, request):
        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.select_related('school').filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)

        # Deserialize the request data for the User (teacher) creation
        user_serializer = CreateUserSerializer(data=request.data)
        if not user_serializer.is_valid():
            return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Create the User instance
            user = user_serializer.save(is_teacher=True, is_admin=False, is_active=True)

            # Create the Teacher instance and associate with the School
            Teacher.objects.create(user=user, school=admin.school)


            return Response(user_serializer.data, status=status.HTTP_201_CREATED)
        except:
            return Response({"email": "already exist"}, status=status.HTTP_400_BAD_REQUEST)
    
class ClientViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.select_related('school').filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)

        # Ensure the admin is associated with a school
        school = admin.school
        if not school:
            return Response({"error": "Admin is not associated with any school."}, status=404)

        # Prefetch teachers and their user data for the school
        school = School.objects.prefetch_related(
            Prefetch(
                'student',
                queryset=Student.objects.select_related('user'),
                to_attr="students"
            )
        ).filter(id=school.id).first()

        # Format the response data for employees
        clients = [
            {
                "first_name": student.user.first_name,
                "last_name": student.user.last_name,
                "email": student.user.email,
                "uuid": student.user.uuid
            }
            for student in school.students
        ]

        return Response({"clients": clients})

    def create(self, request):
        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.select_related('school').filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)

        # Deserialize the request data for the User (teacher) creation
        user_serializer = CreateUserSerializer(data=request.data)
        if not user_serializer.is_valid():
            return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Create the User instance
            user = user_serializer.save(is_teacher=True, is_admin=False, is_active=True)

            # Create the Teacher instance and associate with the School
            student = Student.objects.create(user=user)
            student.school.add(admin.school)

            return Response({
                "success": True, 
                 "message": "Client created successfully.",
                 }, status=status.HTTP_201_CREATED)
        except:
            return Response({"email": "already exist"}, status=status.HTTP_400_BAD_REQUEST)
    
class RegistrationViewset(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request, uuid):
        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)

        # Retrieve the teacher by primary key (id)
        student = Student.objects.prefetch_related(
            Prefetch(
                "registration",
                queryset=CourseRegistration.objects.select_related("course"),
                to_attr="registrations"
                )).get(user__uuid=uuid, school=admin.school)
        if not student:
            return Response({"error": "Teacher not found."}, status=404)

        # Accessing the related user model for the teacher
        
        registrations = []
        for registration in student.registrations:
            registrations.append({
                "registration_uuid": registration.uuid,  # Using UUID as a unique identifier
                "course_name": registration.course.name,
                "registration_date": registration.registered_date,
                "paid_price": registration.paid_price
            })

        return Response({"registrations": registrations})
        

    def create(self, request, uuid=None):
        # Check if the student exists
        try:
            student = Student.objects.get(user__uuid=uuid)
        except Student.DoesNotExist:
            return Response({"error": "Student with this UUID does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # Add the student to the request data
        request_data = request.data.copy()
        request_data['student'] = student.id  # Use the primary key for the ForeignKey relation

        serializer = CourseRegistrationSerializer(data=request_data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CourseViewset(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)

        courses = Course.objects.filter(school_id=admin.school_id)
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        admin = Admin.objects.filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()  # Copy to avoid modifying the original request data
        data['school'] = admin.school.id  # Set the school as the Admin's school

        # Pass the updated data to the serializer
        serializer = CourseSerializer(data=data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
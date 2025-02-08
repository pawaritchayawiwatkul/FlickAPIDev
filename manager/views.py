from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from django.db.models import Prefetch, Sum, Count
from datetime import datetime, timedelta
from student.models import Lesson, CourseRegistration, StudentTeacherRelation, Student, Booking
from school.models import School, Course  # Ensure Admin model is imported
from teacher.models import Teacher, AvailableTime
from manager.models import Admin
from manager.serializers import ( 
    CourseRegistrationSerializer, 
    CourseSerializer, 
    PurchaseSerializer, 
    AvailableTimeSerializer, 
    LessonSerializer,
    ProfileSerializer  # Add this import
)
from core.serializers import CreateUserSerializer, UserUpdateSerializer
from rest_framework import status
from django.db.utils import IntegrityError
from internal.permissions import IsManager
from django.db import transaction
from django.utils.dateparse import parse_date


class InsightViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsManager]

    def retrieve(self, request):
        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)

        total_earnings = CourseRegistration.objects.filter(course__school=admin.school_id).aggregate(
            total_paid_price=Sum('paid_price')
        )['total_paid_price']
        # Fetch and annotate metrics for the specific school
        school_analytics = School.objects.filter(id=admin.school.id).annotate(
            purchases=Count("course__registration", distinct=True),
            staffs=Count("teacher", distinct=True),
            clients=Count("student", distinct=True),
            weekly_class=Count("course__lesson", distinct=True),
        ).first()  # Fetch the first (and only) result for this school

        # Prepare the analysis dictionary
        analysis = {
            "earnings_amount": total_earnings,
            "staffs": school_analytics.staffs or 0,
            "clients": school_analytics.clients or 0,
            "weekly_class": school_analytics.weekly_class or 0,
            "purchases": school_analytics.purchases or 0,
        }

        # Return the response
        return Response(analysis, status=200)
    
class LessonViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsManager]

    def list(self, request):
            # Get and validate request parameters
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        lesson_statuses = request.GET.getlist("lesson_status")

        # Validate date format using parse_date
        start_date = parse_date(start_date) if start_date else None
        end_date = parse_date(end_date) if end_date else None

        if start_date is None and request.GET.get("start_date"):
            return Response({"error": "Invalid start_date format. Use 'YYYY-MM-DD'."}, status=400)
        if end_date is None and request.GET.get("end_date"):
            return Response({"error": "Invalid end_date format. Use 'YYYY-MM-DD'."}, status=400)

        # Validate lesson statuses
        valid_statuses = {'PENTE', 'CON', 'COM', 'CAN'}
        if lesson_statuses and not set(lesson_statuses).issubset(valid_statuses):
            return Response({"error": f"Invalid lesson statuses. Valid statuses are {list(valid_statuses)}."}, status=400)

        # Get the Admin instance for the logged-in user
        admin = Admin.objects.filter(user_id=request.user.id).select_related("school").first()
        if not admin or not admin.school:
            return Response({"error": "Admin not found for the current user."}, status=404)

        # Build filtering conditions
        filters = {"course__school": admin.school}
        if start_date:
            filters["datetime__gte"] = start_date
        if end_date:
            filters["datetime__lte"] = end_date
        if lesson_statuses:
            filters["status__in"] = lesson_statuses

        # Fetch lessons efficiently
        lessons = (
            Lesson.objects
            .select_related("course", "teacher__user")
            .prefetch_related(
                Prefetch(
                    "booking",
                    queryset=Booking.objects.select_related("student__user"),
                    to_attr="prefetched_bookings"
                )
            )
            .filter(**filters)
        )
        print(lessons)

        # Build response data
        serialized_data = LessonSerializer(lessons, many=True).data

        return Response(serialized_data, status=200)

class CourseRegistrationViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsManager]

    def list(self, request):
        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)

        # Prefetch data for the admin's school, including registration and related student/course data
        school = School.objects.prefetch_related(
            Prefetch(
                "course",  # Prefetch all courses related to the school
                queryset=Course.objects.prefetch_related(
                    Prefetch(
                        "registration",  # Prefetch registrations related to each course
                        queryset=CourseRegistration.objects.select_related("student__user"),
                        to_attr="prefetched_registrations",  # Store prefetched registrations in this attribute
                    )
                ),
                to_attr="prefetched_courses"  # Store prefetched courses in this attribute
            )
        ).filter(id=admin.school.id).first()

        if not school:
            return Response({"error": "School not found."}, status=404)

        # Collect registrations from the prefetched courses
        purchases = [
            registration
            for course in getattr(school, "prefetched_courses", [])
            for registration in getattr(course, "prefetched_registrations", [])
        ]

        # Serialize the data using the optimized serializer
        purchases_data = PurchaseSerializer(purchases, many=True).data

        return Response({"purchases": purchases_data})
    
    
    def payment_validation(self, request, uuid):
        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)

        # Retrieve the registration by UUID
        try:
            registration = CourseRegistration.objects.get(uuid=uuid, course__school=admin.school)
        except CourseRegistration.DoesNotExist:
            return Response({"error": "Registration not found."}, status=404)

        # Get the payment status from request data
        payment_status = request.data.get('payment_status')
        if payment_status not in ['confirm', 'denied']:
            return Response({"error": "Valid payment status is required."}, status=400)

        # If payment status is 'confirm', teacher_uuid is required
        if payment_status == 'confirm':
            teacher_uuid = request.data.get('teacher_uuid')
            if not teacher_uuid:
                return Response({"error": "Teacher UUID is required when confirming payment."}, status=400)

            # Retrieve the teacher by UUID and ensure they belong to the admin's school
            try:
                teacher = Teacher.objects.get(user__uuid=teacher_uuid, school=admin.school)
            except Teacher.DoesNotExist:
                return Response({"error": "Teacher not found or does not belong to the admin's school."}, status=404)

            registration.teacher = teacher

            # Check if the student is already associated with the teacher
            if not teacher.student.filter(id=registration.student.id).exists():
                teacher.student.add(registration.student)

        # Update the payment status
        registration.payment_status = payment_status
        registration.save()

        return Response({"message": "Payment status and teacher updated successfully."}, status=200)
    
class StaffViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsManager]

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
                queryset=Teacher.objects.select_related('user'),
                to_attr='cached_teachers'
            )
        ).filter(id=school.id).first()

        if not school:
            return Response({"error": "School not found."}, status=404)

        # Format the response data for employees
        employees = [
            {
                "profile_picture": teacher.user.profile_image.url if teacher.user.profile_image else "",
                "first_name": teacher.user.first_name,
                "last_name": teacher.user.last_name,
                "uuid": teacher.user.uuid,
                "phone_number": teacher.user.phone_number,
                "email": teacher.user.email,
            } for teacher in school.cached_teachers
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

        # Prepare the detailed response for the teacher
        teacher_details = {
            "id": user.uuid,  # Using UUID as a unique identifier
            "profile_picture": user.profile_image.url if user.profile_image else "",
            "first_name": user.first_name,
            "last_name": user.last_name,  # Full name
            "email": user.email,
            "phone_number": user.phone_number,
            "is_manager": user.is_manager,
        }

        return Response({"teacher": teacher_details})
        
    def client(self, request, uuid=None):
        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.select_related('school').filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)

        # Retrieve the teacher by their UUID and ensure they belong to the admin's school
        try:
            teacher = Teacher.objects.prefetch_related(
                Prefetch(
                    'student_relation',
                    queryset=StudentTeacherRelation.objects.select_related('student__user'),
                    to_attr='cached_student_relation'
                )
            ).get(user__uuid=uuid, school_id=admin.school.id)
        except Teacher.DoesNotExist:
            return Response({"error": "Teacher not found."}, status=404)

        # Format the response data
        clients = [
            {
                "uuid": relation.student.user.uuid,
                "name": relation.student.user.get_full_name(),
                "phone_number": relation.student.user.phone_number,
            }
            for relation in teacher.cached_student_relation
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
            instance = serializer.save()  # Save the updated data
            
                
            if instance.is_manager:
                # Create Admin instance if it doesn't exist
                Admin.objects.get_or_create(user=teacher.user, school=admin.school)
            else:
                # Remove Admin instance if it exists
                Admin.objects.filter(user=teacher.user).delete()
            
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
        
        available_times_data = request.data.get('available_time', [])
        available_time_serializer = AvailableTimeSerializer(data=available_times_data, many=True)
        if not available_time_serializer.is_valid():        
            return Response(available_time_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Create the User instance
            user = user_serializer.save(is_teacher=True)
            is_manager = request.data.get('is_manager', False)
            user.is_manager = is_manager
            user.save()
            
            # Create the Teacher instance and associate with the School
            teacher = Teacher.objects.create(user=user, school=admin.school)
            available_time_serializer.save(teacher=teacher)
            
            # If the user is a manager, create an Admin instance
            if is_manager:
                Admin.objects.create(user=user, school=admin.school)
            
            return Response(user_serializer.data, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            error_message = str(e)
            if "core_user_email_key" in error_message:
                return Response({"email": "This email is already in use."}, status=status.HTTP_400_BAD_REQUEST)
            elif "core_user_phone_number" in error_message:  # Example constraint for phone number
                return Response({"phone": "This phone number is already in use."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": "A unique constraint was violated."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An error occurred while creating the client."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ClientViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsManager]

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
                "profile_picture": student.user.profile_image.url if student.user.profile_image  else "",
                "first_name": student.user.first_name,
                "last_name": student.user.last_name,
                "uuid": student.user.uuid,
                "phone_number": student.user.phone_number,

            }
            for student in school.students
        ]

        return Response({"clients": clients})

    def retrieve(self, request, uuid=None):
        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)

        # Retrieve the teacher by primary key (id)
        student = Student.objects.filter(user__uuid=uuid, school=admin.school).first()

        if not student:
            return Response({"error": "Student not found."}, status=404)

        # Accessing the related user model for the teacher
        user = student.user

        # Prepare address (defaults to empty if not available)

        # Prepare the detailed response for the teacher
        student_detail = {
            "uuid": user.uuid,  # Using UUID as a unique identifier
            "profile_picture": user.profile_image.url if user.profile_image  else "",
            "first_name": user.first_name,
            "last_name": user.last_name,  # Full name
            "email": user.email,
            "phone_number": user.phone_number,
        }

        return Response({"student": student_detail})
    
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
            user = user_serializer.save(is_teacher=True, is_admin=False)

            # Create the Teacher instance and associate with the School
            student = Student.objects.create(user=user)
            student.school.add(admin.school)

            return Response({
                "success": True, 
                 "message": "Client created successfully.",
                 }, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            # Check the exception message for details
            error_message = str(e)

            if "core_user_email_key" in error_message:
                return Response({"email": "This email is already in use."}, status=status.HTTP_400_BAD_REQUEST)
            elif "core_user_phone_number" in error_message:  # Example constraint for phone number
                return Response({"phone": "This phone number is already in use."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": "A unique constraint was violated."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An error occurred while creating the client."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def edit(self, request, uuid):
        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.select_related('school').filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)

        # Ensure the admin is associated with a school
        school = admin.school
        if not school:
            return Response({"error": "Admin is not associated with any school."}, status=404)

        student = Student.objects.select_related('user').filter(user__uuid=uuid, school=school).first()
        if not student:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        # Retrieve and validate data for updating
        user_serializer = CreateUserSerializer(student.user, data=request.data, partial=True)
        if not user_serializer.is_valid():
            return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Save the updates to the user instance
            user_serializer.save()
            return Response({
                "success": True, 
                "message": "Client updated successfully.",
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def list_registration(self, request, uuid):
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
                "paid_price": registration.paid_price,
                "lessons_left": registration.lessons_left
            })

        return Response({"registrations": registrations})
        
    def create_registration(self, request, uuid=None):
        # Add the student to the request data
        request_data = request.data.copy()
        request_data['student_uuid'] = uuid  # Use the primary key for the ForeignKey relation

        serializer = CourseRegistrationSerializer(data=request_data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CourseViewset(ViewSet):
    permission_classes = [IsAuthenticated, IsManager]

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


class AvailableTimeViewSet(ViewSet):
    def list(self, request, uuid=None):
        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)

        # Get teacher_uuid from request parameters
        # Filter available times for the specified teacher in the admin's school
        available_times = AvailableTime.objects.filter(teacher__user__uuid=uuid, teacher__school=admin.school)
        serializer = AvailableTimeSerializer(available_times, many=True)
        return Response(serializer.data)
    
    def bulk_manage(self, request, uuid=None):
        # Retrieve the Admin instance for the logged-in user
        admin = Admin.objects.filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=status.HTTP_404_NOT_FOUND)

        # Extract request data
        create_data = request.data.get("create", [])
        delete_uuids = request.data.get("delete", [])
        update_data = request.data.get("update", [])

        updated_instances = []
        created_instances = []
        deleted_instances = []
        errors = []

        teacher_uuid = uuid  # Use the `uuid` passed in URL for teacher

        # **Handle Bulk Updates**
        if update_data:
            update_uuids = [entry.get("uuid") for entry in update_data if entry.get("uuid")]
            available_times = AvailableTime.objects.filter(uuid__in=update_uuids, teacher__school=admin.school, teacher__user__uuid=teacher_uuid)
            available_time_dict = {str(at.uuid): at for at in available_times}

            for entry in update_data:
                uuid = entry.get("uuid")
                if uuid not in available_time_dict:
                    errors.append({"uuid": uuid, "error": "UUID not found or not associated with your school"})
                    continue

                # Update instance fields
                available_time = available_time_dict[uuid]
                available_time.day = entry.get("day", available_time.day)
                available_time.start = entry.get("start", available_time.start)
                available_time.stop = entry.get("stop", available_time.stop)
                updated_instances.append(available_time)

            if updated_instances:
                with transaction.atomic():
                    AvailableTime.objects.bulk_update(updated_instances, ["day", "start", "stop"])

        # **Handle Bulk Deletions**
        if delete_uuids:
            deleted_count, _ = AvailableTime.objects.filter(uuid__in=delete_uuids, teacher__school=admin.school, teacher__user__uuid=teacher_uuid).delete()
        else:
            deleted_count = 0
        # **Handle Bulk Creations**
        if create_data:
            if not teacher_uuid:
                return Response({"error": "Teacher UUID is required for creation."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                teacher = Teacher.objects.get(user__uuid=teacher_uuid, school=admin.school)
            except Teacher.DoesNotExist:
                return Response({"error": "Teacher not found or does not belong to the admin's school."}, status=status.HTTP_404_NOT_FOUND)

            serializer = AvailableTimeSerializer(data=create_data, many=True)
            if serializer.is_valid():
                serializer.save(teacher=teacher)
                created_instances = serializer.data
            else:
                errors.extend(serializer.errors)

        # **Prepare Response**
        response_data = {
            "updated_count": len(updated_instances),
            "deleted_count": deleted_count,
            "created_count": len(created_instances),
            "errors": errors
        }

        return Response(response_data, status=status.HTTP_200_OK)

class BookingViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsManager]

    def check_in(self, request, code=None):
        try:
            booking = Booking.objects.get(code=code)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        booking.check_in = datetime.now()
        booking.save()
        return Response({"message": "Check-in successful."}, status=status.HTTP_200_OK)

    def check_out(self, request, code=None):
        try:
            booking = Booking.objects.select_related("registration").get(code=code)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        if not booking.check_in:
            return Response({"error": "Check-in is required before check-out."}, status=status.HTTP_400_BAD_REQUEST)

        booking.check_out = datetime.now()
        booking.save()
        booking.registration.lessons_left -= 1
        booking.registration.save()
        return Response({"message": "Check-out successful."}, status=status.HTTP_200_OK)

class ProfileViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsManager]

    def retrieve(self, request):
        admin = Admin.objects.filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)
        
        serializer = ProfileSerializer(instance=request.user)
        return Response(serializer.data)

    def update(self, request):
        admin = Admin.objects.filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)
        
        serializer = ProfileSerializer(instance=request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request):
        admin = Admin.objects.filter(user_id=request.user.id).first()
        if not admin:
            return Response({"error": "Admin not found for the current user."}, status=404)
        
        request.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
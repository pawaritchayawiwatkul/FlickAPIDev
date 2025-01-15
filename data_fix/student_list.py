from student.models import StudentTeacherRelation
students = list(StudentTeacherRelation.objects.select_related("student__user").filter(student_first_name="unknown", student_last_name="unknown"))
edited_student = []
for student in students:
    student.student_first_name = student.student.user.first_name
    student.student_last_name = student.student.user.last_name
    edited_student.append(student)
StudentTeacherRelation.objects.bulk_update(edited_student, fields=["student_first_name", "student_last_name"])
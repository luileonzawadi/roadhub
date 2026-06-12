import sys
from datetime import datetime, timedelta
from app import create_app
from app.models import db, User, Course, Lesson, Cohort, Enrollment, Progress, Certificate

def test_database():
    print("Initializing test database environment...")
    
    # Configure application for in-memory SQLite testing
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False
    })
    
    with app.app_context():
        # Create all tables defined in models.py
        print("Creating tables...")
        db.create_all()
        print("Tables created successfully.")
        
        # 1. Add Users (Student, Instructor, Admin)
        print("Inserting mock users...")
        student = User(email="student@roadshub.com", first_name="Kofi", last_name="Mensah", role="student")
        student.set_password("password123")
        
        instructor = User(email="instructor@roadshub.com", first_name="Amadi", last_name="Okonkwo", role="instructor")
        instructor.set_password("password123")
        
        admin = User(email="admin@roadshub.com", first_name="Elena", last_name="Toure", role="admin")
        admin.set_password("password123")
        
        db.session.add_all([student, instructor, admin])
        db.session.commit()
        print(f"Users seeded: {User.query.count()} total.")
        
        # Verify user attributes
        assert student.is_student is True
        assert instructor.is_instructor is True
        assert admin.is_admin is True
        
        # 2. Add Course
        print("Creating course...")
        course = Course(
            title="Civil 3D Road Design",
            description="Intermediate alignment geometry and corridor modeling",
            price=299.99,
            instructor_id=instructor.id
        )
        db.session.add(course)
        db.session.commit()
        
        # Verify relationships
        assert len(instructor.courses_taught) == 1
        assert instructor.courses_taught[0].title == "Civil 3D Road Design"
        
        # 3. Add Lessons
        print("Creating lessons...")
        lesson1 = Lesson(course_id=course.id, title="Alignment Basics", order_index=1)
        lesson2 = Lesson(course_id=course.id, title="Corridor Assembly Design", order_index=2)
        db.session.add_all([lesson1, lesson2])
        db.session.commit()
        
        assert len(course.lessons) == 2
        assert course.lessons[0].title == "Alignment Basics"
        
        # 4. Add Cohort
        print("Creating cohort...")
        cohort = Cohort(
            course_id=course.id,
            name="July 2026 Cohort",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=60)
        )
        db.session.add(cohort)
        db.session.commit()
        
        assert len(course.cohorts) == 1
        assert course.cohorts[0].name == "July 2026 Cohort"
        
        # 5. Enroll Student into Cohort
        print("Enrolling student...")
        enrollment = Enrollment(user_id=student.id, cohort_id=cohort.id)
        db.session.add(enrollment)
        db.session.commit()
        
        assert len(student.enrollments) == 1
        assert student.enrollments[0].cohort_id == cohort.id
        
        # 6. Mark progress
        print("Seeding lesson progress...")
        progress = Progress(enrollment_id=enrollment.id, lesson_id=lesson1.id, is_completed=True, completed_at=datetime.now())
        db.session.add(progress)
        db.session.commit()
        
        assert len(enrollment.progress_records) == 1
        assert enrollment.progress_records[0].is_completed is True
        
        # 7. Generate Certificate
        print("Creating certificate...")
        certificate = Certificate(
            user_id=student.id,
            course_id=course.id,
            certificate_code="RH-2026-TEST"
        )
        db.session.add(certificate)
        db.session.commit()
        
        assert len(student.certificates) == 1
        assert student.certificates[0].certificate_code == "RH-2026-TEST"
        
        print("\nAll database model tests and schema relationship assertions passed successfully!")
        return True

if __name__ == '__main__':
    try:
        success = test_database()
        if success:
            sys.exit(0)
    except Exception as e:
        print(f"\nDatabase test failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

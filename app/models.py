from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    """
    User model covering Students, Instructors, and Admins.
    Includes role-based properties and Flask-Login authentication compatibility.
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # 'student', 'instructor', 'admin'
    bio = db.Column(db.Text, nullable=True)
    profile_image_url = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    courses_taught = db.relationship('Course', backref='instructor', lazy=True)
    enrollments = db.relationship('Enrollment', backref='student', lazy=True, cascade="all, delete-orphan")
    certificates = db.relationship('Certificate', backref='student', lazy=True, cascade="all, delete-orphan")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    @property
    def is_student(self):
        return self.role == 'student'
        
    @property
    def is_instructor(self):
        return self.role == 'instructor'
        
    @property
    def is_admin(self):
        return self.role == 'admin'
        
    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Course(db.Model):
    """
    Course management model. Courses are created and managed by Instructors,
    and approved/published before being visible to students.
    """
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    cover_image_url = db.Column(db.String(256), nullable=True)
    price = db.Column(db.Float, default=0.0)
    is_published = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)  # Admin course approval step
    is_acp = db.Column(db.Boolean, default=False)        # Tracks readiness for Autodesk Certified Professional
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    lessons = db.relationship('Lesson', backref='course', lazy=True, cascade="all, delete-orphan")
    cohorts = db.relationship('Cohort', backref='course', lazy=True, cascade="all, delete-orphan")
    certificates = db.relationship('Certificate', backref='course', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Course {self.title}>"


class Lesson(db.Model):
    """
    Individual course lessons. Supporting text content, video URLs (YouTube/Vimeo),
    and attachments (e.g. PDF manuals, templates, plugins).
    """
    __tablename__ = 'lessons'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    content_text = db.Column(db.Text, nullable=True)
    video_url = db.Column(db.String(256), nullable=True)  # YouTube/Vimeo embed URL
    pdf_url = db.Column(db.String(256), nullable=True)    # Cloudinary PDF attachment URL
    order_index = db.Column(db.Integer, default=0)         # Manual ordering of lessons
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    progress_records = db.relationship('Progress', backref='lesson', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Lesson {self.title} [Course: {self.course_id}]>"


class Cohort(db.Model):
    """
    Cohort-based learning structure. Groups students within a course
    and defines specific start and end dates.
    """
    __tablename__ = 'cohorts'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # e.g. "Cohort 1 - July 2026"
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='cohort', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Cohort {self.name} [Course: {self.course_id}]>"


class Enrollment(db.Model):
    """
    Pivot table linking a Student (User) to a specific Course Cohort.
    Tracks overall completion status.
    """
    __tablename__ = 'enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    cohort_id = db.Column(db.Integer, db.ForeignKey('cohorts.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    progress_records = db.relationship('Progress', backref='enrollment', lazy=True, cascade="all, delete-orphan")
    
    # Ensure a user is only enrolled in a cohort once
    __table_args__ = (
        db.UniqueConstraint('user_id', 'cohort_id', name='_user_cohort_uc'),
    )
    
    def __repr__(self):
        return f"<Enrollment User: {self.user_id} Cohort: {self.cohort_id}>"


class Progress(db.Model):
    """
    Granular progress tracker. Records when a student completes a specific lesson
    within their enrolled course. Tracks time spent on learning materials.
    """
    __tablename__ = 'progress'
    
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollments.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    time_spent = db.Column(db.Integer, default=0)  # Study duration in minutes
    
    # Ensure progress per enrollment is only documented once for a given lesson
    __table_args__ = (
        db.UniqueConstraint('enrollment_id', 'lesson_id', name='_enrollment_lesson_uc'),
    )
    
    def __repr__(self):
        return f"<Progress Enrollment: {self.enrollment_id} Lesson: {self.lesson_id} Completed: {self.is_completed}>"


class Certificate(db.Model):
    """
    Course completion certificate granted to Students upon completing
    all course requirements.
    """
    __tablename__ = 'certificates'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    certificate_code = db.Column(db.String(50), unique=True, nullable=False)  # Verification code
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    verification_url = db.Column(db.String(256), nullable=True)
    
    def __repr__(self):
        return f"<Certificate {self.certificate_code} for User: {self.user_id}>"


class Payment(db.Model):
    """
    Payment transaction record for course enrollments.
    Handles both M-Pesa (local) and Stripe (international) payment methods.
    """
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='USD')
    method = db.Column(db.String(50), nullable=False)  # 'mpesa', 'stripe'
    status = db.Column(db.String(50), default='pending')  # 'pending', 'confirmed', 'failed'
    reference = db.Column(db.String(256), nullable=True)  # M-Pesa receipt or Stripe Session ID
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('payments', lazy=True, cascade="all, delete-orphan"))
    course = db.relationship('Course', backref=db.backref('payments', lazy=True, cascade="all, delete-orphan"))
    
    def __repr__(self):
        return f"<Payment {self.method} | {self.amount} {self.currency} | Status: {self.status}>"


# ──────────────────────────────────────────────────────────────────────────
# Quiz & Question Engine Models
# ──────────────────────────────────────────────────────────────────────────

class Quiz(db.Model):
    """
    Quiz model attached to a specific Lesson.
    Defines general settings such as title and target passing percentage.
    """
    __tablename__ = 'quizzes'
    
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False, unique=True)
    title = db.Column(db.String(200), nullable=False)
    passing_score = db.Column(db.Float, default=70.0)  # Required score to pass (e.g. 70.0 = 70%)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    lesson = db.relationship('Lesson', backref=db.backref('quiz', uselist=False), lazy=True)
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade="all, delete-orphan")
    attempts = db.relationship('QuizAttempt', backref='quiz', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Quiz '{self.title}' for Lesson: {self.lesson_id}>"


class Question(db.Model):
    """
    Multiple-choice question belonging to a Quiz.
    Includes an explanation to display upon auto-grading submission.
    """
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=True)  # Instructive text explaining the correct choice
    
    # Relationships
    options = db.relationship('QuestionOption', backref='question', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Question id: {self.id} on Quiz: {self.quiz_id}>"


class QuestionOption(db.Model):
    """
    Potential answer option for a multiple-choice question.
    """
    __tablename__ = 'question_options'
    
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    option_text = db.Column(db.String(256), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f"<QuestionOption id: {self.id} Correct: {self.is_correct}>"


class QuizAttempt(db.Model):
    """
    Attempt history log recording a user's score on a given Quiz.
    """
    __tablename__ = 'quiz_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)  # Percentage score (e.g. 85.0)
    passed = db.Column(db.Boolean, default=False)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('quiz_attempts', lazy=True, cascade="all, delete-orphan"))
    
    def __repr__(self):
        return f"<QuizAttempt User: {self.user_id} Quiz: {self.quiz_id} Score: {self.score}% Passed: {self.passed}>"


class Lead(db.Model):
    """
    Lead capture model for marketing and nurture sequences.
    """
    __tablename__ = 'leads'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    area_of_interest = db.Column(db.String(100), nullable=True)
    source_tag = db.Column(db.String(50), nullable=True)
    
    is_high_intent = db.Column(db.Boolean, default=False)
    pricing_page_visited = db.Column(db.Boolean, default=False)
    email_opened = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Lead {self.email} - High Intent: {self.is_high_intent}>"

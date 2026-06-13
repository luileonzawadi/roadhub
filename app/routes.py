import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, Course, Lesson, Cohort, Enrollment, Progress, Certificate, Quiz, Question, QuestionOption, QuizAttempt, Payment, Lead
from app.utils.certificate import generate_certificate_pdf
from app.utils.mpesa import initiate_stk_push
from app.utils.stripe_payment import create_checkout_session, stripe, STRIPE_WEBHOOK_SECRET

main_bp = Blueprint('main', __name__)

# ──────────────────────────────────────────────────────────────────────────
# Lesson Sequencing Check Helper
# ──────────────────────────────────────────────────────────────────────────
def check_lesson_unlocked(user_id, lesson):
    """
    Enforces sequential progression. A student can only view a lesson if:
    - All previous lessons (lower order_index) are marked completed.
    - All quizzes attached to previous lessons have been passed.
    """
    # Instructors and Admins bypass sequencing locks for design review purposes
    user = User.query.get(user_id)
    if user and (user.role == 'admin' or user.role == 'instructor'):
        return True
        
    previous_lessons = Lesson.query.filter(
        Lesson.course_id == lesson.course_id,
        Lesson.order_index < lesson.order_index
    ).order_by(Lesson.order_index).all()
    
    # Locate user enrollment
    enrollment = Enrollment.query.join(Cohort).filter(
        Enrollment.user_id == user_id,
        Cohort.course_id == lesson.course_id
    ).first()
    
    if not enrollment:
        return False
        
    for prev_les in previous_lessons:
        # Check progress completion
        progress = Progress.query.filter_by(
            enrollment_id=enrollment.id,
            lesson_id=prev_les.id,
            is_completed=True
        ).first()
        if not progress:
            return False
            
        # Check quiz pass state
        quiz = Quiz.query.filter_by(lesson_id=prev_les.id).first()
        if quiz:
            passing_attempt = QuizAttempt.query.filter_by(
                user_id=user_id,
                quiz_id=quiz.id,
                passed=True
            ).first()
            if not passing_attempt:
                return False
                
    return True


def check_and_award_certificate(user_id, course_id):
    """
    Checks if a student has completed all lessons and passed all quizzes in a course.
    If so, flags the enrollment as completed and issues a verified completion certificate.
    """
    enrollment = Enrollment.query.join(Cohort).filter(
        Enrollment.user_id == user_id,
        Cohort.course_id == course_id
    ).first()
    
    if not enrollment:
        return
        
    lessons = Lesson.query.filter_by(course_id=course_id).all()
    if not lessons:
        return
        
    for les in lessons:
        # Ensure lesson marked completed
        prog = Progress.query.filter_by(
            enrollment_id=enrollment.id,
            lesson_id=les.id,
            is_completed=True
        ).first()
        if not prog:
            return
            
        # Ensure quiz passed if present
        quiz = Quiz.query.filter_by(lesson_id=les.id).first()
        if quiz:
            passing = QuizAttempt.query.filter_by(
                user_id=user_id,
                quiz_id=quiz.id,
                passed=True
            ).first()
            if not passing:
                return
                
    # All checked out, award credential
    if not enrollment.is_completed:
        enrollment.is_completed = True
        enrollment.completed_at = datetime.utcnow()
        
        existing_cert = Certificate.query.filter_by(user_id=user_id, course_id=course_id).first()
        if not existing_cert:
            cert_code = f"RH-{datetime.now().year}-{enrollment.id:04d}"
            cert = Certificate(
                user_id=user_id,
                course_id=course_id,
                certificate_code=cert_code,
                verification_url=f"/verify/{cert_code}"
            )
            db.session.add(cert)
        db.session.commit()


# ──────────────────────────────────────────────────────────────────────────
# Standard Routes
# ──────────────────────────────────────────────────────────────────────────
@main_bp.route('/')
def index():
    """Home landing page showing public courses."""
    courses = Course.query.filter_by(is_published=True).all()
    return render_template('index.html', courses=courses)


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Mock login page to demonstrate roles: Student, Instructor, Admin."""
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('main.admin_dashboard'))
        elif current_user.is_instructor:
            return redirect(url_for('main.instructor_dashboard'))
        else:
            return redirect(url_for('main.student_dashboard'))
            
    if request.method == 'POST':
        selected_role = request.form.get('role', 'student')
        email = f"{selected_role}@roadshub.com"
        
        # Look up or create mock user for testing
        user = User.query.filter_by(email=email).first()
        if not user:
            first_names = {'student': 'Kofi', 'instructor': 'Amadi', 'admin': 'Elena'}
            last_names = {'student': 'Mensah', 'instructor': 'Okonkwo', 'admin': 'Toure'}
            
            user = User(
                email=email,
                first_name=first_names.get(selected_role, 'Demo'),
                last_name=last_names.get(selected_role, 'User'),
                role=selected_role,
                bio=f"Professional {selected_role.capitalize()} account on Roadshub."
            )
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()
            
        login_user(user)
        
        # Ensure basic mock curriculum items are seeded in DB context
        with db.session.no_autoflush:
            # Seed default courses/lessons/cohorts if admin or instructor
            if selected_role in ['admin', 'instructor', 'student']:
                admin_user = User.query.filter_by(role='admin').first() or user
                if not Course.query.first():
                    course = Course(
                        title="Advanced Civil 3D Road Design & Corridor Modeling",
                        description="Master corridor modeling, horizontal & vertical alignments, roundabouts, and drainage networks using real-world African infrastructure standards.",
                        cover_image_url="https://roadshub.org/wp-content/uploads/elementor/thumbs/CIVIL-3D-TRAINING-WHO-CAN-APPLY_062114-qqrfkl2rd3260de23hdtyl1ni6cc7n0pfx0bkneb7k.png",
                        price=450.0,
                        is_published=True,
                        is_approved=True,
                        is_acp=True,  # Enable Autodesk Certified Professional Pathway readiness tracking
                        instructor_id=admin_user.id
                    )
                    db.session.add(course)
                    db.session.commit()
                    
                    # Add Lessons
                    lesson1 = Lesson(
                        course_id=course.id,
                        title="Introduction to Alignment Coordinates",
                        description="Configure regional coordinate systems and map local terrain grids into Autodesk Civil 3D.",
                        content_text="Detailed instructions on alignment layouts, station controls, and datum checks.",
                        video_url="https://www.youtube.com/embed/dQw4w9WgXcQ",
                        order_index=1
                    )
                    lesson2 = Lesson(
                        course_id=course.id,
                        title="Corridor Modelling & Assembly Construction",
                        description="Construct detailed subassemblies for dual-carriageway alignments and drainage channels.",
                        content_text="Instructions on lane widening parameters, subgrade assemblies, and side slopes.",
                        video_url="https://www.youtube.com/embed/dQw4w9WgXcQ",
                        order_index=2
                    )
                    db.session.add_all([lesson1, lesson2])
                    db.session.commit()
                    
                    # Add Quiz to Lesson 1
                    quiz = Quiz(lesson_id=lesson1.id, title="Alignment Coordinate Competency Quiz", passing_score=70.0)
                    db.session.add(quiz)
                    db.session.commit()
                    
                    # Add Questions
                    q1 = Question(quiz_id=quiz.id, question_text="Which tool is typically used to align local coordinate grids with UTM projections?", explanation="Global Mapper allows georeferencing coordinate tables to match UTM systems before drawing corridors.")
                    db.session.add(q1)
                    db.session.commit()
                    
                    # Add Options
                    op1 = QuestionOption(question_id=q1.id, option_text="Global Mapper Transformation tool", is_correct=True)
                    op2 = QuestionOption(question_id=q1.id, option_text="Civil 3D Default Text importer", is_correct=False)
                    op3 = QuestionOption(question_id=q1.id, option_text="AutoCAD block scaling tool", is_correct=False)
                    db.session.add_all([op1, op2, op3])
                    
                    # Add Cohort
                    cohort = Cohort(
                        course_id=course.id,
                        name="July 2026 Cohort (East Africa Intake)",
                        start_date=datetime.now() + timedelta(days=15),
                        end_date=datetime.now() + timedelta(days=75),
                        is_active=True
                    )
                    db.session.add(cohort)
                    db.session.commit()
        
        flash(f"Access granted. Welcome to the {selected_role.capitalize()} portal!", "success")
        
        if user.is_admin:
            return redirect(url_for('main.admin_dashboard'))
        elif user.is_instructor:
            return redirect(url_for('main.instructor_dashboard'))
        else:
            return redirect(url_for('main.student_dashboard'))
            
    return render_template('login.html')


@main_bp.route('/logout')
def logout():
    """Log out active sessions."""
    logout_user()
    flash("You have signed out of Roadshub.", "info")
    return redirect(url_for('main.index'))


@main_bp.route('/student/dashboard')
@login_required
def student_dashboard():
    """Student view dashboard showing courses, progress and certifications."""
    # Seed enrollment for the student if none exists
    if current_user.is_student:
        existing_enrollment = Enrollment.query.filter_by(user_id=current_user.id).first()
        if not existing_enrollment:
            cohort = Cohort.query.first()
            if cohort:
                enrollment = Enrollment(user_id=current_user.id, cohort_id=cohort.id)
                db.session.add(enrollment)
                db.session.commit()

    # Query student data
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    certificates = Certificate.query.filter_by(user_id=current_user.id).all()
    payments = Payment.query.filter_by(user_id=current_user.id).order_by(Payment.created_at.desc()).all()
    
    enrollment_data = []
    for enr in enrollments:
        total_lessons = Lesson.query.filter_by(course_id=enr.cohort.course_id).count()
        completed_lessons = Progress.query.filter_by(enrollment_id=enr.id, is_completed=True).count()
        progress_percentage = int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0
        
        enrollment_data.append({
            'enrollment': enr,
            'total_lessons': total_lessons,
            'completed_lessons': completed_lessons,
            'percentage': progress_percentage
        })
        
    return render_template('student_dashboard.html', enrollment_data=enrollment_data, certificates=certificates, payments=payments)


@main_bp.route('/instructor/dashboard')
@login_required
def instructor_dashboard():
    """Instructor portal dashboard."""
    if not (current_user.is_instructor or current_user.is_admin):
        flash("Unauthorized. Instructors access only.", "danger")
        return redirect(url_for('main.index'))
        
    courses = Course.query.filter_by(instructor_id=current_user.id).all()
    students_count = Enrollment.query.join(Cohort).join(Course).filter(Course.instructor_id == current_user.id).count()
    
    return render_template('instructor_dashboard.html', courses=courses, students_count=students_count)


@main_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin controller showing revenue, user list, and course approval status."""
    if not current_user.is_admin:
        flash("Access denied. Administrator privileges required.", "danger")
        return redirect(url_for('main.index'))
        
    users = User.query.all()
    pending_courses = Course.query.filter_by(is_approved=False).all()
    all_courses = Course.query.all()
    
    total_enrollments = Enrollment.query.count()
    
    # Calculate revenue from confirmed payments
    confirmed_payments = Payment.query.filter_by(status='confirmed').all()
    revenue = sum(p.amount for p in confirmed_payments)
    
    mpesa_revenue = sum(p.amount for p in confirmed_payments if p.method == 'mpesa')
    stripe_revenue = sum(p.amount for p in confirmed_payments if p.method == 'stripe')
    
    return render_template('admin_dashboard.html', 
                           users=users, 
                           pending_courses=pending_courses, 
                           all_courses=all_courses,
                           total_enrollments=total_enrollments,
                           revenue=revenue,
                           mpesa_revenue=mpesa_revenue,
                           stripe_revenue=stripe_revenue)


# ──────────────────────────────────────────────────────────────────────────
# LMS & Sequencing Routes
# ──────────────────────────────────────────────────────────────────────────
@main_bp.route('/courses/<int:course_id>/lessons/<int:lesson_id>')
@login_required
def view_lesson(course_id, lesson_id):
    """View lesson content. Checks sequencing locks before rendering."""
    lesson = Lesson.query.get_or_404(lesson_id)
    course = Course.query.get_or_404(course_id)
    
    # Enforce lesson sequencing check
    if not check_lesson_unlocked(current_user.id, lesson):
        flash("🔒 This lesson is locked. You must complete the previous lessons and pass their quizzes first.", "warning")
        return redirect(url_for('main.student_dashboard'))
        
    lessons = Lesson.query.filter_by(course_id=course_id).order_by(Lesson.order_index).all()
    
    # Fetch student enrollment and progress record
    enrollment = Enrollment.query.join(Cohort).filter(
        Enrollment.user_id == current_user.id,
        Cohort.course_id == course_id
    ).first()
    
    progress = None
    if enrollment:
        progress = Progress.query.filter_by(enrollment_id=enrollment.id, lesson_id=lesson_id).first()
        # Log study session activity (adds study minutes automatically for testing)
        if not progress:
            progress = Progress(enrollment_id=enrollment.id, lesson_id=lesson_id, time_spent=5)
            db.session.add(progress)
        else:
            progress.time_spent = (progress.time_spent or 0) + 5  # Increment time spent
        db.session.commit()
        
    return render_template('lesson.html', course=course, lesson=lesson, lessons=lessons, progress=progress)


@main_bp.route('/lessons/<int:lesson_id>/complete', methods=['POST'])
@login_required
def complete_lesson(lesson_id):
    """Marks a lesson as completed."""
    lesson = Lesson.query.get_or_404(lesson_id)
    enrollment = Enrollment.query.join(Cohort).filter(
        Enrollment.user_id == current_user.id,
        Cohort.course_id == lesson.course_id
    ).first()
    
    if enrollment:
        progress = Progress.query.filter_by(enrollment_id=enrollment.id, lesson_id=lesson_id).first()
        if not progress:
            progress = Progress(enrollment_id=enrollment.id, lesson_id=lesson_id, is_completed=True, completed_at=datetime.utcnow(), time_spent=10)
            db.session.add(progress)
        else:
            progress.is_completed = True
            progress.completed_at = datetime.utcnow()
            
        db.session.commit()
        flash(f"Lesson '{lesson.title}' completed!", "success")
        
        # Check and award certificate if course is fully completed
        check_and_award_certificate(current_user.id, lesson.course_id)
            
    return redirect(url_for('main.view_lesson', course_id=lesson.course_id, lesson_id=lesson_id))


# ──────────────────────────────────────────────────────────────────────────
# Quiz Engine Routes
# ──────────────────────────────────────────────────────────────────────────
@main_bp.route('/courses/<int:course_id>/lessons/<int:lesson_id>/quiz')
@login_required
def view_quiz(course_id, lesson_id):
    """Renders the quiz form for the lesson."""
    lesson = Lesson.query.get_or_404(lesson_id)
    
    # Enforce sequencing check
    if not check_lesson_unlocked(current_user.id, lesson):
        flash("🔒 You must unlock this lesson before attempting the quiz.", "warning")
        return redirect(url_for('main.student_dashboard'))
        
    quiz = Quiz.query.filter_by(lesson_id=lesson_id).first_or_404()
    return render_template('quiz.html', quiz=quiz, lesson=lesson)


@main_bp.route('/courses/<int:course_id>/lessons/<int:lesson_id>/quiz/submit', methods=['POST'])
@login_required
def submit_quiz(course_id, lesson_id):
    """Auto-grades a quiz attempt, registers attempt logs, and awards certificates."""
    quiz = Quiz.query.filter_by(lesson_id=lesson_id).first_or_404()
    lesson = Lesson.query.get_or_404(lesson_id)
    
    total_questions = len(quiz.questions)
    correct_count = 0
    user_answers = {}
    
    for question in quiz.questions:
        selected_option_id = request.form.get(f"question_{question.id}")
        user_answers[str(question.id)] = selected_option_id
        
        if selected_option_id:
            option = QuestionOption.query.get(int(selected_option_id))
            if option and option.is_correct:
                correct_count += 1
                
    score_percentage = float((correct_count / total_questions) * 100) if total_questions > 0 else 0.0
    passed = score_percentage >= quiz.passing_score
    
    # Log attempt
    attempt = QuizAttempt(
        user_id=current_user.id,
        quiz_id=quiz.id,
        score=score_percentage,
        passed=passed
    )
    db.session.add(attempt)
    db.session.commit()
    
    # Cache user choices in session for review rendering
    session[f"quiz_answers_{attempt.id}"] = user_answers
    
    if passed:
        flash(f"Passed! You scored {score_percentage}% on the quiz.", "success")
        # Automatically mark progress as completed upon passing
        enrollment = Enrollment.query.join(Cohort).filter(
            Enrollment.user_id == current_user.id,
            Cohort.course_id == course_id
        ).first()
        if enrollment:
            progress = Progress.query.filter_by(enrollment_id=enrollment.id, lesson_id=lesson_id).first()
            if not progress:
                progress = Progress(enrollment_id=enrollment.id, lesson_id=lesson_id, is_completed=True, completed_at=datetime.utcnow())
                db.session.add(progress)
            else:
                progress.is_completed = True
                progress.completed_at = datetime.utcnow()
            db.session.commit()
            
            # Check if this qualifies them for a certificate
            check_and_award_certificate(current_user.id, course_id)
    else:
        flash(f"Failed. You scored {score_percentage}%. The passing grade is {quiz.passing_score}%.", "danger")
        
    return redirect(url_for('main.quiz_results', attempt_id=attempt.id))


@main_bp.route('/quiz/results/<int:attempt_id>')
@login_required
def quiz_results(attempt_id):
    """Renders MCQ answers review with explanations."""
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    if attempt.user_id != current_user.id:
        flash("Unauthorized access to attempt logs.", "danger")
        return redirect(url_for('main.student_dashboard'))
        
    quiz = Quiz.query.get(attempt.quiz_id)
    lesson = Lesson.query.get(quiz.lesson_id)
    user_answers = session.get(f"quiz_answers_{attempt_id}", {})
    
    return render_template('quiz_results.html', attempt=attempt, quiz=quiz, lesson=lesson, user_answers=user_answers)


# ──────────────────────────────────────────────────────────────────────────
# Student Analytics Route
# ──────────────────────────────────────────────────────────────────────────
@main_bp.route('/student/analytics')
@login_required
def student_analytics():
    """Aggregates learning metrics, weekly study times, weak items, and exam readiness scores."""
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    certificates_count = Certificate.query.filter_by(user_id=current_user.id).count()
    
    # 1. Study time summation
    total_minutes = db.session.query(db.func.sum(Progress.time_spent)).join(Enrollment).filter(
        Enrollment.user_id == current_user.id
    ).scalar() or 0
    
    # 2. Quiz counts and averages
    # Fetch unique quizzes for enrolled courses
    course_ids = [enr.cohort.course_id for enr in enrollments]
    total_quizzes = Quiz.query.join(Lesson).filter(Lesson.course_id.in_(course_ids)).count() if course_ids else 0
    
    attempts = QuizAttempt.query.filter_by(user_id=current_user.id).all()
    passed_attempts = [a for a in attempts if a.passed]
    passed_quizzes = len(set(a.quiz_id for a in passed_attempts))
    
    # Calculate average score of highest attempt per quiz
    quiz_highest_scores = {}
    for a in attempts:
        if a.quiz_id not in quiz_highest_scores or a.score > quiz_highest_scores[a.quiz_id]:
            quiz_highest_scores[a.quiz_id] = a.score
            
    avg_score = int(sum(quiz_highest_scores.values()) / len(quiz_highest_scores)) if quiz_highest_scores else 0
    
    # 3. Autodesk ACP Readiness Score (based on quiz averages for ACP courses)
    acp_courses = Course.query.filter(Course.id.in_(course_ids), Course.is_acp == True).all() if course_ids else []
    acp_readiness = 0
    if acp_courses:
        acp_quiz_scores = []
        for c in acp_courses:
            for les in c.lessons:
                quiz = Quiz.query.filter_by(lesson_id=les.id).first()
                if quiz:
                    score = quiz_highest_scores.get(quiz.id, 0.0)
                    acp_quiz_scores.append(score)
        acp_readiness = int(sum(acp_quiz_scores) / len(acp_quiz_scores)) if acp_quiz_scores else 0
        
    # 4. Strength & Weakness Audit
    strong_topics = []
    weak_topics = []
    
    if course_ids:
        lessons = Lesson.query.filter(Lesson.course_id.in_(course_ids)).all()
        for les in lessons:
            quiz = Quiz.query.filter_by(lesson_id=les.id).first()
            if quiz:
                best_score = quiz_highest_scores.get(quiz.id, 0.0)
                # If they have attempted it
                if quiz.id in quiz_highest_scores:
                    if best_score >= 80.0:
                        strong_topics.append((les.title, int(best_score)))
                    elif best_score < 70.0:
                        weak_topics.append((les.title, int(best_score)))
                else:
                    # Unattempted count as weakness
                    weak_topics.append((les.title, 0))
                    
    # 5. Chart.js datasets compiling
    # Progression Timeline Chart
    attempts_sorted = sorted(attempts, key=lambda x: x.attempted_at)
    quiz_dates_labels = [a.attempted_at.strftime('%m-%d %H:%M') for a in attempts_sorted]
    quiz_scores_data = [a.score for a in attempts_sorted]
    
    # Time Allocation Bar Chart
    progress_records = Progress.query.join(Enrollment).filter(Enrollment.user_id == current_user.id).all()
    lesson_labels = [p.lesson.title[:15] + "..." for p in progress_records if p.lesson]
    lesson_times_data = [p.time_spent or 0 for p in progress_records]
    
    return render_template(
        'student_analytics.html',
        total_minutes=total_minutes,
        total_quizzes=total_quizzes,
        passed_quizzes=passed_quizzes,
        avg_score=avg_score,
        certificates_count=certificates_count,
        acp_readiness=acp_readiness,
        strong_topics=strong_topics[:5],
        weak_topics=weak_topics[:5],
        quiz_dates_labels=quiz_dates_labels,
        quiz_scores_data=quiz_scores_data,
        lesson_labels=lesson_labels,
        lesson_times_data=lesson_times_data
    )


# ──────────────────────────────────────────────────────────────────────────
# Certificate Dynamic Stream Route
# ──────────────────────────────────────────────────────────────────────────
@main_bp.route('/courses/<int:course_id>/certificate')
@login_required
def download_certificate(course_id):
    """Generates and streams the completed certificate PDF."""
    course = Course.query.get_or_404(course_id)
    certificate = Certificate.query.filter_by(
        user_id=current_user.id,
        course_id=course_id
    ).first_or_404()
    
    # Call the PDF ReportLab utility
    pdf_buffer = generate_certificate_pdf(
        student_name=f"{current_user.first_name} {current_user.last_name}",
        course_title=course.title,
        cert_code=certificate.certificate_code,
        issue_date=certificate.issue_date
    )
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"Roadshub_Certificate_{certificate.certificate_code}.pdf"
    )


# ──────────────────────────────────────────────────────────────────────────
# Payment Processing Routes
# ──────────────────────────────────────────────────────────────────────────
@main_bp.route('/checkout/<int:course_id>')
@login_required
def checkout(course_id):
    course = Course.query.get_or_404(course_id)
    return render_template('checkout.html', course=course)


@main_bp.route('/checkout/<int:course_id>/mpesa', methods=['POST'])
@login_required
def checkout_mpesa(course_id):
    course = Course.query.get_or_404(course_id)
    phone_number = request.form.get('phone_number')
    
    if not phone_number:
        flash("Phone number is required for M-Pesa payments.", "danger")
        return redirect(url_for('main.checkout', course_id=course_id))
        
    payment = Payment(
        user_id=current_user.id,
        course_id=course.id,
        amount=course.price,
        currency='KES',
        method='mpesa',
        status='pending'
    )
    db.session.add(payment)
    db.session.commit()
    
    callback_url = url_for('main.mpesa_webhook', _external=True)
    response = initiate_stk_push(
        phone_number=phone_number,
        amount=course.price,
        account_reference=f"RH_COURSE_{course.id}",
        transaction_desc=f"Payment for {course.title}",
        callback_url=callback_url
    )
    
    if "error" in response:
        flash(f"Error initiating M-Pesa payment: {response['error']}", "danger")
        payment.status = 'failed'
        db.session.commit()
    else:
        flash("M-Pesa payment initiated. Please check your phone to complete the transaction.", "info")
        payment.reference = response.get('CheckoutRequestID')
        db.session.commit()
        
    return redirect(url_for('main.student_dashboard'))


@main_bp.route('/checkout/<int:course_id>/stripe', methods=['POST'])
@login_required
def checkout_stripe(course_id):
    course = Course.query.get_or_404(course_id)
    
    payment = Payment(
        user_id=current_user.id,
        course_id=course.id,
        amount=course.price,
        currency='USD',
        method='stripe',
        status='pending'
    )
    db.session.add(payment)
    db.session.commit()
    
    success_url = url_for('main.student_dashboard', _external=True) + "?payment=success"
    cancel_url = url_for('main.checkout', course_id=course.id, _external=True) + "?payment=cancelled"
    
    session = create_checkout_session(course, payment.id, success_url, cancel_url)
    if "error" in session:
        flash(f"Error creating Stripe session: {session['error']}", "danger")
        payment.status = 'failed'
        db.session.commit()
        return redirect(url_for('main.checkout', course_id=course_id))
        
    payment.reference = session.id
    db.session.commit()
    return redirect(session.url, code=303)


@main_bp.route('/webhook/mpesa', methods=['POST'])
def mpesa_webhook():
    data = request.json
    try:
        body = data.get('Body', {}).get('stkCallback', {})
        checkout_request_id = body.get('CheckoutRequestID')
        result_code = body.get('ResultCode')
        
        payment = Payment.query.filter_by(reference=checkout_request_id).first()
        if not payment:
            return "Payment not found", 404
            
        if result_code == 0:
            payment.status = 'confirmed'
            db.session.commit()
            
            # Trigger auto-enrollment
            cohort = Cohort.query.filter_by(course_id=payment.course_id).first()
            if cohort:
                existing = Enrollment.query.filter_by(user_id=payment.user_id, cohort_id=cohort.id).first()
                if not existing:
                    enrollment = Enrollment(user_id=payment.user_id, cohort_id=cohort.id)
                    db.session.add(enrollment)
                    db.session.commit()
        else:
            payment.status = 'failed'
            db.session.commit()
            
        return "OK", 200
    except Exception as e:
        return str(e), 500


@main_bp.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        payment_id = session.get('client_reference_id')
        
        if payment_id:
            payment = Payment.query.get(payment_id)
            if payment:
                payment.status = 'confirmed'
                db.session.commit()
                
                # Trigger auto-enrollment
                cohort = Cohort.query.filter_by(course_id=payment.course_id).first()
                if cohort:
                    existing = Enrollment.query.filter_by(user_id=payment.user_id, cohort_id=cohort.id).first()
                    if not existing:
                        enrollment = Enrollment(user_id=payment.user_id, cohort_id=cohort.id)
                        db.session.add(enrollment)
                        db.session.commit()

    return "OK", 200


# ──────────────────────────────────────────────────────────────────────────
# Lead Capture & Nurture Routes
# ──────────────────────────────────────────────────────────────────────────
@main_bp.route('/lead')
def lead_capture_page():
    return render_template('capture_form.html')

@main_bp.route('/lead/capture', methods=['POST'])
def capture_lead():
    from app.tasks import send_whatsapp_message_task, send_nurture_email_task
    
    name = request.form.get('name')
    email = request.form.get('email')
    phone_number = request.form.get('phone_number')
    area_of_interest = request.form.get('area_of_interest')
    source_tag = request.form.get('source_tag', 'Organic')
    
    lead = Lead(
        name=name,
        email=email,
        phone_number=phone_number,
        area_of_interest=area_of_interest,
        source_tag=source_tag
    )
    db.session.add(lead)
    db.session.commit()
    
    # Schedule WhatsApp message in 5 minutes (300 seconds)
    send_whatsapp_message_task.apply_async(args=[lead.id], countdown=300)
    
    # Schedule Email sequences
    # Day 1: 24 hours (86400 seconds)
    send_nurture_email_task.apply_async(args=[lead.id, 1], countdown=86400)
    # Day 3: 72 hours (259200 seconds)
    send_nurture_email_task.apply_async(args=[lead.id, 3], countdown=259200)
    # Day 7: 168 hours (604800 seconds)
    send_nurture_email_task.apply_async(args=[lead.id, 7], countdown=604800)
    
    flash("Thank you! Your ACP Study Guide has been emailed to you and we'll send a WhatsApp confirmation shortly.", "success")
    return redirect(url_for('main.index'))
@main_bp.route('/pricing')
def pricing():
    from app.tasks import evaluate_lead_intent_task
    
    lead_id = request.args.get('lead_id')
    if lead_id:
        lead = Lead.query.get(lead_id)
        if lead:
            lead.pricing_page_visited = True
            db.session.commit()
            # Evaluate intent asynchronously
            evaluate_lead_intent_task.apply_async(args=[lead.id])
            
    return render_template('index.html')  # Mock pricing page using index for now
@main_bp.route('/api/chat', methods=['POST'])
def chat():
    """
    Roadhub AI Assistant API.
    Provides context-aware responses to user queries about the Roadhub platform.
    """
    data = request.get_json() or {}
    user_msg = data.get('message', '').strip().lower()
    
    if not user_msg:
        return {"response": "I didn't catch that. Could you please type something?"}, 400

    # Contextual matching logic
    if any(k in user_msg for k in ['hvac', 'plumbing', 'fire fighting', 'mechanical']):
        response = (
            "Our <strong>Mechanical Engineering Path</strong> covers HVAC load calculations, pipe sizing, "
            "duct design, and Fire Fighting layouts matching international codes. "
            "Would you like to <a href='/login'>log in</a> to see the specific modules?"
        )
    elif any(k in user_msg for k in ['electrical', 'power', 'light current', 'bms']):
        response = (
            "The <strong>Electrical Engineering Path</strong> covers interior lighting design, power distribution sizing, "
            "earthing systems, light current systems, and Building Management Systems (BMS). "
            "All lessons are created by practicing senior electrical designers."
        )
    elif any(k in user_msg for k in ['civil', 'structure', 'infrastructure', 'concrete']):
        response = (
            "The <strong>Civil & Structural Paths</strong> focus on concrete element designs, reinforcement layout checks, "
            "site supervision procedures, and infrastructural design. You get to work on real shop drawings."
        )
    elif any(k in user_msg for k in ['architect', 'landscape', 'interior', 'design']):
        response = (
            "Our <strong>Architecture & Interior Design Paths</strong> guide you through space planning, zoning, "
            "material selections, drafting construction details, and architectural rendering principles."
        )
    elif any(k in user_msg for k in ['pricing', 'cost', 'fee', 'payment', 'free', 'price']):
        response = (
            "Roadhub offers a mix of free introductory courses and premium cohort-based paths. "
            "You can view the full pricing breakdown and pay securely via Stripe or MPESA "
            "upon logging into your student account."
        )
    elif any(k in user_msg for k in ['certif', 'acp', 'autodesk', 'credential', 'exam']):
        response = (
            "Yes! Completing Roadhub courses prepares you for the <strong>Autodesk Certified Professional (ACP)</strong> exams. "
            "Once you complete all cohort milestones, a verified digital completion certificate is awarded automatically."
        )
    elif any(k in user_msg for k in ['mentor', 'teacher', 'instructor', 'who teach']):
        response = (
            "All our instructors are practicing professional engineers and project leads with global market experience. "
            "They review your submissions and host weekly live design sessions."
        )
    elif any(k in user_msg for k in ['study guide', 'download', 'pdf', 'nurture', 'guide']):
        response = (
            "You can download our free <strong>Engineering Study Guide</strong> by clicking the 'Get Study Guide' button "
            "in the banner at the bottom of the home page, or register via the lead form to get it emailed to you."
        )
    elif any(k in user_msg for k in ['hello', 'hi', 'hey', 'greetings', 'start']):
        response = (
            "Hello! Welcome to Roadhub. I'm your engineering study assistant. "
            "Ask me anything about our HVAC, Electrical, Civil, or Architecture courses, certifications, or pricing!"
        )
    else:
        response = (
            "I'm here to help you navigate Roadhub! I can provide info about our "
            "practical courses (HVAC, Electrical, Civil, Architecture), Autodesk certification preparation, "
            "pricing details, and professional mentorship. What would you like to know?"
        )

    return {"response": response}

@main_bp.route('/articles')
def articles():
    return render_template('articles.html')

@main_bp.route('/community')
def community():
    return render_template('community.html')


from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Student, Subject, StudentSubject, MonthlyTest, ExamMark, FeeAccount, Payment, FeeSetting, Timetable, ExamTimetable, PrincipalComment, TeacherRemark, ActivityLog, Activity, StaffLeave, LevyFund, zim_grade
from config import Config
from functools import wraps
from datetime import datetime, date, timedelta
import os
import random
import string

app = Flask(__name__)
app.config.from_object(Config)
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True

db.init_app(app)
with app.app_context():
    db.create_all()
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    existing_columns = [col['name'] for col in inspector.get_columns('students')]
    if 'curriculum' not in existing_columns:
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE students ADD COLUMN curriculum VARCHAR(20)'))
            conn.commit()



login_manager = LoginManager(app)
login_manager.login_view = 'auth_login'
login_manager.login_message_category = 'info'


@app.context_processor
def inject_now():
    return {'now': datetime.now}


def generate_student_id():
    year = datetime.now().year
    while True:
        num = random.randint(1000, 9999)
        sid = f'{year}{num}'
        if not Student.query.filter_by(student_id=sid).first():
            return sid


def log_activity(action, description=None, user=None, student=None, visibility='public'):
    entry = ActivityLog(action=action, description=description, visibility=visibility,
                        user_id=user.id if user else None,
                        student_id=student.id if student else None)
    db.session.add(entry)
    db.session.commit()


def generate_receipt():
    while True:
        ref = 'RCP' + ''.join(random.choices(string.digits, k=8))
        if not Payment.query.filter_by(receipt_number=ref).first():
            return ref


@login_manager.user_loader
def load_user(user_id):
    if user_id.startswith('student_'):
        return Student.query.get(int(user_id.replace('student_', '')))
    return User.query.get(int(user_id))


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth_login'))
            if isinstance(current_user, Student):
                flash('Access denied. Staff only.', 'danger')
                return redirect(url_for('student_dashboard'))
            if current_user.role not in roles:
                flash('Access denied.', 'danger')
                return redirect(url_for('staff_dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth_login'))
        if not isinstance(current_user, Student):
            flash('Access denied. Students only.', 'danger')
            return redirect(url_for('staff_dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ============ AUTH ROUTES ============

@app.route('/')
def index():
    if current_user.is_authenticated:
        if isinstance(current_user, Student):
            return redirect(url_for('student_dashboard'))
        return redirect(url_for('staff_dashboard'))
    return redirect(url_for('auth_login'))


@app.route('/auth/login', methods=['GET', 'POST'])
def auth_login():
    if current_user.is_authenticated:
        if isinstance(current_user, Student):
            return redirect(url_for('student_dashboard'))
        return redirect(url_for('staff_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        student = Student.query.filter_by(student_id=username).first()
        if student and student.check_password(password):
            if not student.is_active:
                flash('Account deactivated. Contact admin.', 'danger')
                return render_template('auth/login.html')
            login_user(student)
            flash(f'Welcome {student.full_name}!', 'success')
            return redirect(url_for('student_dashboard'))

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash('Account deactivated. Contact principal.', 'danger')
                return render_template('auth/login.html')
            login_user(user)
            flash(f'Welcome {user.full_name}!', 'success')
            return redirect(url_for('staff_dashboard'))

        flash('Invalid username or password', 'danger')

    return render_template('auth/login.html')


@app.route('/auth/logout')
@login_required
def auth_logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth_login'))


@app.route('/auth/change-password', methods=['GET', 'POST'])
@login_required
def auth_change_password():
    if request.method == 'POST':
        current_pw = request.form.get('current_password', '')
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')

        if not current_user.check_password(current_pw):
            flash('Current password is incorrect.', 'danger')
            return render_template('auth/change_password.html')

        if len(new_pw) < 6:
            flash('New password must be at least 6 characters.', 'danger')
            return render_template('auth/change_password.html')

        if new_pw != confirm_pw:
            flash('New passwords do not match.', 'danger')
            return render_template('auth/change_password.html')

        current_user.set_password(new_pw)
        db.session.commit()
        flash('Password changed successfully! Please log in with your new password.', 'success')
        return redirect(url_for('auth_logout'))

    return render_template('auth/change_password.html')


def normalize_phone(p):
    return ''.join(c for c in p if c.isdigit() or c == '+')

def find_person_by_reg_and_phone(reg_raw, phone_raw):
    phone_normalized = normalize_phone(phone_raw)
    reg_clean = reg_raw.replace('-', '').replace('REG', '').replace('reg', '')
    reg_variants = list(set([
        reg_raw,
        reg_raw.replace('-', ''),
        f'REG-{reg_clean}',
        f'REG{reg_clean}',
        reg_raw.upper(),
    ]))

    from itertools import chain
    candidates = list(chain.from_iterable(
        User.query.filter(User.reg_number == r).all() for r in reg_variants
    )) + list(chain.from_iterable(
        Student.query.filter(Student.reg_number == r).all() for r in reg_variants
    )) + list(chain.from_iterable(
        Student.query.filter(Student.student_id == r).all() for r in reg_variants
    )) + list(chain.from_iterable(
        User.query.filter(User.username == r).all() for r in reg_variants
    ))

    seen = set()
    for p in candidates:
        if p.id in seen:
            continue
        seen.add(p.id)
        if normalize_phone(p.phone or '') == phone_normalized:
            return p
    return None

@app.route('/auth/reset-password', methods=['GET', 'POST'])
def auth_reset_password():
    if request.method == 'POST':
        reg_number = request.form.get('reg_number', '').strip()
        phone = request.form.get('phone', '').strip()

        person = find_person_by_reg_and_phone(reg_number, phone)
        if not person:
            flash('Registration number/Student ID and phone number do not match our records.', 'danger')
            return render_template('auth/reset_password.html', debug_reg=reg_number, debug_phone=phone)

        reset_code = str(random.randint(100000, 999999))
        session['reset_phone'] = phone
        session['reset_code'] = reset_code
        session['reset_expiry'] = (datetime.now() + timedelta(hours=1)).timestamp()
        session['reset_user_type'] = 'User' if isinstance(person, User) else 'Student'
        session['reset_user_id'] = person.id

        flash(f'Your 6-digit verification code is: {reset_code}', 'info')
        return redirect(url_for('auth_reset_code'))

    return render_template('auth/reset_password.html')


@app.route('/auth/reset-code', methods=['GET', 'POST'])
def auth_reset_code():
    phone = session.get('reset_phone')
    expected_code = session.get('reset_code')
    expiry = session.get('reset_expiry')

    if not all([session.get(k) for k in ('reset_phone', 'reset_code', 'reset_expiry', 'reset_user_type', 'reset_user_id')]):
        flash('No reset session found. Please request a password reset first.', 'warning')
        return redirect(url_for('auth_reset_password'))

    if datetime.now().timestamp() > expiry:
        session.pop('reset_phone', None)
        session.pop('reset_code', None)
        session.pop('reset_expiry', None)
        session.pop('reset_user_type', None)
        session.pop('reset_user_id', None)
        flash('Reset code has expired. Please request a new one.', 'danger')
        return redirect(url_for('auth_reset_password'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()

        if code != expected_code:
            flash('Invalid verification code.', 'danger')
            return render_template('auth/reset_code.html', code=expected_code)

        session['reset_code_verified'] = True
        return redirect(url_for('auth_reset_set_password'))

    return render_template('auth/reset_code.html', code=expected_code)


@app.route('/auth/reset-set-password', methods=['GET', 'POST'])
def auth_reset_set_password():
    if not session.get('reset_code_verified'):
        flash('Please verify your code first.', 'warning')
        return redirect(url_for('auth_reset_code'))

    if datetime.now().timestamp() > session.get('reset_expiry', 0):
        for k in ('reset_phone', 'reset_code', 'reset_expiry', 'reset_user_type', 'reset_user_id', 'reset_code_verified'):
            session.pop(k, None)
        flash('Reset session has expired. Please start over.', 'danger')
        return redirect(url_for('auth_reset_password'))

    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')

        if len(new_password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('auth/reset_set_password.html')

        if new_password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/reset_set_password.html')

        user_type = session.get('reset_user_type')
        user_id = session.get('reset_user_id')
        if user_type == 'User':
            user = User.query.get(user_id)
            if user:
                user.set_password(new_password)
        elif user_type == 'Student':
            student = Student.query.get(user_id)
            if student:
                student.set_password(new_password)
        db.session.commit()

        for k in ('reset_phone', 'reset_code', 'reset_expiry', 'reset_user_type', 'reset_user_id', 'reset_code_verified'):
            session.pop(k, None)

        flash('Password reset successfully! You can now log in.', 'success')
        return redirect(url_for('auth_login'))

    return render_template('auth/reset_set_password.html')


# ============ STAFF DASHBOARD ============

@app.route('/staff/dashboard')
@login_required
def staff_dashboard():
    if isinstance(current_user, Student):
        return redirect(url_for('student_dashboard'))

    stats = {}
    if current_user.role == 'teacher':
        subj = current_user.teacher_subject
        stats['subject_name'] = subj.name if subj else 'Not assigned'
        stats['student_count'] = StudentSubject.query.filter_by(subject_id=current_user.subject_id).count() if current_user.subject_id else 0
        stats['activities_count'] = Activity.query.count()
        stats['recent_activity_posts'] = Activity.query.order_by(Activity.created_at.desc()).limit(10).all()
    elif current_user.role == 'cashier':
        stats['pending_clearance'] = Payment.query.filter_by(cleared=False).count()
        stats['total_payments_today'] = Payment.query.filter(db.func.date(Payment.created_at) == date.today()).count()
        stats['recent_activity_posts'] = Activity.query.order_by(Activity.created_at.desc()).limit(10).all()
    elif current_user.role == 'admin':
        stats['total_students'] = Student.query.count()
        stats['active_students'] = Student.query.filter_by(is_active=True).count()
        stats['staff_count'] = User.query.filter(User.role != 'principal').count()
        term = 'Term 1'
        stats['term'] = term
        stats['total_expected'] = db.session.query(db.func.sum(FeeAccount.total_fees)).filter_by(term=term).scalar() or 0
        stats['total_collected'] = db.session.query(db.func.sum(Payment.amount)).filter(Payment.cleared == True).scalar() or 0
        fee_accounts = FeeAccount.query.filter_by(term=term).all()
        stats['outstanding'] = sum(fa.balance for fa in fee_accounts if fa.balance > 0)
        stats['outstanding_list'] = FeeAccount.query.filter(FeeAccount.term == term, FeeAccount.balance > 0).order_by(FeeAccount.balance.desc()).all()
        now_date = date.today()
        stats['upcoming_exams'] = ExamTimetable.query.filter(ExamTimetable.exam_date >= now_date).order_by(ExamTimetable.exam_date).limit(5).all()
        stats['recent_activities'] = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()
        stats['recent_activity_posts'] = Activity.query.order_by(Activity.created_at.desc()).limit(10).all()
        stats['staff_on_leave'] = StaffLeave.query.filter(StaffLeave.status == 'Approved',
                                                           StaffLeave.end_date >= now_date).count()
        subjects = Subject.query.all()
        pass_rates = []
        for subj in subjects:
            exams = ExamMark.query.filter_by(subject_id=subj.id, term=term).all()
            if exams:
                passed = sum(1 for e in exams if e.marks / e.total_marks * 100 >= 50)
                pass_rates.append({'subject': subj.name, 'rate': round(passed / len(exams) * 100, 1), 'total': len(exams)})
        stats['pass_rates'] = pass_rates
        form_pass_rates = []
        forms = ['Form 1', 'Form 2', 'Form 3', 'Form 4', 'Form 5', 'Form 6']
        for f in forms:
            sids = [s.id for s in Student.query.filter_by(form=f).all()]
            if sids:
                exams = ExamMark.query.filter(ExamMark.student_id.in_(sids), ExamMark.term == term).all()
                if exams:
                    passed = sum(1 for e in exams if e.marks / e.total_marks * 100 >= 50)
                    form_pass_rates.append({'form': f, 'rate': round(passed / len(exams) * 100, 1), 'total': len(exams)})
        stats['form_pass_rates'] = form_pass_rates
        stats['levies'] = LevyFund.query.filter_by(term=term).all()
        staff_leaves = StaffLeave.query.filter(StaffLeave.status == 'Approved',
                                                StaffLeave.end_date >= now_date).count()
        stats['active_staff_count'] = stats['staff_count'] - staff_leaves
        stats['staff_on_leave_count'] = staff_leaves
    elif current_user.role == 'principal':
        term = 'Term 1'
        stats['term'] = term
        stats['total_expected'] = db.session.query(db.func.sum(FeeAccount.total_fees)).filter_by(term=term).scalar() or 0
        stats['total_collected'] = db.session.query(db.func.sum(Payment.amount)).filter(Payment.cleared == True).scalar() or 0
        fee_accounts = FeeAccount.query.filter_by(term=term).all()
        stats['outstanding'] = sum(fa.balance for fa in fee_accounts if fa.balance > 0)
        stats['outstanding_list'] = FeeAccount.query.filter(FeeAccount.term == term, FeeAccount.balance > 0).order_by(FeeAccount.balance.desc()).all()
        active_staff = User.query.filter(User.role != 'principal', User.is_active == True).count()
        staff_on_leave_count = StaffLeave.query.filter(StaffLeave.status == 'Approved',
                                                        StaffLeave.end_date >= date.today()).count()
        stats['active_staff_count'] = active_staff
        stats['staff_on_leave_count'] = staff_on_leave_count
        now_date = date.today()
        stats['upcoming_exams'] = ExamTimetable.query.filter(ExamTimetable.exam_date >= now_date).order_by(ExamTimetable.exam_date).limit(5).all()
        stats['recent_activities'] = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()
        stats['recent_activity_posts'] = Activity.query.order_by(Activity.created_at.desc()).limit(10).all()
        subjects = Subject.query.all()
        pass_rates = []
        for subj in subjects:
            exams = ExamMark.query.filter_by(subject_id=subj.id, term=term).all()
            if exams:
                passed = sum(1 for e in exams if e.marks / e.total_marks * 100 >= 50)
                pass_rates.append({'subject': subj.name, 'rate': round(passed / len(exams) * 100, 1), 'total': len(exams)})
        stats['pass_rates'] = pass_rates
        form_pass_rates = []
        forms = ['Form 1', 'Form 2', 'Form 3', 'Form 4', 'Form 5', 'Form 6']
        for f in forms:
            sids = [s.id for s in Student.query.filter_by(form=f).all()]
            if sids:
                exams = ExamMark.query.filter(ExamMark.student_id.in_(sids), ExamMark.term == term).all()
                if exams:
                    passed = sum(1 for e in exams if e.marks / e.total_marks * 100 >= 50)
                    form_pass_rates.append({'form': f, 'rate': round(passed / len(exams) * 100, 1), 'total': len(exams)})
        stats['form_pass_rates'] = form_pass_rates
        stats['levies'] = LevyFund.query.filter_by(term=term).all()

    return render_template('staff/dashboard.html', stats=stats)


@app.route('/staff/activities')
@login_required
def staff_activities():
    activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).all()
    return render_template('staff/activities.html', activities=activities)


# ============ TEACHER ROUTES ============

@app.route('/staff/teacher/class')
@login_required
@role_required('teacher')
def teacher_class():
    if not current_user.subject_id:
        flash('No subject assigned.', 'warning')
        return redirect(url_for('staff_dashboard'))

    subject = Subject.query.get(current_user.subject_id)
    student_subjects = StudentSubject.query.filter_by(subject_id=current_user.subject_id).all()
    students = [ss.student for ss in student_subjects if ss.student.is_active]
    recent_activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(5).all()

    return render_template('staff/teacher/class.html', subject=subject, students=students, recent_activities=recent_activities)


@app.route('/staff/teacher/student/<int:student_id>/results')
@login_required
@role_required('teacher')
def teacher_student_results(student_id):
    student = Student.query.get_or_404(student_id)
    monthly_tests = MonthlyTest.query.filter_by(student_id=student.id, subject_id=current_user.subject_id).order_by(MonthlyTest.academic_year.desc(), MonthlyTest.term).all()
    exam_marks = ExamMark.query.filter_by(student_id=student.id, subject_id=current_user.subject_id).order_by(ExamMark.academic_year.desc(), ExamMark.term).all()
    subject = Subject.query.get(current_user.subject_id)
    return render_template('staff/teacher/student_results.html', student=student, monthly_tests=monthly_tests, exam_marks=exam_marks, subject=subject)


@app.route('/staff/teacher/marks')
@login_required
@role_required('teacher')
def teacher_marks():
    if not current_user.subject_id:
        flash('No subject assigned.', 'warning')
        return redirect(url_for('staff_dashboard'))

    subject = Subject.query.get(current_user.subject_id)
    student_subjects = StudentSubject.query.filter_by(subject_id=current_user.subject_id).all()
    students = [ss.student for ss in student_subjects if ss.student.is_active]
    monthly_tests = MonthlyTest.query.filter_by(subject_id=current_user.subject_id).all()
    exam_marks_list = ExamMark.query.filter_by(subject_id=current_user.subject_id).all()

    marks_data = {}
    for s in students:
        s_monthly = [mt for mt in monthly_tests if mt.student_id == s.id]
        s_exam = [em for em in exam_marks_list if em.student_id == s.id]
        marks_data[s.id] = {'monthly': s_monthly, 'exam': s_exam}

    return render_template('staff/teacher/marks.html', subject=subject, students=students, marks_data=marks_data)


@app.route('/staff/teacher/marks/add', methods=['POST'])
@login_required
@role_required('teacher')
def teacher_add_mark():
    student_id = request.form.get('student_id')
    mark_type = request.form.get('mark_type')
    term = request.form.get('term')
    month = request.form.get('month')
    exam_type = request.form.get('exam_type')
    marks = float(request.form.get('marks'))
    total_marks = float(request.form.get('total_marks', 100))
    academic_year = request.form.get('academic_year', str(datetime.now().year))
    comment = request.form.get('comment')

    student = Student.query.get(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('teacher_marks'))

    if mark_type == 'monthly':
        test = MonthlyTest(
            student_id=student.id, subject_id=current_user.subject_id,
            term=term, academic_year=academic_year, month=month,
            marks=marks, total_marks=total_marks, teacher_id=current_user.id,
            comment=comment or None
        )
        db.session.add(test)
    elif mark_type == 'exam':
        exam = ExamMark(
            student_id=student.id, subject_id=current_user.subject_id,
            term=term, academic_year=academic_year, exam_type=exam_type,
            marks=marks, total_marks=total_marks, teacher_id=current_user.id,
            comment=comment or None
        )
        db.session.add(exam)

    db.session.commit()
    log_activity('Marks entered', f'{mark_type} - {student.full_name}: {marks}/{total_marks}', user=current_user, student=student)
    flash(f'Marks added! Grade: {zim_grade(marks, total_marks, "A" if "6" in student.form or "5" in student.form else "O")}', 'success')
    return redirect(url_for('teacher_marks'))


@app.route('/staff/teacher/marks/edit/<int:mark_id>', methods=['POST'])
@login_required
@role_required('teacher')
def teacher_edit_mark(mark_id):
    mark_type = request.form.get('mark_type')
    marks = float(request.form.get('marks'))
    total_marks = float(request.form.get('total_marks', 100))
    comment = request.form.get('comment')

    if mark_type == 'monthly':
        mark = MonthlyTest.query.get_or_404(mark_id)
        if mark.subject_id != current_user.subject_id:
            flash('Access denied.', 'danger')
            return redirect(url_for('teacher_marks'))
        mark.marks = marks
        mark.total_marks = total_marks
        mark.comment = comment or None
    elif mark_type == 'exam':
        mark = ExamMark.query.get_or_404(mark_id)
        if mark.subject_id != current_user.subject_id:
            flash('Access denied.', 'danger')
            return redirect(url_for('teacher_marks'))
        mark.marks = marks
        mark.total_marks = total_marks
        mark.comment = comment or None

    db.session.commit()
    flash('Marks updated!', 'success')
    return redirect(url_for('teacher_marks'))


@app.route('/staff/teacher/marks/delete/<int:mark_id>/<mark_type>')
@login_required
@role_required('teacher')
def teacher_delete_mark(mark_id, mark_type):
    if mark_type == 'monthly':
        mark = MonthlyTest.query.get_or_404(mark_id)
        if mark.teacher_id != current_user.id:
            flash('Access denied.', 'danger')
            return redirect(url_for('teacher_marks'))
        db.session.delete(mark)
    elif mark_type == 'exam':
        mark = ExamMark.query.get_or_404(mark_id)
        if mark.teacher_id != current_user.id:
            flash('Access denied.', 'danger')
            return redirect(url_for('teacher_marks'))
        db.session.delete(mark)

    db.session.commit()
    flash('Mark deleted.', 'success')
    return redirect(url_for('teacher_marks'))


@app.route('/staff/teacher/remark/save', methods=['POST'])
@login_required
@role_required('teacher')
def teacher_save_remark():
    student_id = request.form.get('student_id')
    remark = request.form.get('remark')
    student = Student.query.get(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('teacher_class'))

    tr = TeacherRemark(student_id=student.id, teacher_id=current_user.id, remark=remark)
    db.session.add(tr)
    db.session.commit()
    flash(f'Remark added for {student.full_name}.', 'success')
    return redirect(url_for('teacher_class'))


# ============ CASHIER ROUTES ============

@app.route('/staff/cashier')
@login_required
@role_required('cashier')
def cashier_dashboard():
    recent_payments = Payment.query.order_by(Payment.created_at.desc()).limit(20).all()
    pending = Payment.query.filter_by(cleared=False).count()
    all_students = Student.query.order_by(Student.student_id).all()
    return render_template('staff/cashier/dashboard.html', payments=recent_payments, pending=pending, all_students=all_students)


@app.route('/staff/cashier/student/fees', methods=['GET', 'POST'])
@login_required
@role_required('cashier')
def cashier_student_fees():
    student = None
    fee_account = None
    payments = []

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        student = Student.query.filter_by(student_id=student_id).first()
        if not student:
            flash('Student not found.', 'danger')
        else:
            fee_account = FeeAccount.query.filter_by(student_id=student.id).first()
            payments = Payment.query.filter_by(student_id=student.id).order_by(Payment.created_at.desc()).all()

    return render_template('staff/cashier/student_fees.html', student=student, fee_account=fee_account, payments=payments)


@app.route('/staff/cashier/payment/add', methods=['POST'])
@login_required
@role_required('cashier')
def cashier_add_payment():
    student_id = request.form.get('student_id')
    amount = float(request.form.get('amount'))
    payment_method = request.form.get('payment_method')
    reference = request.form.get('reference')

    student = Student.query.get(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('cashier_dashboard'))

    payment = Payment(
        student_id=student.id, receipt_number=generate_receipt(),
        amount=amount, payment_date=datetime.now(),
        payment_method=payment_method, reference=reference,
        cashier_id=current_user.id, cleared=False
    )
    db.session.add(payment)

    fee_account = FeeAccount.query.filter_by(student_id=student.id).first()
    if fee_account:
        fee_account.amount_paid += amount
        fee_account.balance = fee_account.total_fees - fee_account.amount_paid

    db.session.commit()
    log_activity('Payment recorded', f'${amount:.2f} for {student.full_name} ({student.reg_number})', user=current_user, student=student)
    flash(f'Payment recorded. Receipt: {payment.receipt_number}', 'success')
    return redirect(url_for('cashier_student_fees'))


@app.route('/staff/cashier/payment/clear/<int:payment_id>')
@login_required
@role_required('cashier')
def cashier_clear_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    payment.cleared = True
    payment.cleared_at = datetime.now()
    db.session.commit()
    flash(f'Payment {payment.receipt_number} cleared.', 'success')
    return redirect(request.referrer or url_for('cashier_dashboard'))


@app.route('/staff/cashier/setup-fees', methods=['POST'])
@login_required
@role_required('cashier')
def cashier_setup_fees():
    student_id = request.form.get('student_id')
    term = request.form.get('term')
    total_fees = float(request.form.get('total_fees'))

    student = Student.query.get(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('cashier_dashboard'))

    existing = FeeAccount.query.filter_by(student_id=student.id, term=term).first()
    if existing:
        existing.total_fees = total_fees
        existing.balance = total_fees - existing.amount_paid
    else:
        fee_account = FeeAccount(
            student_id=student.id, term=term,
            total_fees=total_fees, amount_paid=0.0, balance=total_fees
        )
        db.session.add(fee_account)

    db.session.commit()
    flash('Fee account updated.', 'success')
    return redirect(url_for('cashier_student_fees'))


# ============ ADMIN ROUTES ============

@app.route('/staff/admin')
@login_required
@role_required('admin')
def admin_dashboard():
    students = Student.query.order_by(Student.created_at.desc()).all()
    active_students = [s for s in students if s.is_active]
    inactive_students = [s for s in students if not s.is_active]

    term = 'Term 1'
    total_expected = db.session.query(db.func.sum(FeeAccount.total_fees)).filter_by(term=term).scalar() or 0
    total_collected = db.session.query(db.func.sum(Payment.amount)).filter(Payment.cleared == True).scalar() or 0
    fee_accounts = FeeAccount.query.filter_by(term=term).all()
    outstanding = sum(fa.balance for fa in fee_accounts if fa.balance > 0)
    outstanding_list = [fa for fa in fee_accounts if fa.balance > 0]

    staff_count = User.query.filter(User.role != 'principal').count()

    now_date = date.today()
    upcoming_exams = ExamTimetable.query.filter(ExamTimetable.exam_date >= now_date).order_by(ExamTimetable.exam_date).limit(5).all()

    recent_activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()
    recent_activity_posts = Activity.query.order_by(Activity.created_at.desc()).limit(10).all()

    staff_leaves = StaffLeave.query.filter(StaffLeave.status == 'Approved', StaffLeave.end_date >= now_date).count()

    subjects = Subject.query.all()
    pass_rates = []
    for subj in subjects:
        exams = ExamMark.query.filter_by(subject_id=subj.id, term=term).all()
        if exams:
            passed = sum(1 for e in exams if e.marks / e.total_marks * 100 >= 50)
            pass_rates.append({'subject': subj.name, 'rate': round(passed / len(exams) * 100, 1), 'total': len(exams)})

    form_pass_rates = []
    forms = ['Form 1', 'Form 2', 'Form 3', 'Form 4', 'Form 5', 'Form 6']
    for f in forms:
        student_ids = [s.id for s in Student.query.filter_by(form=f).all()]
        if student_ids:
            exams = ExamMark.query.filter(ExamMark.student_id.in_(student_ids), ExamMark.term == term).all()
            if exams:
                passed = sum(1 for e in exams if e.marks / e.total_marks * 100 >= 50)
                form_pass_rates.append({'form': f, 'rate': round(passed / len(exams) * 100, 1), 'total': len(exams)})

    levies = LevyFund.query.filter_by(term=term).all()

    return render_template('staff/admin/dashboard.html', students=students, active_students=active_students,
                           inactive_students=inactive_students, total_expected=total_expected,
                           total_collected=total_collected, outstanding=outstanding,
                           outstanding_list=outstanding_list, staff_count=staff_count,
                           upcoming_exams=upcoming_exams, recent_activities=recent_activities,
                           recent_activity_posts=recent_activity_posts,
                           staff_leaves=staff_leaves, pass_rates=pass_rates,
                           form_pass_rates=form_pass_rates, term=term, levies=levies)


@app.route('/staff/admin/student/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_add_student():
    subjects = Subject.query.all()
    o_level = [s for s in subjects if s.level == 'O']
    a_level = [s for s in subjects if s.level == 'A']
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        form = request.form.get('form')
        curriculum = request.form.get('curriculum')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        subject_ids = request.form.getlist('subjects')

        student_id = generate_student_id()
        reg_number = f'REG{student_id}'

        student = Student(
            student_id=student_id, first_name=first_name, last_name=last_name,
            form=form, curriculum=curriculum, email=email or None, phone=phone, reg_number=reg_number
        )
        student.set_password(password or 'student123')

        db.session.add(student)
        db.session.flush()

        for sid in subject_ids:
            ss = StudentSubject(student_id=student.id, subject_id=int(sid))
            db.session.add(ss)

        db.session.commit()
        log_activity('New student registered', f'{first_name} {last_name} ({reg_number})', user=current_user)
        flash(f'Student {first_name} {last_name} added. ID: {student_id}, Reg: {reg_number}', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('staff/admin/add_student.html', subjects=subjects, o_level=o_level, a_level=a_level)


@app.route('/staff/admin/student/edit/<int:student_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    subjects = Subject.query.all()
    enrolled_ids = [ss.subject_id for ss in student.subjects]
    o_level = [s for s in subjects if s.level == 'O']
    a_level = [s for s in subjects if s.level == 'A']

    if request.method == 'POST':
        student.first_name = request.form.get('first_name')
        student.last_name = request.form.get('last_name')
        student.form = request.form.get('form')
        student.curriculum = request.form.get('curriculum')
        student.email = request.form.get('email') or None
        student.phone = request.form.get('phone')
        if request.form.get('password'):
            student.set_password(request.form.get('password'))

        StudentSubject.query.filter_by(student_id=student.id).delete()
        for sid in request.form.getlist('subjects'):
            ss = StudentSubject(student_id=student.id, subject_id=int(sid))
            db.session.add(ss)

        db.session.commit()
        flash('Student updated.', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('staff/admin/edit_student.html', student=student, subjects=subjects, enrolled_ids=enrolled_ids, o_level=o_level, a_level=a_level)


@app.route('/staff/admin/student/deactivate/<int:student_id>')
@login_required
@role_required('admin')
def admin_deactivate_student(student_id):
    student = Student.query.get_or_404(student_id)
    student.is_active = not student.is_active
    status = 'reactivated' if student.is_active else 'deactivated (transferred)'
    db.session.commit()
    flash(f'Student {student.full_name} {status}.', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/staff/admin/student/<int:student_id>/remove-subjects', methods=['POST'])
@login_required
@role_required('admin')
def admin_remove_student_subjects(student_id):
    student = Student.query.get_or_404(student_id)
    count = StudentSubject.query.filter_by(student_id=student.id).count()
    StudentSubject.query.filter_by(student_id=student.id).delete()
    db.session.commit()
    log_activity('Student removed from all subjects', f'{student.full_name} ({count} subjects)', user=current_user)
    flash(f'Removed {student.full_name} from all {count} subject(s).', 'success')
    return redirect(url_for('admin_edit_student', student_id=student.id))


@app.route('/staff/admin/activity/add', methods=['POST'])
@login_required
@role_required('admin')
def admin_add_activity():
    action = request.form.get('action')
    description = request.form.get('description')
    visibility = request.form.get('visibility', 'public')
    if action:
        log_activity(action, description, user=current_user, visibility=visibility)
        flash('Activity logged.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/staff/admin/activities')
@login_required
@role_required('admin')
def admin_activities():
    activities_list = Activity.query.order_by(Activity.created_at.desc()).all()
    return render_template('staff/admin/activities.html', activities_list=activities_list)


@app.route('/staff/admin/activities/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_add_new_activity():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        visibility = request.form.get('visibility', 'all')
        if title:
            activity = Activity(title=title, description=description,
                                visibility=visibility, created_by=current_user.id)
            db.session.add(activity)
            db.session.commit()
            flash('Activity created.', 'success')
            return redirect(url_for('admin_activities'))
        flash('Title is required.', 'danger')
    return render_template('staff/admin/add_activity.html')


@app.route('/staff/admin/activities/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_edit_activity(id):
    activity = Activity.query.get_or_404(id)
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        visibility = request.form.get('visibility', 'all')
        if title:
            activity.title = title
            activity.description = description
            activity.visibility = visibility
            db.session.commit()
            flash('Activity updated.', 'success')
            return redirect(url_for('admin_activities'))
        flash('Title is required.', 'danger')
    return render_template('staff/admin/edit_activity.html', activity=activity)


@app.route('/staff/admin/activities/delete/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_activity(id):
    activity = Activity.query.get_or_404(id)
    db.session.delete(activity)
    db.session.commit()
    flash('Activity deleted.', 'success')
    return redirect(url_for('admin_activities'))


# ============ PRINCIPAL ROUTES ============

@app.route('/staff/principal')
@login_required
@role_required('principal')
def principal_dashboard():
    staff = User.query.all()
    students = Student.query.order_by(Student.student_id).all()
    student_fees = {}
    for s in students:
        fee = FeeAccount.query.filter_by(student_id=s.id).first()
        payments = Payment.query.filter_by(student_id=s.id).order_by(Payment.created_at.desc()).all()
        total_paid = sum(p.amount for p in payments)
        student_fees[s.id] = {'fee': fee, 'payments': payments, 'total_paid': total_paid}

    term = 'Term 1'
    total_expected = db.session.query(db.func.sum(FeeAccount.total_fees)).filter_by(term=term).scalar() or 0
    total_collected = db.session.query(db.func.sum(Payment.amount)).filter(Payment.cleared == True).scalar() or 0
    fee_accounts = FeeAccount.query.filter_by(term=term).all()
    outstanding = sum(fa.balance for fa in fee_accounts if fa.balance > 0)
    outstanding_list = [fa for fa in fee_accounts if fa.balance > 0]

    active_staff_count = User.query.filter(User.role != 'principal', User.is_active == True).count()
    staff_on_leave = StaffLeave.query.filter(StaffLeave.status == 'Approved',
                                              StaffLeave.end_date >= date.today()).count()

    now_date = date.today()
    upcoming_exams = ExamTimetable.query.filter(ExamTimetable.exam_date >= now_date).order_by(ExamTimetable.exam_date).limit(5).all()

    recent_activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()
    recent_activity_posts = Activity.query.order_by(Activity.created_at.desc()).limit(10).all()

    subjects = Subject.query.all()
    pass_rates = []
    for subj in subjects:
        exams = ExamMark.query.filter_by(subject_id=subj.id, term=term).all()
        if exams:
            passed = sum(1 for e in exams if e.marks / e.total_marks * 100 >= 50)
            pass_rates.append({'subject': subj.name, 'rate': round(passed / len(exams) * 100, 1), 'total': len(exams)})

    form_pass_rates = []
    forms = ['Form 1', 'Form 2', 'Form 3', 'Form 4', 'Form 5', 'Form 6']
    for f in forms:
        sids = [s.id for s in Student.query.filter_by(form=f).all()]
        if sids:
            exams = ExamMark.query.filter(ExamMark.student_id.in_(sids), ExamMark.term == term).all()
            if exams:
                passed = sum(1 for e in exams if e.marks / e.total_marks * 100 >= 50)
                form_pass_rates.append({'form': f, 'rate': round(passed / len(exams) * 100, 1), 'total': len(exams)})

    levies = LevyFund.query.filter_by(term=term).all()
    zimsec_students = Student.query.filter_by(curriculum='ZIMSEC', is_active=True).count()

    return render_template('staff/principal/dashboard.html', staff=staff, students=students,
                           student_fees=student_fees, total_expected=total_expected,
                           total_collected=total_collected, outstanding=outstanding,
                           outstanding_list=outstanding_list, active_staff_count=active_staff_count,
                           staff_on_leave=staff_on_leave, upcoming_exams=upcoming_exams,
                           recent_activities=recent_activities, recent_activity_posts=recent_activity_posts,
                           pass_rates=pass_rates, form_pass_rates=form_pass_rates, term=term, levies=levies,
                           zimsec_students=zimsec_students)


@app.route('/staff/principal/student/<int:student_id>/results')
@login_required
@role_required('principal')
def principal_student_results(student_id):
    student = Student.query.get_or_404(student_id)
    subjects = [ss.subject for ss in student.subjects if ss.subject]
    monthly_tests = MonthlyTest.query.filter_by(student_id=student.id).order_by(MonthlyTest.academic_year.desc(), MonthlyTest.term).all()
    exam_marks_list = ExamMark.query.filter_by(student_id=student.id).order_by(ExamMark.academic_year.desc(), ExamMark.term).all()
    principal_comments = PrincipalComment.query.filter_by(student_id=student.id).all()
    pc_by_key = {}
    for pc in principal_comments:
        pc_by_key[(pc.subject_id, pc.term, pc.academic_year)] = pc
    return render_template('staff/principal/student_results.html', student=student, subjects=subjects,
                         monthly_tests=monthly_tests, exam_marks=exam_marks_list, pc_by_key=pc_by_key)


@app.route('/staff/principal/comment/save', methods=['POST'])
@login_required
@role_required('principal')
def principal_save_comment():
    student_id = request.form.get('student_id')
    subject_id = request.form.get('subject_id')
    term = request.form.get('term')
    academic_year = request.form.get('academic_year')
    comment = request.form.get('comment')

    existing = PrincipalComment.query.filter_by(
        student_id=student_id, subject_id=subject_id,
        term=term, academic_year=academic_year
    ).first()
    if existing:
        existing.comment = comment
    else:
        pc = PrincipalComment(
            student_id=student_id, subject_id=subject_id,
            term=term, academic_year=academic_year, comment=comment
        )
        db.session.add(pc)
    db.session.commit()
    flash('Comment saved.', 'success')
    return redirect(url_for('principal_student_results', student_id=student_id))


@app.route('/staff/principal/staff/add', methods=['GET', 'POST'])
@login_required
@role_required('principal')
def principal_add_staff():
    subjects = Subject.query.all()
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        subject_id = request.form.get('subject_id')

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('principal_add_staff'))

        reg_number = f'STF{username.upper()}'

        user = User(
            username=username, email=email, role=role, full_name=full_name,
            phone=phone, reg_number=reg_number,
            subject_id=int(subject_id) if subject_id and role == 'teacher' else None
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f'Staff {full_name} added as {role}. Reg: {reg_number}', 'success')
        return redirect(url_for('principal_dashboard'))

    return render_template('staff/principal/add_staff.html', subjects=subjects)


@app.route('/staff/principal/staff/edit/<int:staff_id>', methods=['GET', 'POST'])
@login_required
@role_required('principal')
def principal_edit_staff(staff_id):
    staff_member = User.query.get_or_404(staff_id)
    subjects = Subject.query.all()

    if request.method == 'POST':
        staff_member.full_name = request.form.get('full_name')
        staff_member.email = request.form.get('email')
        staff_member.phone = request.form.get('phone')
        staff_member.role = request.form.get('role')
        staff_member.subject_id = int(request.form.get('subject_id')) if request.form.get('subject_id') and request.form.get('role') == 'teacher' else None
        if request.form.get('password'):
            staff_member.set_password(request.form.get('password'))
        db.session.commit()
        flash('Staff updated.', 'success')
        return redirect(url_for('principal_dashboard'))

    return render_template('staff/principal/edit_staff.html', staff=staff_member, subjects=subjects)


@app.route('/staff/principal/staff/fire/<int:staff_id>')
@login_required
@role_required('principal')
def principal_fire_staff(staff_id):
    staff_member = User.query.get_or_404(staff_id)
    if staff_member.role == 'principal':
        flash('Cannot fire the principal.', 'danger')
        return redirect(url_for('principal_dashboard'))
    full_name = staff_member.full_name
    db.session.delete(staff_member)
    db.session.commit()
    flash(f'{full_name} has been fired and login removed.', 'warning')
    return redirect(url_for('principal_dashboard'))


@app.route('/staff/principal/student/toggle-status/<int:student_id>')
@login_required
@role_required('principal')
def principal_toggle_student_status(student_id):
    student = Student.query.get_or_404(student_id)
    student.is_active = not student.is_active
    status = 'reactivated' if student.is_active else 'deactivated'
    db.session.commit()
    flash(f'Student {student.full_name} has been {status}.', 'warning')
    return redirect(url_for('principal_dashboard'))


@app.route('/staff/principal/timetables')
@login_required
@role_required('principal')
def principal_timetables():
    subjects = Subject.query.all()
    teachers = User.query.filter_by(role='teacher').all()
    timetables = Timetable.query.order_by(Timetable.form, Timetable.day_of_week, Timetable.start_time).all()
    exam_timetables = ExamTimetable.query.order_by(ExamTimetable.exam_date, ExamTimetable.start_time).all()
    return render_template('staff/principal/timetables.html', subjects=subjects, teachers=teachers, timetables=timetables, exam_timetables=exam_timetables)


@app.route('/staff/principal/timetable/add', methods=['POST'])
@login_required
@role_required('principal')
def principal_add_timetable():
    tt = Timetable(
        form=request.form.get('form'), day_of_week=request.form.get('day_of_week'),
        subject_id=int(request.form.get('subject_id')), start_time=request.form.get('start_time'),
        end_time=request.form.get('end_time'), teacher_id=int(request.form.get('teacher_id')),
        room=request.form.get('room')
    )
    db.session.add(tt)
    db.session.commit()
    flash('Timetable entry added.', 'success')
    return redirect(url_for('principal_timetables'))


@app.route('/staff/principal/exam-timetable/add', methods=['POST'])
@login_required
@role_required('principal')
def principal_add_exam_timetable():
    ett = ExamTimetable(
        form=request.form.get('form'), subject_id=int(request.form.get('subject_id')),
        exam_date=datetime.strptime(request.form.get('exam_date'), '%Y-%m-%d').date(),
        start_time=request.form.get('start_time'), end_time=request.form.get('end_time'),
        room=request.form.get('room')
    )
    db.session.add(ett)
    db.session.commit()
    flash('Exam timetable entry added.', 'success')
    return redirect(url_for('principal_timetables'))


@app.route('/staff/principal/timetable/delete/<int:tt_id>')
@login_required
@role_required('principal')
def principal_delete_timetable(tt_id):
    db.session.delete(Timetable.query.get_or_404(tt_id))
    db.session.commit()
    flash('Timetable entry deleted.', 'success')
    return redirect(url_for('principal_timetables'))


@app.route('/staff/principal/exam-timetable/delete/<int:ett_id>')
@login_required
@role_required('principal')
def principal_delete_exam_timetable(ett_id):
    db.session.delete(ExamTimetable.query.get_or_404(ett_id))
    db.session.commit()
    flash('Exam timetable entry deleted.', 'success')
    return redirect(url_for('principal_timetables'))


@app.route('/staff/principal/fee-settings', methods=['GET', 'POST'])
@login_required
@role_required('principal')
def principal_fee_settings():
    if request.method == 'POST':
        form = request.form.get('form', '').strip()
        term_fee = float(request.form.get('term_fee', 0))
        if form and term_fee > 0:
            existing = FeeSetting.query.filter_by(form=form).first()
            if existing:
                existing.term_fee = term_fee
            else:
                db.session.add(FeeSetting(form=form, term_fee=term_fee))
            db.session.commit()
            flash(f'Fee for {form} set to ${term_fee:.2f}.', 'success')
        return redirect(url_for('principal_fee_settings'))

    fee_settings = FeeSetting.query.order_by(FeeSetting.form).all()
    forms = ['Form 1', 'Form 2', 'Form 3', 'Form 4', 'Form 5', 'Form 6']
    return render_template('staff/principal/fee_settings.html', fee_settings=fee_settings, forms=forms)


@app.route('/staff/principal/fee-settings/delete/<int:fs_id>')
@login_required
@role_required('principal')
def principal_delete_fee_setting(fs_id):
    fs = FeeSetting.query.get_or_404(fs_id)
    db.session.delete(fs)
    db.session.commit()
    flash('Fee setting removed.', 'success')
    return redirect(url_for('principal_fee_settings'))


@app.route('/staff/principal/student/<int:student_id>/edit-fees', methods=['GET', 'POST'])
@login_required
@role_required('principal')
def principal_edit_student_fees(student_id):
    student = Student.query.get_or_404(student_id)
    fee_account = FeeAccount.query.filter_by(student_id=student.id).first()

    if request.method == 'POST':
        total_fees = float(request.form.get('total_fees', 0))
        amount_paid = float(request.form.get('amount_paid', 0))
        if not fee_account:
            fee_account = FeeAccount(student_id=student.id, term='Term 1')
            db.session.add(fee_account)
        fee_account.total_fees = total_fees
        fee_account.amount_paid = amount_paid
        fee_account.balance = total_fees - amount_paid
        db.session.commit()
        flash(f'Fees updated for {student.full_name}.', 'success')
        return redirect(url_for('principal_dashboard'))

    return render_template('staff/principal/edit_fees.html', student=student, fee_account=fee_account)


# ============ EXPORT ROUTES ============

@app.route('/staff/principal/export/zimsec-candidates')
@login_required
@role_required('principal')
def export_zimsec_candidates():
    students = Student.query.filter_by(curriculum='ZIMSEC', is_active=True).order_by(Student.form, Student.last_name).all()
    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student ID', 'Reg Number', 'Full Name', 'Form', 'Subjects', 'Gender'])
    for s in students:
        subs = ', '.join(ss.subject.name for ss in s.subjects)
        writer.writerow([s.student_id, s.reg_number, s.full_name, s.form, subs, ''])
    response = app.response_class(output.getvalue(), mimetype='text/csv',
                                  headers={'Content-Disposition': 'attachment; filename=zimsec_candidates.csv'})
    log_activity('Exported ZIMSEC candidate list', user=current_user)
    return response


@app.route('/staff/principal/export/ministry-report')
@login_required
@role_required('principal')
def export_ministry_report():
    term = 'Term 1'
    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Form', 'Total Students', 'Total Passed', 'Pass Rate', 'Total Expected Fees', 'Total Collected', 'Outstanding'])
    forms = ['Form 1', 'Form 2', 'Form 3', 'Form 4', 'Form 5', 'Form 6']
    for f in forms:
        sids = [s.id for s in Student.query.filter_by(form=f).all()]
        total = len(sids)
        passed = 0
        if sids:
            exams = ExamMark.query.filter(ExamMark.student_id.in_(sids), ExamMark.term == term).all()
            if exams:
                passed = sum(1 for e in exams if e.marks / e.total_marks * 100 >= 50)
        fee_total = db.session.query(db.func.sum(FeeAccount.total_fees)).filter(FeeAccount.term == term).scalar() or 0
        fee_collected = db.session.query(db.func.sum(Payment.amount)).filter(Payment.cleared == True).scalar() or 0
        outstanding_fees = fee_total - fee_collected
        pass_rate = round(passed / total * 100, 1) if total > 0 else 0
        writer.writerow([f, total, passed, f'{pass_rate}%', f'${fee_total:.2f}', f'${fee_collected:.2f}', f'${outstanding_fees:.2f}'])
    response = app.response_class(output.getvalue(), mimetype='text/csv',
                                  headers={'Content-Disposition': 'attachment; filename=ministry_report.csv'})
    log_activity('Exported Ministry report', user=current_user)
    return response


# ============ STUDENT ROUTES ============

@app.route('/student/dashboard')
@login_required
@student_required
def student_dashboard():
    subjects = [ss.subject for ss in current_user.subjects if ss.subject]
    monthly_tests = MonthlyTest.query.filter_by(student_id=current_user.id).all()
    exam_marks_list = ExamMark.query.filter_by(student_id=current_user.id).all()
    fee_account = FeeAccount.query.filter_by(student_id=current_user.id).first()
    payments = Payment.query.filter_by(student_id=current_user.id).order_by(Payment.created_at.desc()).limit(10).all()
    timetables = Timetable.query.filter_by(form=current_user.form).order_by(Timetable.day_of_week, Timetable.start_time).all()
    exam_timetables = ExamTimetable.query.filter_by(form=current_user.form).order_by(ExamTimetable.exam_date).all()

    # Get teacher for each subject
    subject_teachers = {}
    for subj in subjects:
        teacher = User.query.filter_by(subject_id=subj.id, role='teacher').first()
        subject_teachers[subj.id] = teacher

    # Get teacher remarks for this student
    teacher_remarks = TeacherRemark.query.filter_by(student_id=current_user.id).order_by(TeacherRemark.created_at.desc()).all()
    recent_activity_posts = Activity.query.filter_by(visibility='all').order_by(Activity.created_at.desc()).limit(10).all()

    return render_template('student/dashboard.html', subjects=subjects, monthly_tests=monthly_tests,
                         exam_marks=exam_marks_list, fee_account=fee_account, payments=payments,
                         timetables=timetables, exam_timetables=exam_timetables, subject_teachers=subject_teachers,
                         teacher_remarks=teacher_remarks, recent_activity_posts=recent_activity_posts)


@app.route('/student/results')
@login_required
@student_required
def student_results():
    fee_account = FeeAccount.query.filter_by(student_id=current_user.id).first()
    fees_cleared = not fee_account or fee_account.balance <= 0

    subjects = [ss.subject for ss in current_user.subjects if ss.subject]
    monthly_tests = MonthlyTest.query.filter_by(student_id=current_user.id).all()
    exam_marks_list = ExamMark.query.filter_by(student_id=current_user.id).all()

    principal_comments = PrincipalComment.query.filter_by(student_id=current_user.id).all()
    pc_by_key = {}
    for pc in principal_comments:
        pc_by_key[(pc.subject_id, pc.term, pc.academic_year)] = pc

    results = {}
    for subj in subjects:
        s_monthly = [mt for mt in monthly_tests if mt.subject_id == subj.id]
        s_exam = [em for em in exam_marks_list if em.subject_id == subj.id]

        # Previous results (different academic year or term)
        level = 'A' if '6' in current_user.form or '5' in current_user.form else 'O'
        prev_monthly = MonthlyTest.query.filter(
            MonthlyTest.student_id == current_user.id,
            MonthlyTest.subject_id == subj.id,
            MonthlyTest.academic_year < str(datetime.now().year)
        ).order_by(MonthlyTest.academic_year, MonthlyTest.term).all()
        prev_exam = ExamMark.query.filter(
            ExamMark.student_id == current_user.id,
            ExamMark.subject_id == subj.id,
            ExamMark.academic_year < str(datetime.now().year)
        ).order_by(ExamMark.academic_year, ExamMark.term).all()

        pc = pc_by_key.get((subj.id, 'Term 1', str(datetime.now().year)))

        results[subj.name] = {
            'monthly': s_monthly, 'exam': s_exam,
            'prev_monthly': prev_monthly, 'prev_exam': prev_exam,
            'level': level, 'principal_comment': pc.comment if pc else None
        }

    return render_template('student/results.html', results=results, fees_cleared=fees_cleared, fee_account=fee_account)


@app.route('/student/finances')
@login_required
@student_required
def student_finances():
    fee_account = FeeAccount.query.filter_by(student_id=current_user.id).first()
    payments = Payment.query.filter_by(student_id=current_user.id).order_by(Payment.created_at.desc()).all()
    return render_template('student/finances.html', fee_account=fee_account, payments=payments)


@app.route('/student/timetables')
@login_required
@student_required
def student_timetables():
    timetables = Timetable.query.filter_by(form=current_user.form).order_by(Timetable.day_of_week, Timetable.start_time).all()
    exam_timetables_list = ExamTimetable.query.filter_by(form=current_user.form).order_by(ExamTimetable.exam_date).all()

    timetable_by_day = {}
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        timetable_by_day[day] = [tt for tt in timetables if tt.day_of_week == day]

    return render_template('student/timetables.html', timetable_by_day=timetable_by_day, exam_timetables=exam_timetables_list)


@app.route('/student/subjects')
@login_required
@student_required
def student_subjects():
    subjects = [ss.subject for ss in current_user.subjects if ss.subject]
    subject_teachers = {}
    for subj in subjects:
        teacher = User.query.filter_by(subject_id=subj.id, role='teacher').first()
        subject_teachers[subj.id] = teacher
    return render_template('student/subjects.html', subjects=subjects, subject_teachers=subject_teachers)


# ============ SEED DATA ============

@app.route('/setup')
def setup():
    if Subject.query.first() is not None and os.environ.get('ENABLE_SETUP', '').lower() != 'true':
        return 'Setup is disabled.', 403
    db.drop_all()
    db.create_all()

    ol = [
        ('Mathematics', 'MATH', 'O'), ('English Language', 'ENG', 'O'), ('Shona', 'SHO', 'O'),
        ('Ndebele', 'NDEB', 'O'), ('Combined Science', 'CSC', 'O'), ('Biology', 'BIO', 'O'),
        ('Chemistry', 'CHEM', 'O'), ('Physics', 'PHY', 'O'), ('History', 'HIST', 'O'),
        ('Geography', 'GEOG', 'O'), ('Accounts', 'ACCT', 'O'), ('Business Studies', 'BS', 'O'),
        ('Economics', 'ECON', 'O'), ('Computer Science', 'COMP', 'O'), ('Food & Nutrition', 'FOOD', 'O'),
        ('Fashion & Fabrics', 'FASH', 'O'), ('Woodwork', 'WOOD', 'O'), ('Metalwork', 'MET', 'O'),
        ('Technical Graphics', 'TECHG', 'O'), ('Building Studies', 'BUILD', 'O'), ('Agriculture', 'AGRI', 'O'),
        ('Religious Studies', 'RELS', 'O'), ('Literature in English', 'LITE', 'O'), ('French', 'FREN', 'O'),
        ('Portuguese', 'PORT', 'O'), ('Music', 'MUS', 'O'), ('Art', 'ART', 'O'),
    ]
    al = [
        ('Pure Mathematics', 'MATH-PURE', 'A'), ('Statistics', 'MATH-STAT', 'A'),
        ('Mechanics', 'MATH-MECH', 'A'), ('Further Mathematics', 'MATH-FURTHER', 'A'),
        ('English Literature', 'ELIT-A', 'A'), ('Shona', 'SHO-A', 'A'),
        ('Ndebele', 'NDEB-A', 'A'), ('Biology', 'BIO-A', 'A'), ('Chemistry', 'CHEM-A', 'A'),
        ('Physics', 'PHY-A', 'A'), ('History', 'HIST-A', 'A'), ('Geography', 'GEOG-A', 'A'),
        ('Accounts', 'ACCT-A', 'A'), ('Economics', 'ECON-A', 'A'), ('Business Studies', 'BS-A', 'A'),
        ('Computer Science', 'COMP-A', 'A'), ('Food Science', 'FOOD-A', 'A'), ('Fashion & Fabrics', 'FASH-A', 'A'),
        ('Technical Graphics', 'TECHG-A', 'A'), ('Agriculture', 'AGRI-A', 'A'), ('Divinity', 'DIV-A', 'A'),
        ('Religious Studies', 'RELS-A', 'A'), ('Literature in English', 'LITE-A', 'A'), ('French', 'FREN-A', 'A'),
        ('Portuguese', 'PORT-A', 'A'), ('Sociology', 'SOC-A', 'A'), ('Management of Business', 'MOB-A', 'A'),
    ]

    for name, code, level in ol + al:
        db.session.add(Subject(name=name, code=code, level=level))
    db.session.commit()

    default_fees = [('Form 1', 350), ('Form 2', 350), ('Form 3', 400), ('Form 4', 500), ('Form 5', 450), ('Form 6', 600)]
    for form, fee in default_fees:
        db.session.add(FeeSetting(form=form, term_fee=fee))
    db.session.commit()

    principal = User(username='principal', email='principal@schoolbridge.zw', role='principal',
                     full_name='Dr. T. Chigumba', reg_number='REG-PRINCIPAL', phone='+263 712 345 678')
    principal.set_password('principal123')
    db.session.add(principal)

    admin = User(username='admin', email='admin@schoolbridge.zw', role='admin',
                 full_name='Mr. K. Moyo', reg_number='REG-ADMIN', phone='+263 712 345 679')
    admin.set_password('admin123')
    db.session.add(admin)

    cashier = User(username='cashier', email='cashier@schoolbridge.zw', role='cashier',
                   full_name='Mrs. S. Dube', reg_number='REG-CASHIER', phone='+263 712 345 680')
    cashier.set_password('cashier123')
    db.session.add(cashier)

    math_s = Subject.query.filter_by(code='MATH').first()
    eng_s = Subject.query.filter_by(code='ENG').first()
    sci_s = Subject.query.filter_by(code='CSC').first()
    bio_s = Subject.query.filter_by(code='BIO').first()
    hist_s = Subject.query.filter_by(code='HIST').first()
    geo_s = Subject.query.filter_by(code='GEOG').first()

    teachers_data = [
        ('teacher1', 'teacher1@schoolbridge.zw', 'Mr. A. Chikwanha', math_s.id, '+263 712 345 681'),
        ('teacher2', 'teacher2@schoolbridge.zw', 'Ms. P. Nyoni', eng_s.id, '+263 712 345 682'),
        ('teacher3', 'teacher3@schoolbridge.zw', 'Mr. B. Sibanda', sci_s.id, '+263 712 345 683'),
        ('teacher4', 'teacher4@schoolbridge.zw', 'Dr. M. Gumbo', bio_s.id, '+263 712 345 684'),
        ('teacher5', 'teacher5@schoolbridge.zw', 'Mrs. T. Moyo', hist_s.id, '+263 712 345 685'),
        ('teacher6', 'teacher6@schoolbridge.zw', 'Mr. C. Dlamini', geo_s.id, '+263 712 345 686'),
    ]
    for uname, email, name, subj_id, phone in teachers_data:
        t = User(username=uname, email=email, role='teacher', full_name=name,
                 subject_id=subj_id, phone=phone, reg_number=f'REG-{uname.upper()}')
        t.set_password('teacher123')
        db.session.add(t)
    db.session.commit()

    forms = ['Form 4', 'Form 4', 'Form 3', 'Form 3', 'Form 4', 'Form 6']
    sample_data = [
        ('2026001', 'Tendai', 'Mukaro', 'Form 4', [math_s, eng_s, sci_s, bio_s, hist_s], '+263 712 000 001'),
        ('2026002', 'Chipo', 'Dube', 'Form 4', [math_s, eng_s, bio_s, geo_s], '+263 712 000 002'),
        ('2026003', 'Tafadzwa', 'Sithole', 'Form 3', [math_s, sci_s, geo_s, hist_s], '+263 712 000 003'),
        ('2026004', 'Rutendo', 'Gumbo', 'Form 3', [eng_s, sci_s, bio_s], '+263 712 000 004'),
        ('2026005', 'Kudzai', 'Zhou', 'Form 4', [math_s, eng_s, sci_s, bio_s, hist_s, geo_s], '+263 712 000 005'),
        ('2026006', 'Tanaka', 'Chigumba', 'Form 6', [Subject.query.filter_by(code='MATH-PURE').first(), Subject.query.filter_by(code='BIO-A').first(), Subject.query.filter_by(code='CHEM-A').first()], '+263 712 000 006'),
    ]

    for sid, fn, ln, form, subjs, phone in sample_data:
        reg = f'REG-{sid}'
        curriculum = 'Cambridge' if form in ('Form 5', 'Form 6') else 'ZIMSEC'
        student = Student(student_id=sid, first_name=fn, last_name=ln, form=form,
                         curriculum=curriculum,
                         email=f'{fn.lower()}.{ln.lower()}@student.schoolbridge.zw',
                         reg_number=reg, phone=phone)
        student.set_password('student123')
        db.session.add(student)
        db.session.flush()
        for subj in subjs:
            db.session.add(StudentSubject(student_id=student.id, subject_id=subj.id))

        balance = 0.0 if sid == '2026005' else 200.0
        fee = FeeAccount(student_id=student.id, term='Term 1', total_fees=500.00, amount_paid=500.00 - balance, balance=balance)
        db.session.add(fee)

    db.session.commit()

    # Sample marks for 2026001
    s1 = Student.query.filter_by(student_id='2026001').first()
    t1 = User.query.filter_by(username='teacher1').first()
    if s1 and t1:
        for month, mks in [('January', 68), ('February', 72), ('March', 65)]:
            db.session.add(MonthlyTest(student_id=s1.id, subject_id=math_s.id, term='Term 1',
                                       month=month, marks=mks, total_marks=100, teacher_id=t1.id))
        db.session.add(ExamMark(student_id=s1.id, subject_id=math_s.id, term='Term 1',
                                exam_type='Mid-Term', marks=71, total_marks=100, teacher_id=t1.id))

    db.session.commit()
    return 'System setup complete! <a href="/auth/login">Login</a>'


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=os.environ.get('FLASK_DEBUG', '').lower() == 'true', port=5000)

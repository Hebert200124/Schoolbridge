from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


def zim_grade(marks, total_marks, level='O'):
    pct = (marks / total_marks) * 100 if total_marks > 0 else 0
    if level == 'A':
        if pct >= 70: return 'A'
        if pct >= 60: return 'B'
        if pct >= 50: return 'C'
        if pct >= 45: return 'D'
        if pct >= 40: return 'E'
        if pct >= 35: return 'O'
        return 'F'
    else:
        if pct >= 70: return 'A'
        if pct >= 60: return 'B'
        if pct >= 50: return 'C'
        if pct >= 45: return 'D'
        if pct >= 40: return 'E'
        return 'U'


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    reg_number = db.Column(db.String(50), unique=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    teacher_subject = db.relationship('Subject', backref='teacher', lazy=True, foreign_keys=[subject_id])
    payments = db.relationship('Payment', backref='cashier', lazy=True, foreign_keys='Payment.cashier_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Subject(db.Model):
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    level = db.Column(db.String(5), default='O')

    students = db.relationship('StudentSubject', backref='subject', lazy=True)
    monthly_tests = db.relationship('MonthlyTest', backref='subject', lazy=True)
    exam_marks = db.relationship('ExamMark', backref='subject', lazy=True)


class Student(UserMixin, db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    form = db.Column(db.String(10), nullable=False)
    curriculum = db.Column(db.String(10), default='ZIMSEC')
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))
    reg_number = db.Column(db.String(50), unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subjects = db.relationship('StudentSubject', backref='student', lazy=True)
    monthly_tests = db.relationship('MonthlyTest', backref='student', lazy=True)
    exam_marks = db.relationship('ExamMark', backref='student', lazy=True)
    fee_account = db.relationship('FeeAccount', backref='student', uselist=False, lazy=True)
    payments = db.relationship('Payment', backref='student', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f'student_{self.id}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'


class StudentSubject(db.Model):
    __tablename__ = 'student_subjects'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)


class MonthlyTest(db.Model):
    __tablename__ = 'monthly_tests'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    term = db.Column(db.String(10), nullable=False)
    academic_year = db.Column(db.String(10), default=lambda: str(datetime.now().year))
    month = db.Column(db.String(20), nullable=False)
    marks = db.Column(db.Float, nullable=False)
    total_marks = db.Column(db.Float, default=100.0)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comment = db.Column(db.Text)
    entered_by = db.relationship('User', backref='entered_tests', foreign_keys=[teacher_id])
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def grade(self, level='O'):
        return zim_grade(self.marks, self.total_marks, level)


class ExamMark(db.Model):
    __tablename__ = 'exam_marks'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    term = db.Column(db.String(10), nullable=False)
    academic_year = db.Column(db.String(10), default=lambda: str(datetime.now().year))
    exam_type = db.Column(db.String(50), nullable=False)
    marks = db.Column(db.Float, nullable=False)
    total_marks = db.Column(db.Float, default=100.0)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comment = db.Column(db.Text)
    entered_by = db.relationship('User', backref='entered_exams', foreign_keys=[teacher_id])
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def grade(self, level='O'):
        return zim_grade(self.marks, self.total_marks, level)


class PrincipalComment(db.Model):
    __tablename__ = 'principal_comments'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    term = db.Column(db.String(10), nullable=False)
    academic_year = db.Column(db.String(10), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = db.relationship('Student', backref='principal_comments', lazy=True)
    subject = db.relationship('Subject', backref='principal_comments', lazy=True)


class FeeAccount(db.Model):
    __tablename__ = 'fee_accounts'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    term = db.Column(db.String(10), nullable=False)
    total_fees = db.Column(db.Float, default=0.0)
    amount_paid = db.Column(db.Float, default=0.0)
    balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    receipt_number = db.Column(db.String(50), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False)
    payment_method = db.Column(db.String(50))
    reference = db.Column(db.String(100))
    cashier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    cleared = db.Column(db.Boolean, default=False)
    cleared_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FeeSetting(db.Model):
    __tablename__ = 'fee_settings'

    id = db.Column(db.Integer, primary_key=True)
    form = db.Column(db.String(10), unique=True, nullable=False)
    term_fee = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TeacherRemark(db.Model):
    __tablename__ = 'teacher_remarks'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    remark = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('Student', backref='teacher_remarks', lazy=True)
    teacher = db.relationship('User', backref='teacher_remarks', lazy=True)


class Timetable(db.Model):
    __tablename__ = 'timetables'

    id = db.Column(db.Integer, primary_key=True)
    form = db.Column(db.String(10), nullable=False)
    day_of_week = db.Column(db.String(15), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    room = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subject_rel = db.relationship('Subject', backref='timetable_entries', foreign_keys=[subject_id])
    teacher_rel = db.relationship('User', backref='timetable_entries', foreign_keys=[teacher_id])


class ExamTimetable(db.Model):
    __tablename__ = 'exam_timetables'

    id = db.Column(db.Integer, primary_key=True)
    form = db.Column(db.String(10), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    exam_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    room = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subject_rel = db.relationship('Subject', backref='exam_timetable_entries', foreign_keys=[subject_id])


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    visibility = db.Column(db.String(10), default='public')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='activities', foreign_keys=[user_id])
    student = db.relationship('Student', backref='activities', foreign_keys=[student_id])


class Activity(db.Model):
    __tablename__ = 'activities'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    visibility = db.Column(db.String(10), default='all')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', backref='posted_activities', foreign_keys=[created_by])


class StaffLeave(db.Model):
    __tablename__ = 'staff_leaves'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    staff = db.relationship('User', backref='leaves', foreign_keys=[user_id])


class LevyFund(db.Model):
    __tablename__ = 'levy_funds'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    total_amount = db.Column(db.Float, default=0.0)
    amount_collected = db.Column(db.Float, default=0.0)
    term = db.Column(db.String(10), nullable=False)
    academic_year = db.Column(db.String(10), default=lambda: str(datetime.now().year))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def balance(self):
        return self.total_amount - self.amount_collected


class OTPCode(db.Model):
    __tablename__ = 'otp_codes'

    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    attempts = db.Column(db.Integer, default=0)
    request_count = db.Column(db.Integer, default=1)
    request_window_start = db.Column(db.DateTime, default=datetime.utcnow)

    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    def is_rate_limited(self):
        return self.request_count >= 3 and (datetime.utcnow() - self.request_window_start).total_seconds() < 900

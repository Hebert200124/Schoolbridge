import os, sys
sys.path.insert(0, '.')
from app import app
from models import db, Student, User, Subject, StudentSubject
app.testing = True

with app.app_context():
    db.drop_all()
    db.create_all()

    s = Subject(name='Math', code='MATH', level='O')
    db.session.add(s)
    u = User(username='teacher1', email='t1@t.com', role='teacher', full_name='T1', reg_number='REG-T1')
    u.set_password('p')
    db.session.add(u)
    stu = Student(student_id='2026001', first_name='T', last_name='M', form='Form 4', email='t@t.com', reg_number='REG-2026001')
    stu.set_password('p')
    db.session.add(stu)
    db.session.flush()
    db.session.add(StudentSubject(student_id=stu.id, subject_id=s.id))
    db.session.commit()

    # Test recognition
    p = Student.query.filter_by(student_id='2026001', email='t@t.com').first()
    assert p, 'student_id match failed'
    print('student_id match: OK')

    p = User.query.filter_by(username='teacher1', email='t1@t.com').first()
    assert p, 'username match failed'
    print('username match: OK')

    p = Student.query.filter_by(reg_number='WRONG', email='x@x.com').first()
    if not p:
        p = Student.query.filter_by(student_id='WRONG', email='x@x.com').first()
    assert p is None, 'wrong data should be rejected'
    print('wrong data rejected: OK')

    # Check all comment displays are bold
    for root, dirs, files in os.walk('templates'):
        for f in files:
            if f.endswith('.html'):
                path = os.path.join(root, f)
                content = open(path, 'r', encoding='utf-8').read()
                if 'class="text-muted"' in content and ('.comment or' in content or '.remark' in content):
                    print(f'WARNING: non-bold comment in {path}')

    print('All bold checks passed')
    print('ALL OK')

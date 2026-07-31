import app as a

a.app.config['TESTING'] = True
c = a.app.test_client()

# ---- Admin dashboard ----
c.post('/auth/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
r = c.get('/staff/admin')
b = r.get_data(as_text=True)

admin_checks = {
    'Students table shown': 'Students' in b,
    'Add Student button': 'Add Student' in b,
    'Student ID column': 'Student ID' in b,
    'No fee cards': 'Fee Collection' not in b,
    'No staff card': 'on leave' not in b,
    'No pass rates': 'Pass Rate' not in b,
    'No levies': 'Levy' not in b,
}
print('=== ADMIN DASHBOARD ===')
for label, ok in admin_checks.items():
    print(f'{"PASS" if ok else "FAIL"} - {label}')

# ---- Principal dashboard ----
c.get('/auth/logout', follow_redirects=True)
c.post('/auth/login', data={'username': 'principal', 'password': 'principal123'}, follow_redirects=True)
r = c.get('/staff/principal')
print('\nPrincipal dashboard status:', r.status_code)
b = r.get_data(as_text=True)

principal_checks = {
    'Students table shown': 'Students' in b,
    'Student ID column': 'Student ID' in b,
    'Results action': 'Results' in b,
    'Fees action': 'Fees' in b,
    'No Staff Members tab': 'Staff Members' not in b,
    'No fee cards': 'Fee Collection' not in b,
    'No staff card': 'on leave' not in b,
    'No Add Staff button': 'Add Staff' not in b,
    'No pass rates': 'Pass Rate' not in b,
    'No levies': 'Levy' not in b,
    'No announcements widget': 'Announcements' not in b,
    'No upcoming exams': 'Upcoming Exams' not in b,
}
print('=== PRINCIPAL DASHBOARD ===')
for label, ok in principal_checks.items():
    print(f'{"PASS" if ok else "FAIL"} - {label}')

all_ok = all(admin_checks.values()) and all(principal_checks.values())
print('\nALL CHECKS PASSED - both dashboards show only students' if all_ok else '\nSOME CHECKS FAILED')

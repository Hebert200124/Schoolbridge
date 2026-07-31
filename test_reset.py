import re
import app as a

a.app.config['TESTING'] = True
c = a.app.test_client()

# Step 1 - enter reg number only
r = c.post('/auth/reset-password',
           data={'reg_number': 'REG-2026001'},
           follow_redirects=True)
print('Step 1 - reg number ->', r.request.path)

# Wrong email on step 2 must NOT reveal anything (generic error, stays on page)
r_bad = c.post('/auth/reset-email',
               data={'email': 'wrong@example.com'},
               follow_redirects=True)
print('Step 2a - wrong email ->', r_bad.request.path,
      '| generic msg:', 'If those details match our records' in r_bad.get_data(as_text=True))

# Correct email on step 2
r = c.post('/auth/reset-email',
           data={'email': 'tendai.mukaro@student.schoolbridge.zw'},
           follow_redirects=True)
print('Step 2 - email ->', r.request.path)

m = re.search(r'\[DEV\] OTP[^<]*?(\d{6})', r.get_data(as_text=True))
if not m:
    print('No [DEV] OTP found. Check FLASK_DEBUG=true and that reg/email match.')
    raise SystemExit(1)
code = m.group(1)
print('Step 3 - OTP:', code)

r2 = c.post('/auth/reset-code', data={'code': code}, follow_redirects=True)
print('Step 4 - verify OTP ->', r2.request.path)

r3 = c.post('/auth/reset-set-password',
            data={'new_password': 'NewPass123', 'confirm_password': 'NewPass123'},
            follow_redirects=True)
print('Step 5 - set password ->', r3.request.path)

r4 = c.post('/auth/login',
            data={'username': '2026001', 'password': 'NewPass123'},
            follow_redirects=True)
print('Step 6 - login ->', r4.request.path)

# SchoolBridge - System Feature Report

A comprehensive report of everything the SchoolBridge school management platform does, organised by feature area. It describes the functions users perform and see - no code is discussed.

---

## 1. System Overview

SchoolBridge is a web-based school management system built for Zimbabwean secondary schools. It manages **students, staff, subjects, marks, fees, payments, timetables, leave, announcements and reporting** for one or more school campuses from a single platform.

The system supports multiple campuses under one umbrella. Each campus is fully isolated from the others - staff and students at one campus only ever see that campus's data. A central Super Admin can see and manage every campus.

### Roles in the system

| Role | Who they are | Main focus |
|------|--------------|------------|
| **Super Admin** | System administrator | Every campus, campus setup, staff assignment |
| **Principal** | Head of a campus | Students, staff, fees, timetables, leave, reports |
| **Admin** | School administrator | Student registration and management, announcements |
| **Teacher** | Subject teacher | Marks entry, results, remarks |
| **Cashier** | Fees clerk | Payments, fee accounts, clearance |
| **Student** | Learner | Own subjects, results, finances, timetables |

---

## 2. Authentication, Access Control & Security

### Logging in
- Users and students sign in with a **username** (students use their student ID) and a **password**.
- On success, each user is taken to the dashboard appropriate to their role.
- The system distinguishes students from staff and directs each to the right area.
- **Inactive accounts** cannot log in; the user is told the account has been deactivated and to contact the school.

### Password rules
- New passwords must be **at least 8 characters**, contain **both letters and numbers**, and must not be a common or weak password.
- When changing a password the user must supply the current password, and the new password must differ from the current one.
- After changing the password the user is logged out and must log in again with the new password.

### Forgot password (self-service reset)
- A user enters their **registration number**.
- The system looks the person up, tolerating formatting variations (dashes, a REG- prefix, casing).
- They then enter the **email** on record. A neutral message is always shown whether or not the details match, so accounts cannot be probed.
- A **6-digit one-time code (OTP)** is emailed to the registered address.
- The code expires after **10 minutes** and users get **5 attempts** before needing a fresh code.
- OTP requests are throttled: at most one per minute, and after 3 requests in 15 minutes further requests are blocked for a while.
- Once verified, the user sets a new password (subject to the same strength rules) and can log in.

### Account and session behaviour
- Users can log out at any time.
- Login attempts are rate-limited to protect against brute force.
- Every page is protected so a role can only reach the areas it is allowed to.

### Browser security hardening
The platform enforces modern web security headers on every page:
- A Content Security Policy that restricts scripts, styles and connections to trusted sources.
- Blocking the site from being embedded in other websites' frames.
- Preventing browsers from MIME-sniffing.
- A strict referrer policy and strict transport security over HTTPS.
- Camera, microphone and geolocation access are blocked by default.

---

## 3. Super Admin Functions

The Super Admin is the only role that spans the whole organisation.

### Global dashboard
- Summary cards for **Campuses**, **Total Students**, **Total Staff** and **Total Fees Collected** across all campuses.
- A table of every campus showing name, code, address, student count and staff count.
- Each card is clickable and opens the page that matches its label (e.g. "Total Students" opens the student list, "Total Staff" opens the staff list).

### Campus management
- **Add a campus** - give it a name, a unique code and an address. The full standard subject list is installed for the new campus automatically.
- **Edit a campus** - rename it, or change the code or address. Codes must stay unique.
- **Delete a campus** - only possible when the campus has **no staff and no students** (data protection). The Main Campus can never be deleted. Deletion cleans up all related records safely.
- **View staff per campus** - open any campus to see its assigned staff.
- **Assign new staff to a campus** - create a staff account for a specific campus, choosing the role (principal, admin, cashier or teacher) and, for teachers, the subject they teach. Passwords must meet the strength rules.
- **Remove staff from a campus** - fire or remove any staff member except a Super Admin.

### Campus isolation
- The Super Admin sees everything; every other role only ever sees its own campus's data.
- The Super Admin can choose which campus new records (students, staff) are attached to when creating them.

---

## 4. Principal Functions

The principal runs a single campus and reaches all these areas from the dashboard and navigation menu.

### Dashboard
- Role cards for **Staff Members**, **Total Students**, **Active Students** and **Timetables**; each card opens the page it describes (staff card opens the staff list, student cards open the student list).
- A fee collection summary showing **Expected**, **Collected** and **Outstanding** for the current term, with a progress bar.
- A staff and attendance card showing **total staff**, **active staff** and how many are **currently on leave**.
- An **Upcoming Exams** panel with a countdown to each exam date, colour-coded by urgency.
- An **Outstanding Balances** list (highest first).
- Recent **announcements and activities**.
- **Pass rate by subject** and **pass rate by form** for the term, each with progress bars.
- Quick-access buttons for the **ZIMSEC candidates export** and the **Ministry report** export.

### Students
- **Full student list** with ID, reg number, name, form, curriculum, email, phone and active status.
- **View a student's results** - all monthly tests and exams across terms, with the ability to add or edit a **principal comment** per subject and term.
- **Edit fees** for an individual student.
- **Activate / deactivate** a student (deactivation effectively marks them transferred).
- **Permanently remove** a student - wipes their marks, fees, payments, comments, subject enrolments and remarks, with confirmation.
- **Bulk import students** from an Excel file (shared with Admin; see the Admin section).
- **Upload Excel** button for bulk student import.

### Staff
- **Staff list** page showing every staff member: name, username, role, subject, email and phone.
- **Add staff** - create a teacher/cashier/admin account with username, password, role, subject (for teachers), email and phone. Optionally mark them **on leave** immediately, with leave type and dates.
- **Edit staff** - change name, email, phone, role and subject; optionally reset their password.
- **Fire / remove staff** - deletes the person and their login. The principal cannot be fired this way.
- **Staff leave** - record leave (type, dates, reason); list all leave records; **approve, reject or delete** leave; see who is currently on leave. Leave feeds the dashboard's attendance figures.

### Fees
- **Fee settings** - set the term fee for each form (Form 1 to Form 6). Updating a fee for a form applies across the campus.
- **Delete a fee setting** for a form.
- **Edit a student's fees** - set the total and the amount already paid; the balance is computed automatically.

### Timetables
- **Weekly timetable** management - add entries by form, day of the week, time, subject, teacher and room; delete entries.
- **Exam timetable** management - schedule exams by form, subject, date, times and room; delete entries.
- Timetable management is reserved for campus principals (not available to the Super Admin).

### Reporting and exports
- **ZIMSEC candidates export** - a CSV of all active ZIMSEC students with reg numbers, forms and enrolled subjects.
- **Ministry report export** - a CSV with, per form: total students, total passed, pass rate, expected fees, collected fees and outstanding.

---

## 5. Admin (School Administrator) Functions

The Admin handles day-to-day student records and school communication.

### Dashboard
- Cards for **Total Students**, **Active Students** and **Register Student**.
- A fee collection summary (expected / collected / outstanding), staff and attendance card, upcoming exams, outstanding balances, announcements and pass-rate tables - the same overview data as the principal dashboard.
- The students page groups students into **active** and **inactive**.

### Student registration
- **Add a student** - enter first name, last name, form, curriculum (ZIMSEC or Cambridge), email, phone and a password, and select the subjects the student takes (O-Level and A-Level subjects are shown in separate lists).
- The system **auto-generates the student ID and registration number**, creates a **fee account** using the term fee for the student's form, and assigns the chosen subjects.

### Editing students
- **Edit a student** - change personal details, form, curriculum, password, and reassign their subjects (previous enrolment is replaced). If the form changes, the fee is recalculated to the new form's term fee.
- **Remove a student from all subjects**, with confirmation.

### Student lifecycle
- **Deactivate / reactivate** a student (deactivate = transferred).
- **Permanently remove** a student with full data cleanup (as the principal can).

### Bulk import
- **Download a template** Excel file showing the required columns.
- **Upload an Excel file** of students (.xlsx or .xls). Required columns: `first_name`, `last_name`, `form`. Optional: `curriculum`, `email`, `phone`.
- Validation is forgiving: numbers for forms are converted to "Form X", blank or invalid curriculum defaults to ZIMSEC, and incomplete rows are skipped and counted.
- On completion the system reports how many students were added and how many rows were skipped. The default password for imported students is `student123`.

### Announcements and activities
- **Quick log** an activity from the dashboard (action, description and visibility).
- A **full activities page** listing all announcements.
- **Create** an announcement with a title, description and visibility - **Everyone** (staff and students) or **Staff only**.
- **Edit** and **delete** announcements.

## 6. Teacher Functions

Teachers work with the single subject they are assigned to teach.

### Dashboard
- Cards for **Your Subject**, **Marks Entry**, **My Students** (count) and **Activities**, each linking to the relevant page.
- A welcome panel explaining what each page is for.
- Recent announcements are shown.

### My Class
- A list of all **active students** enrolled in the teacher's subject.
- For each student, access to their **results for that subject** - all monthly tests and exams, past and present terms.

### Marks entry
- Enter **monthly test marks** for a student: term, month, marks, total marks (default 100) and an optional comment.
- Enter **exam marks**: term, exam type, marks, total and comment.
- The system immediately shows the **ZIMSEC grade** the mark earns (grading differs for O-Level and A-Level students).
- **Edit** a mark's value, total and comment.
- **Delete** a mark - only the teacher who entered it can delete it.
- All marks are stored per academic year and term, so history is preserved.

### Remarks
- Add a **written remark** for a student; remarks appear on the student's dashboard.

---

## 7. Cashier Functions

The cashier manages money coming in.

### Dashboard
- Cards for **Pending Clearance** (payments awaiting clearing), **Payments Today** and **Search Student** (the fees page).
- A recent payments list (most recent first) with a quick **clear** action for each.

### Finding a student
- Search by **student ID** to open that student's fee page.

### Fee account view
- Shows the student's **fee account**: term, total fees, amount paid and balance.
- Shows the **detected / expected fee** for the student's form.
- Lists the student's **payment history**.

### Recording payments
- **Record a payment**: amount, payment method and a reference. A unique **receipt number** is generated automatically (e.g. RCP plus 8 digits).
- The payment starts as **pending clearance** and the student's paid amount and balance update immediately.
- **Clear a payment** once it is confirmed - this marks it paid and stamps the clearance time. Cleared payments count toward the school's collected totals.

### Setting up a fee account
- **Setup / update fees** for a student - set the total fee for a term; if an account exists it is updated, otherwise one is created.

---

## 8. Student Functions

Students see only their own data.

### Dashboard
- Clickable cards: **Subjects**, **Monthly Tests**, **Exam Results**, **Fee Balance** (colour-coded: green when cleared, amber when there is a balance) and the overall **Pass Rate**.
- **My Subjects and Teachers** table - subject, level, teacher name and email.
- **My Pass Rates by Subject** - progress bars with passed/total.
- **Fee Account** summary - term, total, paid, balance, with a button to the full statement.
- **Teacher Remarks** feed.
- **Weekly Timetable** (next few lessons) with a link to the full timetable.
- **Upcoming Exams** panel.
- **School Announcements** (only those marked visible to everyone).

### Subjects
- A page listing the student's subjects with the teacher responsible for each.

### Results
- Full results per subject: **monthly tests and exams** for the current term and year.
- **Previous years' marks** are also shown so progress can be compared.
- **Principal comments** appear per subject.
- **Pass rate** overall and by subject.
- If there is an outstanding fee balance, the unpaid status is displayed so the student is prompted to settle fees.

### Finances
- The student's **fee account** in detail - term, total, paid, balance.
- Full **payment history**, including method, reference, receipt number and dates.

### Timetables
- The **weekly timetable** laid out day by day (Monday to Friday) with times and subjects.
- The **exam timetable** with dates, subjects and rooms.

---

## 9. Shared Features

### ZIMSEC curriculum support
- The system ships with the **standard ZIMSEC subject catalogue - 27 O-Level and 27 A-Level subjects** (Mathematics, English, Shona, Ndebele, Sciences, Humanities, Commercial, Technical and Languages).
- Every campus automatically receives the full catalogue; new campuses get it on creation, and any campus missing subjects is topped up automatically.
- **Grading follows the ZIMSEC scales** for both O-Level (A, B, C, D, E, U) and A-Level (A, B, C, D, E, O, F), applied automatically to marks.

### Multi-campus isolation
- Every record (students, staff, subjects, marks, fees, payments, timetables, activities, leave) belongs to a campus.
- A user at one campus can never read or modify another campus's data; the Super Admin is the only exception.
- The system was upgraded to multi-campus without data loss - existing databases are migrated silently at startup.

### Announcements and activity feed
- Posts created by Admins with a visibility setting (**Everyone** vs **Staff only**) appear on the relevant dashboards.
- A **log of system actions** (who did what - payments recorded, students added, marks entered, exports made) is kept per campus and visible to staff.

### Fee engine
- Term fees are defined **per form and per campus**.
- Each student gets a **fee account per term** (total, paid, balance).
- Payments are recorded with receipts and must be **cleared** to count toward collection totals.
- Dashboards aggregate **expected**, **collected** and **outstanding** fees and show outstanding balances.

### Leave and attendance awareness
- Staff leave is recorded and approved or rejected, and the dashboards show who is **currently on leave** plus the active staff count.

---

## 10. System Setup and Maintenance

- **First-time setup**: a protected setup function rebuilds the database and creates a complete demo school - Main Campus, the full ZIMSEC subject list, default term fees, principal/admin/cashier/superadmin accounts, six sample teachers and six sample students (with subjects, fee accounts and sample marks). It only runs when explicitly enabled.
- **Auto-healing migrations**: on every start-up the system quietly fixes older databases - adding the curriculum field to students, widening the password-reset storage field, adding campus columns, and replacing outdated global unique rules with per-campus ones so multiple campuses can share the same subject codes.
- **Subject catalogue sync**: on every start-up every campus is checked and topped up with any missing standard subjects.
- The platform runs as a standard web application (deployed on Render with Postgres) and also works locally with SQLite.

---

## 11. Quick Feature Checklist

- [x] Multi-campus with full data isolation
- [x] Role-based logins (Super Admin, Principal, Admin, Teacher, Cashier, Student)
- [x] Secure password policy and rate-limited login
- [x] Email OTP password reset
- [x] Role-specific dashboards with clickable stat cards
- [x] Student registration (single and Excel bulk import)
- [x] Student editing, activation/deactivation and permanent removal
- [x] Subject assignment per student (O and A Level)
- [x] Teacher marks entry for monthly tests and exams with automatic ZIMSEC grading
- [x] Marks editing and deletion
- [x] Teacher remarks for students
- [x] Cashier payments with auto-generated receipts and pending clearance
- [x] Per-form, per-campus term fee settings
- [x] Student fee accounts and balance tracking
- [x] Principal staff management (add, edit, fire)
- [x] Staff leave recording and approval workflow
- [x] Weekly and exam timetables
- [x] Principal comments on student results
- [x] Announcements with visibility control
- [x] ZIMSEC candidates export (CSV)
- [x] Ministry report export (CSV)
- [x] Pass-rate analytics by subject and form
- [x] Student portal (results, finances, timetables, announcements)
- [x] Full ZIMSEC subject catalogue on every campus
- [x] Automatic database migrations and subject sync on startup

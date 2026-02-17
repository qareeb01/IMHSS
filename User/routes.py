# User/routes.py - Application Routes
import uuid
import datetime
import os
from flask import render_template, request, redirect, url_for, flash
from flask import session, Blueprint, jsonify, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from flask_mail import Message
from .models import User
from .database import users, students, messages, flags, counselor_messages
from .database import logs
from .auth import role_required, login_required, student_required
from .chat import send_message


routes = Blueprint('IMHSS', __name__, template_folder='templates',
                   static_folder='static')


# --------------------------------------------------
# Landing Page
# --------------------------------------------------
@routes.route('/')
def base():
    return render_template('base.html')


# --------------------------------------------------
# Counselor / Admin Authentication
# --------------------------------------------------
@routes.route('/counselor-admin/login', methods=['GET', 'POST'])
def counselor_login():
    if request.method == 'POST':
        counselor_record, email, password = User.counselor_admin_login()

        if not counselor_record:
            flash("Invalid credentials", "error")
            return redirect(url_for('.counselor_login'))

        if not check_password_hash(counselor_record.get('hashed_password'),
                                   password):
            flash("Invalid credentials", "error")
            return redirect(url_for('.counselor_login'))

        if counselor_record.get('status') == 'blocked':
            flash("Your account has been blocked. Contact admin.", "error")
            return redirect(url_for('.counselor_login'))

        timestamp = datetime.datetime.utcnow()
        users.update_one(
            {'email': email},
            {'$set': {"last_login": timestamp}}
        )

        session.clear()
        session["user_id"] = str(counselor_record["_id"])
        session["role"] = counselor_record.get("role")
        session["email"] = counselor_record.get("email")
        session["name"] = counselor_record.get("name")
        session["timestamp"] = timestamp.isoformat()

        if counselor_record.get("role") == "admin":
            flash("Login successful", "success")
            return redirect(url_for('.admin_dashboard'))

        if counselor_record.get("role") == "counselor":
            flash("Login successful", "success")
            return redirect(url_for('.counselor_dashboard'))

        flash("Unauthorized access", "error")
        return redirect(url_for('.counselor_login'))

    return render_template('counselor_login.html')


# --------------------------------------------------
# Forgot Password  (GET: show form | POST: send email)
# No login required — this is for locked-out users.
# --------------------------------------------------
@routes.route('/counselor-admin/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """
    Forgot-password flow for counselors and admins only.

    GET  — render the forgot-password form.
    POST — look up the email in the users collection:
           • Unknown email → flash a clear error (security: staff-only system).
           • Known but blocked → flash error.
           • Known and active → generate token, send email, redirect to login.
    """
    # Already logged in? Redirect away.
    if session.get('user_id'):
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('.admin_dashboard'))
        return redirect(url_for('.counselor_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if not email:
            flash("Please enter your email address.", "error")
            return redirect(url_for('.forgot_password'))

        # ── STRICT CHECK: only registered counselors / admins may reset ──
        # create_password_reset_token returns None for unknown or blocked users
        result = User.create_password_reset_token(email)

        if not result:
            # Email not found OR account is blocked — tell the user clearly.
            # This is intentional: IMHSS is a closed staff system, not a
            # public app, so we do NOT hide whether the email exists.
            flash(
                "No active counselor or admin account found for that email. "
                "Please check the address or contact your administrator.",
                "error"
            )
            return redirect(url_for('.forgot_password'))

        # ── Email exists and is active — send the reset link ─────────────
        reset_url = url_for(
            '.reset_password',
            token=result['token'],
            _external=True
        )

        try:
            mail = current_app.extensions.get('mail')
            if mail is None:
                raise RuntimeError(
                    "Flask-Mail is not initialised. "
                    "Check MAIL_* environment variables."
                )

            # Read sender identity from .env.
            # CRITICAL: sender email MUST be the same as MAIL_USERNAME
            # (the authenticated Gmail account). Gmail rejects mail sent
            # "from" a different domain than the authenticated account.
            mail_username = os.getenv('MAIL_USERNAME')
            noreply_name = os.getenv('NOREPLY_NAME', 'IMHMS Support')
            # Always use the authenticated Gmail as the actual sender address
            noreply_email = os.getenv('NOREPLY_EMAIL', mail_username)

            msg = Message(
                subject="Reset your IMHMS password",
                recipients=[result['user_email']],
                sender=(noreply_name, noreply_email),
                reply_to=None   # no-reply: suppress reply-to header
            )
            msg.body = (
                f"Hi {result['user_name']},\n\n"
                f"We received a request to reset your IMHMS password.\n\n"
                f"Click the link below to set a new password.\n"
                f"This link expires in 1 hour.\n\n"
                f"{reset_url}\n\n"
                f"If you did not request a password reset, please ignore "
                f"this email.\n\n"
                f"---\n"
                f"IMHMS – Integrated Mental Health Monitoring System\n"
                f"Do not reply to this email."
            )
            mail.send(msg)

            flash(
                f"A password reset link has been sent to {email}. "
                "Check your inbox (and spam folder). The link expires in 1 hour.",
                "success"
            )
            return redirect(url_for('.counselor_login'))

        except Exception as e:
            current_app.logger.error(f"Password reset email error: {e}")
            flash(
                "Your account was found but we could not send the reset email. "
                "Please contact your administrator or try again later.",
                "error"
            )
            return redirect(url_for('.forgot_password'))

    return render_template('forget_password.html')


# --------------------------------------------------
# Reset Password  (GET: validate token + show form |
#                  POST: apply new password)
# --------------------------------------------------
@routes.route('/counselor-admin/reset-password/<token>',
              methods=['GET', 'POST'])
def reset_password(token):
    """
    Password-reset confirmation page.

    GET  — validate the token; if valid render the new-password form,
           otherwise flash an error and redirect to forgot-password.
    POST — validate the token again, apply the new password, redirect
           to login on success.
    """
    # Already logged in? Redirect away.
    if session.get('user_id'):
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('.admin_dashboard'))
        return redirect(url_for('.counselor_dashboard'))

    if request.method == 'GET':
        token_doc = User.verify_reset_token(token)

        if not token_doc:
            flash(
                "This password reset link is invalid or has expired. "
                "Please request a new one.",
                "error"
            )
            return redirect(url_for('.forgot_password'))

        return render_template('reset_password.html', token=token)

    # ── POST ─────────────────────────────────────────────────────
    new_password = request.form.get('new_password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()

    # Validate inputs
    if not new_password:
        flash("Please enter a new password.", "error")
        return redirect(url_for('.reset_password', token=token))

    if len(new_password) < 8:
        flash("Password must be at least 8 characters long.", "error")
        return redirect(url_for('.reset_password', token=token))

    if new_password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for('.reset_password', token=token))

    # Apply reset — re-validates the token inside
    success = User.reset_password_with_token(token, new_password)

    if not success:
        flash(
            "This reset link is invalid or has expired. "
            "Please request a new one.",
            "error"
        )
        return redirect(url_for('.forgot_password'))

    flash(
        "Password reset successfully! You can now log in with your "
        "new password.",
        "success"
    )
    return redirect(url_for('.counselor_login'))


# --------------------------------------------------
# Logout
# --------------------------------------------------
@routes.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out", "success")
    return redirect(url_for('.base'))


# --------------------------------------------------
# Admin Routes
# --------------------------------------------------
@routes.route('/admin/dashboard')
@login_required
@role_required("admin")
def admin_dashboard():
    counselor_count = users.count_documents({'role': 'counselor'})
    student_count = students.count_documents({})
    active_users = users.count_documents({'status': 'active'})

    counselors = list(users.find(
        {'role': 'counselor'},
        {'name': 1, 'email': 1, 'department': 1, 'status': 1}
    ))

    all_students = list(students.find(
        {},
        {'name': 1, 'email': 1, 'matric': 1, 'department': 1,
         'counselor_id': 1, 'token_expires_at': 1, 'token_used': 1,
         'last_login': 1, 'counselor_name': 1, 'access_token': 1}
    ))

    counselor_student_counts = {}
    for counselor in counselors:
        counselor_id = str(counselor['_id'])
        count = students.count_documents({'counselor_id': counselor_id})
        counselor_student_counts[counselor_id] = count
        counselor["capacity_percent"] = int((count / 5) * 100)

    total_messages = messages.estimated_document_count()
    flagged_count = flags.count_documents({'reviewed': False})

    return render_template('admin.html',
                           counselor_count=counselor_count,
                           student_count=student_count,
                           active_users=active_users,
                           counselors=counselors,
                           counselor_student_counts=counselor_student_counts,
                           students=all_students,
                           total_messages=total_messages,
                           flagged_count=flagged_count)


# --------------------------------------------------
# Admin – User Management
# --------------------------------------------------
@routes.route('/admin/create-counselor', methods=['GET', 'POST'])
@login_required
@role_required("admin")
def admin_create_counselor():
    if request.method == 'POST':
        response, status_code = User.counselor_signup()

        if status_code == 201:
            flash("Counselor registered successfully", "success")
            return redirect(url_for('.admin_dashboard'))
        else:
            flash(response.get_json().get('error', 'Registration failed'),
                  "error")
            return redirect(url_for('.admin_create_counselor'))

    return render_template('register-counselor.html')


@routes.route('/admin/toggle-user-status', methods=['POST'])
@login_required
@role_required("admin")
def admin_toggle_user_status():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Access denied. Admin only.", "error")
        return redirect(url_for('.counselor_login'))

    user_id = request.form.get('user_id')
    user = users.find_one({'_id': user_id})

    if not user:
        flash("User not found", "error")
        return redirect(url_for('.admin_dashboard'))

    if user['role'] == 'admin':
        flash("Cannot block admin users", "error")
        return redirect(url_for('.admin_dashboard'))

    new_status = 'blocked' if user.get('status') == 'active' else 'active'
    users.update_one({'_id': user_id}, {'$set': {'status': new_status}})

    flash(f"User {user['name']} has been {new_status}", "success")
    return redirect(url_for('.admin_dashboard'))


# --------------------------------------------------
# Admin – Messages (privacy-protected)
# --------------------------------------------------
@routes.route('/admin/messages')
@login_required
@role_required("admin")
def admin_view_all_messages():
    flash(
        "Student chat history is private. "
        "Only flagged messages are accessible for review.",
        "info"
    )
    return redirect(url_for('.admin_view_all_flags'))


@routes.route('/admin/flags')
@login_required
@role_required("admin")
def admin_view_all_flags():
    page = request.args.get('page', 1, type=int)
    per_page = 50

    skip = (page - 1) * per_page
    all_flags = list(flags.find().sort('flagged_at', -1)
                     .skip(skip).limit(per_page))

    student_ids = list(set([f['student_id'] for f in all_flags]))
    message_ids = list(set([f['message_id'] for f in all_flags]))
    counselor_ids = list(set([f['counselor_id'] for f in all_flags]))

    student_map = {s['_id']: s for s in students.find(
        {'_id': {'$in': student_ids}})}
    message_map = {m['_id']: m for m in messages.find(
        {'_id': {'$in': message_ids}})}
    counselor_map = {u['_id']: u for u in users.find(
        {'_id': {'$in': counselor_ids}})}

    for flag in all_flags:
        flag['student'] = student_map.get(flag['student_id'])
        flag['message'] = message_map.get(flag['message_id'])
        flag['counselor'] = counselor_map.get(flag['counselor_id'])

    total = flags.estimated_document_count()

    return render_template('admin_flags.html',
                           flags=all_flags,
                           page=page,
                           total_pages=(total + per_page - 1) // per_page)


# --------------------------------------------------
# Counselor Routes
# --------------------------------------------------
@routes.route('/counselor/dashboard')
@login_required
@role_required("counselor")
def counselor_dashboard():
    counselor_id = session.get('user_id')
    now = datetime.datetime.utcnow()

    my_students = list(students.find(
        {'counselor_id': counselor_id},
        {
            'name': 1, 'email': 1, 'matric': 1, 'department': 1,
            'token_expires_at': 1, 'access_token': 1, 'token_used': 1
        }
    ))

    for student in my_students:
        token_expires_at = student.get('token_expires_at')
        if token_expires_at:
            student['token_expired'] = now > token_expires_at
            student['days_until_expiry'] = (
                (token_expires_at - now).days
                if now < token_expires_at else 0
            )
        else:
            student['token_expired'] = True
            student['days_until_expiry'] = 0

    my_students_count = len(my_students)
    student_ids = [s['_id'] for s in my_students]

    total_messages_count = messages.count_documents(
        {'student_id': {'$in': student_ids}})

    high_risk_flags = list(flags.find({
        'counselor_id': counselor_id,
        'reviewed': False,
        'risk_level': 'high'
    }).sort('flagged_at', -1).limit(20))

    medium_risk_flags = list(flags.find({
        'counselor_id': counselor_id,
        'reviewed': False,
        'risk_level': 'medium'
    }).sort('flagged_at', -1).limit(20))

    flag_student_ids = list(
        set([f['student_id'] for f in high_risk_flags + medium_risk_flags]))
    flag_message_ids = list(
        set([f['message_id'] for f in high_risk_flags + medium_risk_flags]))

    flag_students = {s['_id']: s for s in students.find(
        {'_id': {'$in': flag_student_ids}})}
    flag_messages = {m['_id']: m for m in messages.find(
        {'_id': {'$in': flag_message_ids}})}

    for flag in high_risk_flags + medium_risk_flags:
        flag['student'] = flag_students.get(flag['student_id'])
        flag['message'] = flag_messages.get(flag['message_id'])

    flagged_student_ids = list(set(
        [f['student_id'] for f in
         list(flags.find({'counselor_id': counselor_id},
                         {'student_id': 1}))]
    ))
    messageable_students = list(students.find(
        {'_id': {'$in': flagged_student_ids},
         'counselor_id': counselor_id},
        {'name': 1, 'email': 1}
    ))

    sent_messages = list(counselor_messages.find(
        {'counselor_id': counselor_id}
    ).sort('sent_at', -1).limit(50))

    return render_template('counselor.html',
                           my_students_count=my_students_count,
                           my_students=my_students,
                           high_risk_flags=high_risk_flags,
                           medium_risk_flags=medium_risk_flags,
                           flagged_messages_count=(
                               len(high_risk_flags) + len(medium_risk_flags)
                           ),
                           total_messages_count=total_messages_count,
                           messageable_students=messageable_students,
                           sent_messages=sent_messages)


# --------------------------------------------------
# Counselor – Student Management
# --------------------------------------------------
@routes.route('/counselor/create-student', methods=['GET', 'POST'])
@login_required
@role_required("counselor")
def counselor_create_student():
    counselor_id = session.get('user_id')
    counselor_record = users.find_one({'_id': counselor_id}, {'name': 1})

    if not counselor_record:
        flash("Counselor not found", "error")
        return redirect(url_for('.counselor_dashboard'))

    counselor_name = counselor_record.get('name')

    if request.method == 'POST':
        response, status_code = User.student_signup()

        if status_code == 201:
            data = response.get_json()
            access_token = data.get('access_token')

            students.update_one(
                {'access_token': access_token},
                {'$set': {'counselor_id': counselor_id,
                          'counselor_name': counselor_name}}
            )

            flash(
                f"Student registered! Token: {access_token} "
                f"(Expires in 7 days)",
                "success"
            )
            return redirect(url_for('.counselor_dashboard'))
        else:
            flash(response.get_json().get('error', 'Registration failed'),
                  "error")
            return redirect(url_for('.counselor_create_student'))

    return render_template('register-student.html')


@routes.route('/counselor/student/<student_id>/regenerate-token',
              methods=['POST'])
@login_required
@role_required("counselor")
def counselor_regenerate_token(student_id):
    counselor_id = session.get('user_id')

    student = students.find_one({
        '_id': student_id,
        'counselor_id': counselor_id
    }, {'name': 1, 'email': 1})

    if not student:
        flash("Student not found or not assigned to you", "error")
        return redirect(url_for('.counselor_dashboard'))

    result = User.regenerate_student_token(student_id)

    if result:
        flash(
            f"New token generated for {student['name']}: "
            f"{result['token']} (Valid for 7 days)",
            "success"
        )
    else:
        flash("Failed to regenerate token", "error")

    return redirect(url_for('.counselor_dashboard'))


# --------------------------------------------------
# Counselor – View Flagged Student Messages ONLY
# --------------------------------------------------
@routes.route('/counselor/student/<student_id>/flagged-messages')
@login_required
@role_required("counselor")
def counselor_view_student_messages(student_id):
    counselor_id = session.get('user_id')
    page = request.args.get('page', 1, type=int)
    per_page = 50

    student = students.find_one({
        '_id': student_id,
        'counselor_id': counselor_id
    })

    if not student:
        flash("Student not found or not assigned to you", "error")
        return redirect(url_for('.counselor_dashboard'))

    skip = (page - 1) * per_page
    student_flags = list(flags.find({
        'student_id': student_id,
        'counselor_id': counselor_id
    }).sort('flagged_at', -1).skip(skip).limit(per_page))

    message_ids = [f['message_id'] for f in student_flags]
    message_map = {
        m['_id']: m for m in messages.find({'_id': {'$in': message_ids}})
    }

    for flag in student_flags:
        flag['message'] = message_map.get(flag['message_id'])

    total_flags = flags.count_documents({
        'student_id': student_id,
        'counselor_id': counselor_id
    })

    return render_template('counselor_student_messages.html',
                           student=student,
                           flags=student_flags,
                           page=page,
                           total_pages=(total_flags + per_page - 1)
                           // per_page)


# --------------------------------------------------
# Counselor – Review Flag
# --------------------------------------------------
@routes.route('/counselor/flag/<flag_id>/review', methods=['POST'])
@login_required
@role_required("counselor")
def counselor_review_flag(flag_id):
    counselor_id = session.get('user_id')
    notes = request.form.get('notes', '')

    result = flags.update_one(
        {'_id': flag_id, 'counselor_id': counselor_id},
        {
            '$set': {
                'reviewed': True,
                'reviewed_at': datetime.datetime.utcnow(),
                'reviewed_by': counselor_id,
                'notes': notes
            }
        }
    )

    if result.modified_count > 0:
        flash("Flag marked as reviewed", "success")
    else:
        flash("Flag not found", "error")

    return redirect(url_for('.counselor_dashboard'))


# --------------------------------------------------
# Counselor – Send Private Email to Student
# Admin has no route that touches counselor_messages.
# --------------------------------------------------
@routes.route('/counselor/send-message', methods=['POST'])
@login_required
@role_required("counselor")
def counselor_send_message():
    counselor_id = session.get('user_id')
    counselor_name = session.get('name', 'Your Counselor')
    counselor_email = session.get('email')

    student_id = request.form.get('student_id', '').strip()
    subject = request.form.get('subject', '').strip()
    body = request.form.get('body', '').strip()

    if not student_id:
        flash("Please select a student.", "error")
        return redirect(url_for('.counselor_dashboard') + '#messages')

    if not subject:
        flash("Subject cannot be empty.", "error")
        return redirect(url_for('.counselor_dashboard') + '#messages')

    if not body:
        flash("Message body cannot be empty.", "error")
        return redirect(url_for('.counselor_dashboard') + '#messages')

    if len(subject) > 200:
        flash("Subject must be 200 characters or fewer.", "error")
        return redirect(url_for('.counselor_dashboard') + '#messages')

    if len(body) > 4000:
        flash("Message body must be 4,000 characters or fewer.", "error")
        return redirect(url_for('.counselor_dashboard') + '#messages')

    student = students.find_one({
        '_id': student_id,
        'counselor_id': counselor_id
    }, {'name': 1, 'email': 1})

    if not student:
        flash("Student not found or not assigned to you.", "error")
        return redirect(url_for('.counselor_dashboard') + '#messages')

    has_flag = flags.find_one({
        'student_id': student_id,
        'counselor_id': counselor_id
    })
    if not has_flag:
        flash("You can only message students who have a flagged message.",
              "error")
        return redirect(url_for('.counselor_dashboard') + '#messages')

    student_name = student.get('name', 'Student')
    student_email = student.get('email')

    if not student_email:
        flash("This student has no email address on record.", "error")
        return redirect(url_for('.counselor_dashboard') + '#messages')

    email_status = "failed"
    try:
        mail = current_app.extensions.get('mail')
        if mail is None:
            raise RuntimeError("Flask-Mail is not initialised.")

        mail_username = os.getenv('MAIL_USERNAME')
        noreply_name = os.getenv('NOREPLY_NAME', 'IMHMS Support')
        noreply_email = os.getenv('NOREPLY_EMAIL', mail_username)

        msg = Message(
            subject=subject,
            recipients=[student_email],
            sender=(noreply_name, noreply_email)
        )
        msg.body = (
            f"Dear {student_name},\n\n"
            f"{body}\n\n"
            f"---\n"
            f"This is an automated system message from your counselor, "
            f"{counselor_name}.\n"
            f"This mailbox is not monitored. Please contact your counselor "
            f"directly.\n\n"
            f"IMHMS support team"
        )
        mail.send(msg)
        email_status = "sent"

    except Exception as e:
        current_app.logger.error(f"Email send error: {e}")
        flash(
            "Message saved but could not be delivered by email. "
            "Please check your mail server settings.",
            "warning"
        )

    counselor_messages.insert_one({
        "_id": str(uuid.uuid4()),
        "counselor_id":    counselor_id,
        "counselor_name":  counselor_name,
        "counselor_email": counselor_email,
        "student_id":      student_id,
        "student_name":    student_name,
        "student_email":   student_email,
        "subject":         subject,
        "body":            body,
        "sent_at":         datetime.datetime.utcnow(),
        "email_status":    email_status
    })

    if email_status == "sent":
        flash(f"Message sent successfully to {student_name}.", "success")

    return redirect(url_for('.counselor_dashboard') + '#messages')


# --------------------------------------------------
# Counselor – Change Password (while logged in)
# --------------------------------------------------
@routes.route('/counselor/change-password', methods=['POST'])
@role_required('counselor')
def change_password():
    """Change counselor password — requires current password verification."""
    counselor_id = session.get('user_id')

    current_password = request.form.get('current_password', '').strip()
    new_password = request.form.get('new_password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()

    if not current_password:
        flash("Please enter your current password.", "error")
        return redirect(url_for('.counselor_dashboard') + '#password')

    if not new_password:
        flash("Please enter a new password.", "error")
        return redirect(url_for('.counselor_dashboard') + '#password')

    if not confirm_password:
        flash("Please confirm your new password.", "error")
        return redirect(url_for('.counselor_dashboard') + '#password')

    if len(new_password) < 8:
        flash("New password must be at least 8 characters long.", "error")
        return redirect(url_for('.counselor_dashboard') + '#password')

    if new_password != confirm_password:
        flash("New passwords do not match.", "error")
        return redirect(url_for('.counselor_dashboard') + '#password')

    if current_password == new_password:
        flash("New password must be different from current password.", "error")
        return redirect(url_for('.counselor_dashboard') + '#password')

    counselor = users.find_one({'_id': counselor_id})

    if not counselor:
        flash("Counselor not found.", "error")
        return redirect(url_for('.counselor_dashboard') + '#password')

    if not check_password_hash(counselor['hashed_password'], current_password):
        flash("Current password is incorrect.", "error")
        return redirect(url_for('.counselor_dashboard') + '#password')

    try:
        new_hashed_password = generate_password_hash(new_password,
                                                     method='pbkdf2')
        result = users.update_one(
            {'_id': counselor_id},
            {
                '$set': {
                    'hashed_password':    new_hashed_password,
                    'password_updated_at': datetime.datetime.utcnow()
                }
            }
        )

        if result.modified_count > 0:
            flash("Password changed successfully!", "success")
            logs.insert_one({
                '_id':        str(uuid.uuid4()),
                'user_id':    counselor_id,
                'action':     'password_changed',
                'timestamp':  datetime.datetime.utcnow(),
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent')
            })
        else:
            flash("Failed to update password. Please try again.", "error")

    except Exception as e:
        current_app.logger.error(f"Password change error: {e}")
        flash("An error occurred while changing password.", "error")

    return redirect(url_for('.counselor_dashboard') + '#password')


# --------------------------------------------------
# Student Routes
# --------------------------------------------------
@routes.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        result = User.student_login()

        if not result:
            flash("Invalid access token", "error")
            return redirect(url_for('.student_login'))

        if isinstance(result, dict) and result.get('expired'):
            flash(
                "Your access token has expired. Please contact your counselor "
                "for a new token.",
                "error"
            )
            return redirect(url_for('.student_login'))

        student_record = result
        timestamp = datetime.datetime.utcnow()

        students.update_one(
            {'access_token': student_record['access_token']},
            {'$set': {"token_used": True, "last_login": timestamp}}
        )

        session.clear()
        session["student_id"] = str(student_record["_id"])
        session["role"] = student_record.get("role")
        session["student_name"] = student_record.get("name")
        session["name"] = student_record.get("name")
        flash("Login successful", "success")
        return redirect(url_for('.student_dashboard'))

    return render_template('student_login.html')


@routes.route('/student/dashboard')
@student_required
def student_dashboard():
    student_id = session.get('student_id')
    student = students.find_one({'_id': student_id})

    if not student:
        flash("Student not found", "error")
        session.clear()
        return redirect(url_for('.student_login'))

    return render_template('student.html')


@routes.route('/student/chat/send', methods=['POST'])
@student_required
def student_chat_send():
    return send_message()


@routes.route('/student/chat/history', methods=['GET'])
@student_required
def student_chat_history():
    student_id = session.get('student_id')
    page = request.args.get('page',     1,  type=int)
    per_page = request.args.get('per_page', 50, type=int)
    skip = (page - 1) * per_page

    chat_history = list(messages.find(
        {'student_id': student_id},
        {'_id': 1, 'content': 1, 'ai_response': 1,
         'timestamp': 1, 'session_id': 1}
    ).sort('timestamp', 1).skip(skip).limit(per_page))

    formatted_messages = []
    for msg in chat_history:
        formatted_messages.append({
            'message_id': msg['_id'],
            'content':    msg['content'],
            'ai_response': msg['ai_response'],
            'timestamp':  msg['timestamp'].isoformat(),
            'session_id': msg.get('session_id')
        })

    total_count = messages.count_documents({'student_id': student_id})

    return jsonify({
        'success':   True,
        'messages':  formatted_messages,
        'page':      page,
        'per_page':  per_page,
        'total':     total_count,
        'has_more':  (skip + per_page) < total_count
    })


# --------------------------------------------------
# Counselor – Notifications
# --------------------------------------------------
@routes.route('/counselor/check-notifications')
@login_required
@role_required("counselor")
def check_notifications():
    counselor_id = session.get('user_id')

    unreviewed_count = flags.count_documents({
        'counselor_id': counselor_id,
        'reviewed': False
    })

    latest_flags = list(flags.find({
        'counselor_id': counselor_id,
        'reviewed': False
    }, {
        'student_id': 1, 'risk_level': 1,
        'flagged_at': 1, 'detected_keywords': 1
    }).sort('flagged_at', -1).limit(3))

    student_ids = [f['student_id'] for f in latest_flags]
    student_map = {s['_id']: s['name'] for s in students.find(
        {'_id': {'$in': student_ids}}, {'name': 1}
    )}

    for flag in latest_flags:
        flag['student_name'] = student_map.get(flag['student_id'], 'Unknown')

    return jsonify({
        'count': unreviewed_count,
        'flags': [{
            'student_name': flag['student_name'],
            'risk_level':   flag.get('risk_level', 'high'),
            'flagged_at':   flag['flagged_at'].isoformat(),
            'keywords':     flag['detected_keywords']
        } for flag in latest_flags]
    })

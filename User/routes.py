# User/routes.py - Optimized Application Routes with Token Expiration
import datetime
from flask import render_template, request, redirect, url_for, flash
from flask import session, Blueprint, jsonify
from werkzeug.security import check_password_hash
from .models import User
from .database import users, students, messages, flags
from .auth import role_required, login_required, student_required
from .chat import send_message


routes = Blueprint('IMHSS', __name__, template_folder='templates',
                   static_folder='static')


# --------------------------------------------------
# Landing Page
# --------------------------------------------------
@routes.route('/')
def base():
    """Main landing page"""
    return render_template('base.html')


# --------------------------------------------------
# Counselor/Admin Authentication
# --------------------------------------------------
@routes.route('/counselor-admin/login', methods=['GET', 'POST'])
def counselor_login():
    """Handles counselor and admin login with optimized queries"""
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
# Logout
# --------------------------------------------------
@routes.route('/logout')
def logout():
    """Log out current user and clear session"""
    session.clear()
    flash("You have been logged out", "success")
    return redirect(url_for('.base'))


# --------------------------------------------------
# Admin Routes (Optimized)
# --------------------------------------------------
@routes.route('/admin/dashboard')
@login_required
@role_required("admin")
def admin_dashboard():
    """Optimized admin dashboard with efficient queries"""
    # Use count_documents with filter for better performance
    counselor_count = users.count_documents({'role': 'counselor'})
    student_count = students.count_documents({})
    active_users = users.count_documents({'status': 'active'})

    # Get counselors with only needed fields (projection)
    counselors = list(users.find(
        {'role': 'counselor'},
        {'name': 1, 'email': 1, 'department': 1, 'status': 1}
    ))

    # Get students with only needed fields
    all_students = list(students.find(
        {},
        {'name': 1, 'email': 1, 'matric': 1, 'department': 1,
         'counselor_id': 1, 'token_expires_at': 1}
    ))

    # Efficient aggregation for student counts
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
    """Block or unblock a user"""
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
# Counselor Routes (Optimized with Token Management)
# --------------------------------------------------
@routes.route('/counselor/dashboard')
@login_required
@role_required("counselor")
def counselor_dashboard():
    """Optimized counselor dashboard with token expiration info"""
    counselor_id = session.get('user_id')
    now = datetime.datetime.utcnow()

    # Get students with only needed fields + expiration status
    my_students = list(students.find(
        {'counselor_id': counselor_id},
        {
            'name': 1, 'email': 1, 'matric': 1, 'department': 1,
            'token_expires_at': 1, 'access_token': 1, 'token_used': 1
        }
    ))

    # Add expiration status to each student
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

    # Efficient message count
    total_messages_count = messages.count_documents(
        {'student_id': {'$in': student_ids}})

    # Get HIGH and MEDIUM risk flags efficiently
    high_risk_flags = list(flags.find({
        'counselor_id': counselor_id,
        'reviewed': False,
        'risk_level': 'high'
    }).sort('flagged_at', -1).limit(20))  # Limit for performance

    medium_risk_flags = list(flags.find({
        'counselor_id': counselor_id,
        'reviewed': False,
        'risk_level': 'medium'
    }).sort('flagged_at', -1).limit(20))  # Limit for performance

    # Batch fetch student and message data (more efficient than loop)
    flag_student_ids = list(
        set([f['student_id'] for f in high_risk_flags + medium_risk_flags]))
    flag_message_ids = list(
        set([f['message_id'] for f in high_risk_flags + medium_risk_flags]))

    flag_students = {s['_id']: s for s in students.find(
        {'_id': {'$in': flag_student_ids}})}
    flag_messages = {m['_id']: m for m in messages.find(
        {'_id': {'$in': flag_message_ids}})}

    # Enrich flags with data
    for flag in high_risk_flags + medium_risk_flags:
        flag['student'] = flag_students.get(flag['student_id'])
        flag['message'] = flag_messages.get(flag['message_id'])

    return render_template('counselor.html',
                           my_students_count=my_students_count,
                           my_students=my_students,
                           high_risk_flags=high_risk_flags,
                           medium_risk_flags=medium_risk_flags,
                           flagged_messages_count=(
                               len(high_risk_flags) +
                               len(medium_risk_flags)
                           ),
                           total_messages_count=total_messages_count)


@routes.route('/counselor/create-student', methods=['GET', 'POST'])
@login_required
@role_required("counselor")
def counselor_create_student():
    """Create student with 7-day token expiration"""
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

            # Update student to assign counselor
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
    """
    NEW: Regenerate access token for a student (7-day expiration)
    Only allowed for students assigned to this counselor
    """
    counselor_id = session.get('user_id')

    # Verify student belongs to this counselor
    student = students.find_one({
        '_id': student_id,
        'counselor_id': counselor_id
    }, {'name': 1, 'email': 1})

    if not student:
        flash("Student not found or not assigned to you", "error")
        return redirect(url_for('.counselor_dashboard'))

    # Regenerate token
    result = User.regenerate_student_token(student_id)

    if result:
        flash(
            (
                f"New token generated for {student['name']}: "
                f"{result['token']} (Valid for 7 days)"
            ),
            "success"
        )
    else:
        flash("Failed to regenerate token", "error")

    return redirect(url_for('.counselor_dashboard'))


# --------------------------------------------------
# Student Routes (With Token Expiration Check)
# --------------------------------------------------
@routes.route('/student/login', methods=['GET', 'POST'])
def student_login():
    """Student login with token expiration validation"""
    if request.method == 'POST':
        result = User.student_login()

        if not result:
            flash("Invalid access token", "error")
            return redirect(url_for('.student_login'))

        # Check if token expired
        if isinstance(result, dict) and result.get('expired'):
            flash(
                "Your access token has expired. Please contact your counselor "
                "for a new token.",
                "error"
            )
            return redirect(url_for('.student_login'))

        student_record = result
        timestamp = datetime.datetime.utcnow()

        # Update token usage and last login
        students.update_one(
            {'access_token': student_record['access_token']},
            {'$set': {"token_used": True, "last_login": timestamp}}
        )

        # Set session
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
    """Student dashboard"""
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
    """Student sends a message to AI chatbot"""
    return send_message()


@routes.route('/student/chat/history', methods=['GET'])
@student_required
def student_chat_history():
    """
    Fetch student's chat history (OPTIMIZED with pagination)
    """
    student_id = session.get('student_id')
    page = request.args.get('page', 1, type=int)
    # Limit to 50 messages per page for performance; can be adjusted as needed
    per_page = request.args.get('per_page', 50, type=int)

    # Calculate skip
    skip = (page - 1) * per_page

    # Get paginated messages
    chat_history = list(messages.find(
        {'student_id': student_id},
        {'_id': 1, 'content': 1, 'ai_response': 1,
         'timestamp': 1, 'session_id': 1}
    ).sort('timestamp', 1).skip(skip).limit(per_page))

    # Format messages
    formatted_messages = []
    for msg in chat_history:
        formatted_messages.append({
            'message_id': msg['_id'],
            'content': msg['content'],
            'ai_response': msg['ai_response'],
            'timestamp': msg['timestamp'].isoformat(),
            'session_id': msg.get('session_id')
        })

    # Get total count for pagination info
    total_count = messages.count_documents({'student_id': student_id})

    return jsonify({
        'success': True,
        'messages': formatted_messages,
        'page': page,
        'per_page': per_page,
        'total': total_count,
        'has_more': (skip + per_page) < total_count
    })


# --------------------------------------------------
# Counselor - View Student Messages (Optimized)
# --------------------------------------------------
@routes.route('/counselor/student/<student_id>/messages')
@login_required
@role_required("counselor")
def counselor_view_student_messages(student_id):
    """View messages with pagination"""
    counselor_id = session.get('user_id')
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Verify student belongs to counselor
    student = students.find_one({
        '_id': student_id,
        'counselor_id': counselor_id
    })

    if not student:
        flash("Student not found or not assigned to you", "error")
        return redirect(url_for('.counselor_dashboard'))

    # Get paginated messages
    skip = (page - 1) * per_page
    student_messages = list(messages.find({
        'student_id': student_id
    }).sort('timestamp', -1).skip(skip).limit(per_page))

    # Get total for pagination
    total_messages = messages.count_documents({'student_id': student_id})
    flagged_count = flags.count_documents({
        'student_id': student_id, 'reviewed': False
        })

    return render_template('counselor_student_messages.html',
                           student=student,
                           messages=student_messages,
                           flagged_count=flagged_count,
                           page=page,
                           total_pages=(total_messages + per_page - 1)
                           // per_page)


@routes.route('/counselor/flag/<flag_id>/review', methods=['POST'])
@login_required
@role_required("counselor")
def counselor_review_flag(flag_id):
    """Mark a flag as reviewed"""
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
# Admin - View Messages/Flags (With Pagination)
# --------------------------------------------------
@routes.route('/admin/messages')
@login_required
@role_required("admin")
def admin_view_all_messages():
    """View messages with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 50

    skip = (page - 1) * per_page
    all_messages = list(
        messages.find()
        .sort('timestamp', -1)
        .skip(skip)
        .limit(per_page)
    )

    # Batch fetch student data
    student_ids = list(set([msg['student_id'] for msg in all_messages]))
    student_map = {s['_id']: s for s in students.find({
        '_id': {'$in': student_ids}
        })}

    for msg in all_messages:
        msg['student'] = student_map.get(msg['student_id'])

    total = messages.estimated_document_count()

    return render_template('admin_messages.html',
                           messages=all_messages,
                           page=page,
                           total_pages=(total + per_page - 1) // per_page)


@routes.route('/admin/flags')
@login_required
@role_required("admin")
def admin_view_all_flags():
    """View flags with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 50

    skip = (page - 1) * per_page
    all_flags = list(flags.find().sort('flagged_at', -1)
                     .skip(skip).limit(per_page))

    # Batch fetch related data
    student_ids = list(set([f['student_id'] for f in all_flags]))
    message_ids = list(set([f['message_id'] for f in all_flags]))
    counselor_ids = list(set([f['counselor_id'] for f in all_flags]))

    student_map = {s['_id']: s for s in students.find({
        '_id': {'$in': student_ids}
        })}
    message_map = {m['_id']: m for m in messages.find({
        '_id': {'$in': message_ids}
        })}
    counselor_map = {u['_id']: u for u in users.find({
        '_id': {'$in': counselor_ids}
        })}

    for flag in all_flags:
        flag['student'] = student_map.get(flag['student_id'])
        flag['message'] = message_map.get(flag['message_id'])
        flag['counselor'] = counselor_map.get(flag['counselor_id'])

    total = flags.estimated_document_count()

    return render_template('admin_flags.html',
                           flags=all_flags,
                           page=page,
                           total_pages=(total + per_page - 1) // per_page)


@routes.route('/counselor/check-notifications')
@login_required
@role_required("counselor")
def check_notifications():
    """Check for new flags (optimized)"""
    counselor_id = session.get('user_id')

    unreviewed_count = flags.count_documents({
        'counselor_id': counselor_id,
        'reviewed': False
    })

    latest_flags = list(flags.find({
        'counselor_id': counselor_id,
        'reviewed': False
    }, {
        'student_id': 1,
        'risk_level': 1,
        'flagged_at': 1,
        'detected_keywords': 1
    }).sort('flagged_at', -1).limit(3))

    # Batch fetch student names
    student_ids = [f['student_id'] for f in latest_flags]
    student_map = {s['_id']: s['name'] for s in students.find(
        {'_id': {'$in': student_ids}},
        {'name': 1}
    )}

    for flag in latest_flags:
        flag['student_name'] = student_map.get(flag['student_id'], 'Unknown')

    return jsonify({
        'count': unreviewed_count,
        'flags': [{
            'student_name': flag['student_name'],
            'risk_level': flag.get('risk_level', 'high'),
            'flagged_at': flag['flagged_at'].isoformat(),
            'keywords': flag['detected_keywords']
        } for flag in latest_flags]
    })

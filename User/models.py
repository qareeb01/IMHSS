# User/models.py - User Models with Token Expiration and Password Reset
import secrets
import string
import datetime
import uuid
from flask import jsonify, request
from werkzeug.security import generate_password_hash as gph
from .database import users, students, password_reset_tokens, logs


class User:

    @staticmethod
    def counselor_signup():
        """Register a new counselor. Returns JSON response with status."""
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            department = request.form.get('department')

            if not all([name, email, password, department]):
                return jsonify({"error": "All fields are required"}), 400

            if users.find_one({"email": email}):
                return jsonify({"error": "Email already exists"}), 400

            hashed_password = gph(password, method="pbkdf2")

            counselor_data = {
                "_id": uuid.uuid4().hex,
                "name": name,
                "email": email,
                "hashed_password": hashed_password,
                "role": "counselor",
                "department": department,
                "status": "active",
                "created_at": datetime.datetime.utcnow()
            }

            users.insert_one(counselor_data)
            return jsonify({"message": "Counselor registered successfully",
                            "data": {"name": name, "email": email}}), 201

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def student_signup():
        """Register a new student with 7-day token expiration."""
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            parent_name = request.form.get('parent_name')
            hostel_hall = request.form.get('hall')
            phone = request.form.get('phone')
            parent_contact = request.form.get('parent_contact')
            department = request.form.get('department')
            gender = request.form.get('gender')
            matric = request.form.get('matric')
            room_number = request.form.get('room_number')

            if not all([name, email, parent_name, parent_contact, hostel_hall,
                        phone, department, matric, room_number]):
                return jsonify({"error": "All fields are required"}), 400

            if students.find_one({"email": email}):
                return jsonify({"error": "Email already exists"}), 400

            alphabet = string.ascii_uppercase + string.digits
            access_token = ''.join(secrets.choice(alphabet) for _ in range(8))

            token_created_at = datetime.datetime.utcnow()
            token_expires_at = token_created_at + datetime.timedelta(days=7)

            student_data = {
                "_id": uuid.uuid4().hex,
                "name": name,
                "email": email,
                "parent_name": parent_name,
                "parent_contact": parent_contact,
                "hostel_hall": hostel_hall,
                "room_number": room_number,
                "phone": phone,
                "department": department,
                "matric": matric,
                "role": "student",
                "gender": gender,
                "access_token": access_token,
                "token_used": False,
                "token_created_at": token_created_at,
                "token_expires_at": token_expires_at,
                "registered_at": datetime.datetime.utcnow()
            }

            students.insert_one(student_data)
            return jsonify({
                "message": "Student registered successfully",
                "access_token": access_token,
                "expires_at": token_expires_at.isoformat()
            }), 201

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def counselor_admin_login():
        """Authenticate counselor or admin. Returns user record or None."""
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            user_record = users.find_one({'email': email})

            if not user_record:
                return None, None, None

            return user_record, email, password

        except Exception as e:
            print(f"Login error: {e}")
            return None, None, None

    @staticmethod
    def student_login():
        """Authenticate student using token with expiration check."""
        try:
            token = request.form.get('token')

            if not token:
                return None

            student_record = students.find_one({"access_token": token})

            if not student_record:
                return None

            token_expires_at = student_record.get('token_expires_at')
            current_time = datetime.datetime.utcnow()
            if token_expires_at and current_time > token_expires_at:
                return {"expired": True, "student": student_record}

            return student_record

        except Exception as e:
            print(f"Student login error: {e}")
            return None

    @staticmethod
    def regenerate_student_token(student_id):
        """Generate a new access token for a student (7-day expiration)."""
        try:
            alphabet = string.ascii_uppercase + string.digits
            new_token = ''.join(secrets.choice(alphabet) for _ in range(8))

            token_created_at = datetime.datetime.utcnow()
            token_expires_at = token_created_at + datetime.timedelta(days=7)

            result = students.update_one(
                {"_id": student_id},
                {
                    "$set": {
                        "access_token": new_token,
                        "token_used": False,
                        "token_created_at": token_created_at,
                        "token_expires_at": token_expires_at
                    }
                }
            )

            if result.modified_count > 0:
                return {
                    "token": new_token,
                    "expires_at": token_expires_at.isoformat()
                }

            return None

        except Exception as e:
            print(f"Token regeneration error: {e}")
            return None

    # ------------------------------------------------------------------
    # PASSWORD RESET
    # ------------------------------------------------------------------

    @staticmethod
    def create_password_reset_token(email: str):
        """
        Initiate a password reset for a counselor or admin.

        - Looks up the user by email.
        - Invalidates any previous unused tokens for that email so only
          the newest link works (prevents token accumulation).
        - Generates a cryptographically secure URL-safe token valid for
          1 hour and stores it in password_reset_tokens.

        Args:
            email: The email address submitted on the forgot-password form.

        Returns:
            dict with keys 'token', 'user_name', 'user_email' if the email
            matches a known user — or None if no match (caller should NOT
            reveal this to the form to prevent email enumeration).
        """
        try:
            user = users.find_one(
                {'email': email},
                {'_id': 1, 'name': 1, 'email': 1, 'role': 1, 'status': 1}
            )

            if not user:
                return None   # silently return — caller shows generic message

            if user.get('status') == 'blocked':
                return None   # blocked accounts cannot reset password

            # Invalidate any existing unused tokens for this email
            password_reset_tokens.update_many(
                {'email': email, 'used': False},
                {'$set': {'used': True}}
            )

            # Generate a 48-byte URL-safe token (64 chars after base64)
            raw_token = secrets.token_urlsafe(48)
            now = datetime.datetime.utcnow()

            token_doc = {
                "_id": uuid.uuid4().hex,
                "user_id": str(user['_id']),
                "email": email,
                "token": raw_token,
                "created_at": now,
                "expires_at": now + datetime.timedelta(hours=1),
                "used": False
            }

            password_reset_tokens.insert_one(token_doc)

            return {
                "token": raw_token,
                "user_name": user.get('name', 'User'),
                "user_email": email
            }

        except Exception as e:
            print(f"create_password_reset_token error: {e}")
            return None

    @staticmethod
    def verify_reset_token(token: str):
        """
        Verify that a password reset token is valid and not expired.

        Does NOT consume the token — call reset_password_with_token()
        for that. This is used by the GET handler to pre-validate before
        rendering the reset form.

        Returns:
            token document (dict) if valid, None otherwise.
        """
        try:
            now = datetime.datetime.utcnow()
            token_doc = password_reset_tokens.find_one({
                'token': token,
                'used': False,
                'expires_at': {'$gt': now}
            })
            return token_doc

        except Exception as e:
            print(f"verify_reset_token error: {e}")
            return None

    @staticmethod
    def reset_password_with_token(token: str, new_password: str):
        """
        Consume a reset token and update the user's password.

        Steps:
          1. Find a valid (unused, unexpired) token document.
          2. Find the corresponding user.
          3. Hash and set the new password.
          4. Mark the token as used so it cannot be replayed.
          5. Log the password-reset event in activity_logs.

        Args:
            token:        The raw token string from the URL.
            new_password: The plaintext new password from the form.

        Returns:
            True on success, False on any failure.
        """
        try:

            now = datetime.datetime.utcnow()

            # 1. Find valid token
            token_doc = password_reset_tokens.find_one({
                'token': token,
                'used': False,
                'expires_at': {'$gt': now}
            })

            if not token_doc:
                return False

            user_id = token_doc['user_id']

            # 2. Find user
            user = users.find_one({'_id': user_id})
            if not user:
                return False

            # 3. Hash new password and update
            new_hash = gph(new_password, method='pbkdf2')
            result = users.update_one(
                {'_id': user_id},
                {'$set': {
                    'hashed_password': new_hash,
                    'password_updated_at': now
                }}
            )

            if result.modified_count == 0:
                return False

            # 4. Mark token consumed
            password_reset_tokens.update_one(
                {'_id': token_doc['_id']},
                {'$set': {'used': True, 'used_at': now}}
            )

            # 5. Audit log
            logs.insert_one({
                '_id': uuid.uuid4().hex,
                'user_id': user_id,
                'action': 'password_reset_via_email',
                'email': token_doc['email'],
                'timestamp': now
            })

            return True

        except Exception as e:
            print(f"reset_password_with_token error: {e}")
            return False

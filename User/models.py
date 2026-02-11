# User/models.py - Optimized User Models with Token Expiration
import secrets
import string
from flask import jsonify, request
from werkzeug.security import generate_password_hash
import datetime
import uuid
from .database import users, students


class User:

    @staticmethod
    def counselor_signup():
        """
        Register a new counselor
        Returns: JSON response with status
        """
        try:
            # Extract form inputs
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            department = request.form.get('department')

            # Validation
            if not all([name, email, password, department]):
                return jsonify({"error": "All fields are required"}), 400

            # Check if email already exists
            if users.find_one({"email": email}):
                return jsonify({"error": "Email already exists"}), 400

            # Hash the password
            hashed_password = generate_password_hash(password, method="pbkdf2")

            # Insert counselor into database
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
        """
        Register a new student with 7-day token expiration
        Returns: JSON response with access token
        """
        try:
            # Extract form inputs
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

            # Validation
            if not all([name, email, parent_name, parent_contact, hostel_hall,
                        phone, department, matric, room_number]):
                return jsonify({"error": "All fields are required"}), 400

            # Check if email already exists
            if students.find_one({"email": email}):
                return jsonify({"error": "Email already exists"}), 400

            # Generate a unique access token
            alphabet = string.ascii_uppercase + string.digits
            access_token = ''.join(secrets.choice(alphabet) for _ in range(8))

            # Calculate token expiration (7 days from now)
            token_created_at = datetime.datetime.utcnow()
            token_expires_at = token_created_at + datetime.timedelta(days=7)

            # Store student details in the database
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
        """
        Authenticate counselor or admin
        Returns: User record if valid, None otherwise
        """
        try:
            # Extract form inputs
            email = request.form.get('email')
            password = request.form.get('password')

            # Find user by email (use index for faster query)
            user_record = users.find_one({'email': email})

            if not user_record:
                return None, None, None

            return user_record, email, password

        except Exception as e:
            print(f"Login error: {e}")
            return None, None, None

    @staticmethod
    def student_login():
        """
        Authenticate student using token (with expiration check)
        Returns: Student record if valid and not expired, None otherwise
        """
        try:
            token = request.form.get('token')

            if not token:
                return None

            # Find student by access token (use index for faster query)
            student_record = students.find_one({"access_token": token})

            if not student_record:
                return None

            # Check if token has expired
            token_expires_at = student_record.get('token_expires_at')
            current_time = datetime.datetime.utcnow()
            if token_expires_at and current_time > token_expires_at:
                # Token has expired
                return {"expired": True, "student": student_record}

            return student_record

        except Exception as e:
            print(f"Student login error: {e}")
            return None

    @staticmethod
    def regenerate_student_token(student_id):
        """
        Generate a new access token for a student (7-day expiration)
        Used by counselors to renew expired tokens
        Returns: New token or None
        """
        try:
            # Generate new token
            alphabet = string.ascii_uppercase + string.digits
            new_token = ''.join(secrets.choice(alphabet) for _ in range(8))

            # Calculate new expiration
            token_created_at = datetime.datetime.utcnow()
            token_expires_at = token_created_at + datetime.timedelta(days=7)

            # Update student record
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

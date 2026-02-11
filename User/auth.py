# decorators.py
from functools import wraps
from flask import session, redirect, url_for, flash


def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "role" not in session:
                flash("Please login first", "error")
                return redirect(url_for('IMHSS.counselor_login'))

            if session["role"] != required_role:
                flash("Unauthorized access", "error")
                return redirect(url_for('IMHSS.counselor_login'))

            return f(*args, **kwargs)
        return wrapper
    return decorator


def student_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "student":
            flash("Please login as student", "error")
            return redirect(url_for('IMHSS.student_login'))
        return f(*args, **kwargs)
    return wrapper


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first", "error")
            return redirect(url_for('IMHSS.counselor_login'))
        return f(*args, **kwargs)
    return wrapper

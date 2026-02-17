# User/database.py - Optimized Database Connection with Indexes
import os
import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from dotenv import load_dotenv

load_dotenv()

# Get MongoDB URI
mongo_uri = os.getenv("MONGODB_URI")
if not mongo_uri:
    raise RuntimeError("MONGODB_URI not set in environment variables")

# Create MongoDB client with optimized settings
client = MongoClient(
    mongo_uri,
    serverSelectionTimeoutMS=3000,
    maxPoolSize=50,
    minPoolSize=10,
    maxIdleTimeMS=45000,
    connectTimeoutMS=10000,
    socketTimeoutMS=20000
)

# Database instance
db = client.IMHSS

# Collections
users = db.users
students = db.student
messages = db.messages
flags = db.flags
logs = db.activity_logs

# ============================================
# PRIVATE COUNSELOR–STUDENT MESSAGES
# Strictly private: accessible only to the counselor who sent the
# message. No admin route imports or queries this collection.
# Schema per document:
#   _id            str  UUID
#   counselor_id   str  session user_id of the sending counselor
#   counselor_name str  display name of counselor
#   counselor_email str email used as reply-to
#   student_id     str  student._id
#   student_name   str  student display name
#   student_email  str  delivery address
#   subject        str
#   body           str
#   sent_at        datetime UTC
#   email_status   str  "sent" | "failed"
# ============================================
counselor_messages = db.counselor_messages

# ============================================
# PASSWORD RESET TOKENS
# Short-lived (1 hour) tokens for forgot-password flow.
# Accessible only by the forgot/reset routes — no dashboard route
# reads or writes this collection.
# Schema per document:
#   _id        str      UUID
#   user_id    str      users._id of the requesting user
#   email      str      for fast lookup on submit
#   token      str      secrets.token_urlsafe(48) — URL-safe random
#   created_at datetime UTC
#   expires_at datetime UTC  (created_at + 1 hour)
#   used       bool     True once the reset has been completed
# ============================================
password_reset_tokens = db.password_reset_tokens


# ============================================
# CREATE INDEXES FOR PERFORMANCE (AUTO-ENABLED)
# ============================================
def setup_indexes():
    try:
        print("Setting up database indexes...")

        users.create_index([("email", ASCENDING)], unique=True,
                           background=True)
        users.create_index([("role", ASCENDING)], background=True)
        users.create_index([("status", ASCENDING)], background=True)
        print("Users indexes created")

        students.create_index([("email", ASCENDING)], unique=True,
                              background=True)
        students.create_index([("access_token", ASCENDING)], unique=True,
                              background=True)
        students.create_index([("counselor_id", ASCENDING)], background=True)
        students.create_index([("token_used", ASCENDING)], background=True)
        students.create_index([("token_expires_at", ASCENDING)],
                              background=True)
        students.create_index(
            [("counselor_id", ASCENDING), ("token_expires_at", ASCENDING)],
            background=True)
        print("Students indexes created")

        messages.create_index(
            [("student_id", ASCENDING), ("timestamp", DESCENDING)],
            background=True)
        messages.create_index(
            [("counselor_id", ASCENDING), ("timestamp", DESCENDING)],
            background=True)
        messages.create_index(
            [("session_id", ASCENDING), ("timestamp", ASCENDING)],
            background=True)
        messages.create_index([("flagged", ASCENDING)], background=True)
        messages.create_index([("risk_level", ASCENDING)], background=True)
        messages.create_index([("timestamp", DESCENDING)], background=True)
        print("Messages indexes created")

        flags.create_index(
            [("counselor_id", ASCENDING), ("reviewed", ASCENDING),
             ("flagged_at", DESCENDING)], background=True)
        flags.create_index(
            [("student_id", ASCENDING), ("flagged_at", DESCENDING)],
            background=True)
        flags.create_index([("reviewed", ASCENDING)], background=True)
        flags.create_index([("message_id", ASCENDING)], background=True)
        flags.create_index(
            [("risk_level", ASCENDING), ("reviewed", ASCENDING)],
            background=True)
        print("Flags indexes created")

        logs.create_index([("timestamp", DESCENDING)], background=True)
        logs.create_index(
            [("user_id", ASCENDING), ("timestamp", DESCENDING)],
            background=True)
        print("Activity logs indexes created")

        # Counselor–Student private messages — scoped to counselor_id only
        counselor_messages.create_index(
            [("counselor_id", ASCENDING), ("sent_at", DESCENDING)],
            background=True)
        counselor_messages.create_index(
            [("student_id", ASCENDING), ("sent_at", DESCENDING)],
            background=True)
        counselor_messages.create_index(
            [("counselor_id", ASCENDING), ("student_id", ASCENDING),
             ("sent_at", DESCENDING)], background=True)
        print("Counselor messages indexes created")

        # Password reset tokens
        # token field is unique so duplicate tokens are impossible
        password_reset_tokens.create_index(
            [("token", ASCENDING)], unique=True, background=True)
        password_reset_tokens.create_index(
            [("email", ASCENDING), ("used", ASCENDING)], background=True)
        password_reset_tokens.create_index(
            [("expires_at", ASCENDING)], background=True,
            expireAfterSeconds=0   # MongoDB TTL index — auto-deletes expired docs
        )
        print("Password reset token indexes created")

        print("All database indexes created successfully!")
        return True

    except Exception as e:
        print(f"Error creating indexes: {e}")
        return False


# ============================================
# PERFORMANCE OPTIMIZATION UTILITIES
# ============================================
def get_collection_stats():
    """
    NOTE: counselor_messages and password_reset_tokens are intentionally
    excluded — admin must not see counts or content of private
    counselor–student correspondence or reset token activity.
    """
    try:
        stats = {
            "users": users.estimated_document_count(),
            "students": students.estimated_document_count(),
            "messages": messages.estimated_document_count(),
            "flags": flags.estimated_document_count(),
            "logs": logs.estimated_document_count()
        }
        return stats
    except Exception as e:
        print(f"Error getting collection stats: {e}")
        return {}


def cleanup_old_messages(days_to_keep=90):
    try:
        cutoff_date = (
            datetime.datetime.utcnow() - datetime.timedelta(days=days_to_keep)
        )
        result = messages.delete_many({"timestamp": {"$lt": cutoff_date}})
        print(f"Cleaned up {result.deleted_count} old messages")
        return result.deleted_count
    except Exception as e:
        print(f"Error cleaning up messages: {e}")
        return 0


def get_expired_tokens():
    try:
        now = datetime.datetime.utcnow()
        expired_students = list(students.find({
            "token_expires_at": {"$lt": now}
        }).sort("token_expires_at", DESCENDING))
        return expired_students
    except Exception as e:
        print(f"Error getting expired tokens: {e}")
        return []


# ============================================
# AUTO-RUN INDEX SETUP ON IMPORT
# ============================================
try:
    setup_indexes()
except Exception as e:
    print(f"Warning: Could not setup indexes automatically: {e}")
    print("Indexes will be created on next database operation")

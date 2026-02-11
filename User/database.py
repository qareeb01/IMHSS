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
    maxPoolSize=50,  # Increased connection pool for better performance
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
# CREATE INDEXES FOR PERFORMANCE (AUTO-ENABLED)
# ============================================
def setup_indexes():
    """
    Create database indexes for optimal query performance.
    This significantly speeds up queries and reduces database load.
    """
    try:
        print("🔧 Setting up database indexes...")

        # Users collection indexes
        users.create_index(
            [("email", ASCENDING)],
            unique=True,
            background=True)
        users.create_index([("role", ASCENDING)], background=True)
        users.create_index([("status", ASCENDING)], background=True)
        print("✅ Users indexes created")

        # Students collection indexes (CRITICAL FOR PERFORMANCE)
        students.create_index(
            [("email", ASCENDING)],
            unique=True,
            background=True
        )
        students.create_index(
            [("access_token", ASCENDING)],
            unique=True,
            background=True)
        students.create_index(
            [("counselor_id", ASCENDING)],
            background=True)
        students.create_index(
            [("token_used", ASCENDING)],
            background=True)
        students.create_index(
            [("token_expires_at", ASCENDING)],
            background=True)  # NEW: for expiration checks
        students.create_index(
            [("counselor_id", ASCENDING),
             ("token_expires_at", ASCENDING)],
            background=True)  # NEW: compound index
        print("✅ Students indexes created")

        # Messages collection indexes (CRITICAL FOR CHAT PERFORMANCE)
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
        print("✅ Messages indexes created")

        # Flags collection indexes (CRITICAL FOR COUNSELOR DASHBOARD)
        flags.create_index(
            [("counselor_id", ASCENDING), ("reviewed", ASCENDING),
             ("flagged_at", DESCENDING)],
            background=True
        )
        flags.create_index(
            [("student_id", ASCENDING), ("flagged_at", DESCENDING)],
            background=True)
        flags.create_index(
            [("reviewed", ASCENDING)], background=True)
        flags.create_index([("message_id", ASCENDING)], background=True)
        flags.create_index(
            [("risk_level", ASCENDING), ("reviewed", ASCENDING)],
            background=True)  # NEW: for filtering
        print("✅ Flags indexes created")

        # Activity logs indexes
        logs.create_index([("timestamp", DESCENDING)], background=True)
        logs.create_index(
            [("user_id", ASCENDING), ("timestamp", DESCENDING)],
            background=True)
        print("✅ Activity logs indexes created")

        print("✅ All database indexes created successfully!")
        return True

    except Exception as e:
        print(f"❌ Error creating indexes: {e}")
        return False


# ============================================
# PERFORMANCE OPTIMIZATION UTILITIES
# ============================================
def get_collection_stats():
    """
    Get statistics about database collections for monitoring
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
    """
    Archive or delete old messages to improve performance
    Optional: Run this periodically via cron job
    """
    try:
        cutoff_date = (
            datetime.datetime.utcnow() -
            datetime.timedelta(days=days_to_keep)
        )
        result = messages.delete_many({"timestamp": {"$lt": cutoff_date}})
        print(f"✅ Cleaned up {result.deleted_count} old messages")
        return result.deleted_count
    except Exception as e:
        print(f"❌ Error cleaning up messages: {e}")
        return 0


def get_expired_tokens():
    """
    Get all students with expired tokens
    Used by counselors to identify who needs new tokens
    """
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
# Automatically create indexes when the module is imported
# This ensures optimal performance from the start
try:
    setup_indexes()
except Exception as e:
    print(f"⚠️  Warning: Could not setup indexes automatically: {e}")
    print("   Indexes will be created on next database operation")

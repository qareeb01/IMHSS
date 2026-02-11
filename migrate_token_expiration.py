"""
Migration Script: Add Token Expiration to Existing Students
Run this ONCE after updating to the new system
"""

import datetime
import sys
import os
from User.database import students

# Add the parent directory to path so we can import User module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def migrate_student_tokens():
    """
    Add token_created_at and token_expires_at to all existing students
    without these fields
    """
    print("=" * 60)
    print("IMHSS Token Expiration Migration")
    print("=" * 60)
    print()

    # Count students without expiration
    students_without_expiration = students.count_documents({
        "token_expires_at": {"$exists": False}
    })

    print(f"Found {students_without_expiration}"
          "students without token expiration")

    if students_without_expiration == 0:
        print("✅ All students already have token expiration set!")
        print("    No migration needed.")
        return

    # Ask for confirmation
    print()
    print("This will:")
    print("  1. Set token_created_at to NOW for all students")
    print("  2. Set token_expires_at to 7 days from NOW")
    print()

    confirm = input("Continue? (yes/no): ").strip().lower()

    if confirm != 'yes':
        print("❌ Migration cancelled")
        return

    print()
    print("🔄 Starting migration...")

    # Current timestamp
    now = datetime.datetime.utcnow()
    expires_at = now + datetime.timedelta(days=7)

    # Update all students without expiration
    result = students.update_many(
        {"token_expires_at": {"$exists": False}},
        {
            "$set": {
                "token_created_at": now,
                "token_expires_at": expires_at
            }
        }
    )

    print("✅ Migration complete!")
    print(f"   Updated: {result.modified_count} students")
    print(f"   Token expires: {expires_at.strftime('%B %d, %Y at %I:%M %p')}")
    print()
    print("⚠️  NOTE: All existing tokens will expire in 7 days")
    print("   Counselors can regenerate tokens from their dashboard")
    print()

    # Show sample of updated students
    print("Sample of updated students:")
    print("-" * 60)

    sample_students = students.find(
        {"token_created_at": {"$exists": True}},
        {"name": 1, "access_token": 1, "token_expires_at": 1}
    ).limit(5)

    for student in sample_students:
        expires = student.get('token_expires_at')
        expires_str = (
            expires.strftime('%b %d, %Y %I:%M %p')
            if expires else 'N/A'
        )
        print(
            f"  • {student['name'][:30]:30} | Token: {student['access_token']}"
            f"| Expires: {expires_str}"
        )

    print("-" * 60)
    print()


def verify_migration():
    """
    Verify that all students have token expiration set
    """
    print("=" * 60)
    print("Verifying Migration")
    print("=" * 60)
    print()

    total_students = students.count_documents({})
    students_with_expiration = students.count_documents({
        "token_expires_at": {"$exists": True}
    })
    students_without_expiration = total_students - students_with_expiration

    print(f"Total students: {total_students}")
    print(f"With expiration: {students_with_expiration}")
    print(f"Without expiration: {students_without_expiration}")
    print()

    if students_without_expiration == 0:
        print("✅ All students have token expiration!")

        # Show expiration summary
        now = datetime.datetime.utcnow()

        expired = students.count_documents({
            "token_expires_at": {"$lt": now}
        })

        expiring_soon = students.count_documents({
            "token_expires_at": {
                "$gte": now,
                "$lt": now + datetime.timedelta(days=3)
            }
        })

        active = students.count_documents({
            "token_expires_at": {"$gte": now + datetime.timedelta(days=3)}
        })

        print()
        print("Token Status Summary:")
        print(f"  🔴 Expired: {expired} students")
        print(f"  🟡 Expiring soon (< 3 days): {expiring_soon} students")
        print(f"  🟢 Active (3+ days): {active} students")

    else:
        print("❌ Migration incomplete!")
        print(
            f"   {students_without_expiration} students still need "
            "migration"
        )
        print("   Run migrate_student_tokens() again")

    print()


def show_expired_tokens():
    """
    Show all students with expired tokens
    """
    print("=" * 60)
    print("Students with Expired Tokens")
    print("=" * 60)
    print()

    now = datetime.datetime.utcnow()

    expired_students = list(students.find({
        "token_expires_at": {"$lt": now}
    }, {
        "name": 1,
        "access_token": 1,
        "token_expires_at": 1,
        "counselor_id": 1
    }).sort("token_expires_at", -1))

    if not expired_students:
        print("✅ No expired tokens!")
        return

    print(f"Found {len(expired_students)} expired tokens:")
    print()

    for student in expired_students:
        expired_date = student.get('token_expires_at')
        expired_str = (
            expired_date.strftime('%b %d, %Y %I:%M %p')
            if expired_date else 'Unknown'
        )
        days_ago = (now - expired_date).days if expired_date else 0

        print(
            f"  • {student['name'][:30]:30} | Expired: {expired_str} "
            f"({days_ago} days ago)"
        )

    print()
    print("Counselors can regenerate these tokens from their dashboard")
    print()


if __name__ == "__main__":
    import sys

    print()
    print("IMHSS Token Expiration Migration Tool")
    print()
    print("Commands:")
    print("  1. migrate  - Add expiration to existing students")
    print("  2. verify   - Check migration status")
    print("  3. expired  - Show expired tokens")
    print()

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
    else:
        command = input("Enter command (migrate/verify/expired): ")
        command = command.strip().lower()

    print()

    if command == "migrate":
        migrate_student_tokens()
    elif command == "verify":
        verify_migration()
    elif command == "expired":
        show_expired_tokens()
    else:
        print("❌ Invalid command")
        print("   Use: migrate, verify, or expired")

    print()

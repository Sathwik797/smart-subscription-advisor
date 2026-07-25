"""Repository layer for user-related SQLAlchemy queries and writes.

Repositories are responsible for all database access so the service layer can
remain focused on business rules.
"""

from database.db import db
from exceptions.exceptions import DatabaseException
from logging_config.logger import logger
from models.user import User


class UserRepository:
    """Handle user database access."""

    @staticmethod
    def get_user_by_username(username):
        return User.query.filter_by(username=username).first()

    @staticmethod
    def get_user_by_email(email):
        return User.query.filter_by(email=email).first()

    @staticmethod
    def get_user_by_id(user_id):
        return User.query.get(int(user_id))

    @staticmethod
    def save_user(user):
        try:
            db.session.add(user)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.error("Database failure while saving user")
            raise DatabaseException("Unable to save user") from exc
        return user

    @staticmethod
    def update_user(user):
        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.error("Database failure while updating user")
            raise DatabaseException("Unable to update user") from exc
        return user

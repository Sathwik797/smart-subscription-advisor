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
        return db.session.get(User, int(user_id))

    @staticmethod
    def get_user_by_mobile_number(mobile_number):
        return User.query.filter_by(mobile_number=mobile_number).first()

    @staticmethod
    def get_user_by_verification_token(token):
        return User.query.filter_by(verification_token=token).first()

    @staticmethod
    def get_user_by_reset_token(token):
        return User.query.filter_by(reset_token=token).first()


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

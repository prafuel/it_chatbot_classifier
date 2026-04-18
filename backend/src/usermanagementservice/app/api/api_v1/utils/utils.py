import re
from app.crud import crud_user
from app import schema

def get_user_details(db, user_data):
    """
    This function takes user data and fetches the data from username
    """
    user = crud_user.get_user_by_email(db, user_data.email)
    return user


def is_valid_password(password):
    # code for checking if password has 6 characters, 1 uppercase, 1 lower case and a special character
    reg = r"^(?=.*[0-9])(?=.*[a-z])(?=.*[A-Z])(?=.*\W)(?!.* ).{6,}$"
    match = re.search(reg, password)
    return match


def save_user_details(db, user_details):
    """
    This function will take the user details while signing up and save them in database
    """
    user = crud_user.create_user(db, user_details)
    return user


def create_token_object(user_jwt_token, user_type=None):
    """
    This function takes JWT token as an argument and returns a token object
    """
    token_obj = schema.TokenResponse()
    token_obj.token = user_jwt_token
    token_obj.token_type = "Bearer"
    token_obj.user_type = user_type
    return token_obj
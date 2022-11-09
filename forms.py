from tokenize import String
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, EmailField, PasswordField, TextAreaField
from wtforms.validators import DataRequired,EqualTo, Length
from wtforms.widgets import TextArea

#Sign Up Form
class SignUpForm(FlaskForm):
    username = StringField('Username: ', validators=DataRequired)
    email = EmailField('Email: ', validators=DataRequired)
    submit = SubmitField('Sign Up')
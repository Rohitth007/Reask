from flask_wtf import FlaskForm  # Helps with Cross-Site Request Forgery(CSRF)
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, SelectField, ValidationError  # These help with easier form validators and checking corner cases
from wtforms.validators import DataRequired, Length, Regexp, Email  # Check the book Flask Web Development by Miguel Grinberg for more.
from flask_pagedown.fields import PageDownField  # Python wrapper for paedown that integrates with flask_wtf
from ..models import Role, User


# Creating form class
# class TestForm(FlaskForm):
#     name = StringField('What is your name?', validators=[DataRequired()])
#     submit = SubmitField('Submit')


class EditProfileForm(FlaskForm):
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')


class EditProfileAdminForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0, 'Usernames must have only letters, numbers, dots or underscores')])
    email = StringField('Email', validators=[DataRequired(), Length(1,64), Email()])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', coerce=int)
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super().__init__()
        self.role.choices = [(role.id, role.role_name) for role in Role.query.order_by(Role.role_name).all()]
        self.user = user

    # email is validated only when it is changes so we need 'self.user'
    def validate_email(self, field):
        if field.data != self.user.email and User.query.filter_by(email=field.data).first():
            raise ValidationError('This Email is already registered.')

    def validate_username(self, field):
        if field.data != self.user.username and User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')


class PostForm(FlaskForm):
    body = PageDownField("What's on your mind?", validators=[DataRequired()])
    submit = SubmitField('Submit')


class CommentForm(FlaskForm):
    body = StringField('', validators=[DataRequired()])
    submit = SubmitField('Submit')

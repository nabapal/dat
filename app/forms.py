from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, DateTimeField, DateField, SelectMultipleField
from wtforms.validators import DataRequired, Optional

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class ActivityForm(FlaskForm):
    details = TextAreaField('Details', validators=[DataRequired()])
    node_name = SelectField('Node Name', coerce=str, validators=[DataRequired()])
    activity_type = SelectField('Activity Type', coerce=str, validators=[DataRequired()])
    status = SelectField('Status', coerce=str, validators=[DataRequired()])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[Optional()])
    assigned_to = SelectMultipleField('Assign To', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Save Activity')

class DummyDropdownForm(FlaskForm):
    node_name = StringField('Node Name', validators=[Optional()])
    activity_type = StringField('Activity Type', validators=[Optional()])
    status = StringField('Status', validators=[Optional()])
    submit = SubmitField('Add Option')

class UpdateForm(FlaskForm):
    update_text = TextAreaField('Update', validators=[DataRequired()])
    update_date = DateField('Date of Update', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Submit Update')

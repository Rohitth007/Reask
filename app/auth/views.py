# New Blueprint for authentication, since it's better the have different blueprints to keep it organized
from flask import render_template, request, session, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from . import auth
from .. import db
from ..models import User
from .forms import LoginForm, RegistrationForm
from ..email import send_email

@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():  # For a POST request
        user = User.query.filter_by(email=form.email.data).first()
        # check if user exists in database and correct password was typed
        if user is None or not user.verify_password(form.password.data):
            flash('Invalid username or password.')
            return redirect(url_for('.login'))
        else:
            '''
                Logs into the user session.
                Creates long term cookie if remember_me is true
                else closes when browser is closed.
                Cookie can stay for 1 year by default
                Can be changed by setting config REMEMBER_COOKIE_DURATION
            '''
            login_user(user, form.remember_me.data)
            flash(f'Welcome {user.username}!')
            '''
                Flask_login stores the protected url in 'next' argument.
                Can be used to return user back to origin URL after authentication
                To prevent hackers to take advantage of next argument'
                we have to check if it is a relative URL
            '''
            next = request.args.get('next')
            # check if next doesn't exist or next is not a relative url, if not then redirect to main.index
            if next is None or not next.startswith('/'):
                next = url_for('main.index')
            return redirect(next)

    return render_template('auth/login.html.j2', form=form)  # For GET request or form.validation fails
    # Template files are relative to this files location
    # Also having a different folder reduces the chances of collision errors

@auth.route('/logout')
@login_required
def logout():
    logout_user()   # Removes and resets the user session
    flash('You have successfully been logged out.')
    return redirect(url_for('main.index'))


@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegistrationForm()
    if request.method == 'GET':
        return render_template('auth/register.html.j2', form=form)
    else:
        if form.validate_on_submit():
            user = User(email=form.email.data, username=form.username.data, hash_password=form.password.data)
            db.session.add(user)
            db.session.commit()
            token = user.generate_confirmation_token()
            send_email(user.email, 'Confirm Your Account', 'auth/email/confirm', user=user, token=token)
            flash('A confirmation email has been sent to your email.')
            return redirect(url_for('main.index'))
        return redirect(url_for('.login'))

@auth.route('/confirm/<token>')
@login_required   # when user clicks link from email (s)he has to login
def confirm(token):
    if current_user.confirmed:   # If user clicks token multiple times
        return redirect(url_for('main.index'))
    elif current_user.confirm(token):
        db.session.commit()
        flash('Thankyou for confirming your account.')
    else:
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('main.index'))

# Every app can decide what unconfirmed users can do
# Here I am asking them to confirm for every page they try to visit
@auth.before_app_request  # before_request only intercepts request in this blueprint so before_app_request is used
def before_request():
    # '.is_authenticated' :So that he is not asked to confirm before he logs in
    # 'request.blueprint' :So that calling an auth view that confirms user does not redirect to confim page again
    # 'request.endpoint'  :So that rendering css of a page is not intercepted
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed \
            and request.blueprint != 'auth' \
            and request.endpoint != 'static':
            return redirect(url_for('auth.unconfirmed'))


@auth.route('/unconfirmed')
def unconfirmed():
    # Gives users instructions to confirm their account
    if current_user.is_anonymous or current_user.confirmed:   # So that typing /unconfirmed in url doesnt bring you to this page if you are a random person or already confirmed
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html.j2')

@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account', 'auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation token has been sent to your email.')
    return redirect(url_for('main.index'))

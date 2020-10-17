from datetime import datetime
from flask import render_template, url_for, redirect, session, request, flash, current_app, abort, make_response
from flask_login import login_required, current_user
from . import main  # blueprint from __init__.py
from .forms import EditProfileForm, EditProfileAdminForm, PostForm, CommentForm
from ..email import send_email
from .. import db
from ..models import User, Permission, Role, Post, Comment
from ..decorators import admin_required, permission_required


'''
Checks if user is in database by calling the 'load_user'
function using the 'login_manager.user_loader' decorator
else redirects them to login view registered in the 'auth.view' blueprint.
Decorators can be chained as below but order matters.
If 'login_required' is put first then route will be registered
before checking for authorisation
'''
@main.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit() and current_user.can(Permission.WRITE):
        post = Post(body=form.body.data, author=current_user._get_current_object())
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)  # 'page' arg is converted to an integer. If not then default 1.
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query
    pagination = query.order_by(Post.timestamp.desc())\
                      .paginate(page,
                                per_page=current_app.config['POSTS_PER_PAGE'],  # Default 20
                                error_out=False)  # raises 404 if True when page outside range is asked. If False empty list is given
    posts = pagination.items
    return render_template('index.html.j2', form=form, posts=posts, pagination=pagination, show_followed=show_followed)


@main.route('/admin')
@login_required
@admin_required
def for_admins_only():
    return "For Administrators!"


# >>>MODERATOR AND OPTIONS
@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE)
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc())\
                              .paginate(page,
                                        per_page=current_app.config['COMMENTS_PER_PAGE'],
                                        error_out=False)
    comments = pagination.items
    return render_template('moderate.html.j2', pagination=pagination, comments=comments, page=page)


@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    db.session.commit()

    # to get him back to same page
    page = request.args.get('page', 1, type=int)
    return redirect(url_for('.moderate', page=page))


@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    db.session.commit()

    page = request.args.get('page', 1, type=int)
    return redirect(url_for('.moderate', page=page))


# >>>USER PROFILE and OPTIONS
@main.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = user.posts.order_by(Post.timestamp.desc()).all()
    return render_template('user.html.j2', user=user, posts=posts)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user._get_current_object())
        db.session.commit()
        flash('Your Profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))

    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html.j2', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.confirmed = form.confirmed.data
        user.role_id = form.role.data
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash(f'The profile of {id} has been updated.')
        return redirect(url_for('.user', username=user.username))

    form.username.data = user.username
    form.email.data = user.email
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html.j2', form=form, user=user)


# >>>POST DISPLAY and OPTIONS
@main.route('/post/<int:id>', methods=['GET', 'POST'])
@login_required
def post(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data, post=post, author=current_user._get_current_object())
        db.session.add(comment)
        db.session.commit()
        return redirect(url_for('.post', id=post.id, page=-1))

    page = request.args.get('page', 1, type=int)
    # To get the last page, i.e., the page where the new post will be
    if page == -1:
        page = (post.comments.count() - 1) // current_app.config['COMMENTS_PER_PAGE'] + 1

    pagination = post.comments.order_by(Comment.timestamp.asc())\
                              .paginate(page,
                                        per_page=current_app.config['COMMENTS_PER_PAGE'],
                                        error_out=False)
    comments = pagination.items
    return render_template('post.html.j2', posts=[post], form=form, comments=comments, pagination=pagination)  # List so that _posts.html can be used


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permission.ADMIN):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        db.session.commit()
        flash('The post has been updated')
        return redirect(url_for('.post', id=post.id))
    form.body.data = post.body
    return render_template('edit_post.html.j2', form=form)


# homepage posts display
@main.route('/all')
@login_required
def show_all():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '', max_age=30*24*60*60)
    return resp


@main.route('/followed')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '1', max_age=30*24*60*60)
    return resp


# >>>FOLLOW and OPTIONS
@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    elif current_user.is_following(user):
        flash('You already following this user.')
    else:
        current_user.follow(user)
        db.session.commit()
        flash(f'You are now following {username}.')
    return redirect(url_for('.user', username=username))


@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    elif not current_user.is_following(user):
        flash("You don't already follow this user.")
    else:
        current_user.unfollow(user)
        db.session.commit()
        flash(f'You have unfollowed {username}.')
    return redirect(url_for('.user', username=username))


@main.route('/followers/<username>')
@login_required
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(page,
                                         per_page=current_app.config['FOLLOWS_PER_PAGE'],
                                         error_out=False)
    follows = [{"user": item.follower, "timestamp": item.timestamp}
               for item in pagination.items]
    return render_template('follow.html.j2',
                           user=user,
                           title=f"Followers of {user.username}:",
                           endpoint='.followers',
                           pagination=pagination,
                           follows=follows)


@main.route('/following/<username>')
@login_required
def following(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(page,
                                        per_page=current_app.config['FOLLOWS_PER_PAGE'],
                                        error_out=False)
    follows = [{"user": item.followed, "timestamp": item.timestamp}
               for item in pagination.items]
    return render_template('follow.html.j2',
                           user=user,
                           title=f"People {user.username} follows:",
                           endpoint='.following',
                           pagination=pagination,
                           follows=follows)


# @main.route('/form', methods=['GET', 'POST'])
# @login_required
# def form():
#     form = TestForm()  # Creating instance of TestForm
#     if request.method == 'GET':
#         return render_template("form.html.j2", form=form, name=session.get('name'), current_time=datetime.utcnow()) # Using get() is better for dictionary
#
#     else:
#         if form.validate_on_submit():  # Returns True if all validators satisfy
#             app = current_app._get_current_object()  # To use app.config dictionary
#
#             session['name'] = form.name.data  # Getting name data better to store in sessions
#             form.name.data = ''  # Resetting name field to empty string
#
#             # Check if user already exists in db else add him **User role should already exist**
#             user = User.query.filter_by(username=session['name']).first()
#             if user is None:
#                 user = User(username=session['name'])  # make new row
#                 db.session.add(user)  # this session is different from flask sessions
#                 if app.config['TEST_ADMIN']: # If new user, send mail to admin
#                     send_email(app.config['TEST_ADMIN'], 'New User', 'email/hello', user=user)
#                 flash("Pleased to meet you!")
#             else:
#                 flash("Good to see you again!")
#
#         return redirect(url_for('.form'))  # Same as redirect('/') better to redirect because request should be a GET
#         # '.form' is same 'main.form' if redirecting to different blueprint then 'blueprint_name.rout_name' is required

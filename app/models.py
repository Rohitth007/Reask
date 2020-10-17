from flask import current_app, request, url_for
from flask_login import UserMixin, AnonymousUserMixin  # Links the User and AnonymousUser model to the login_manager respectively
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer  # creates timed JSON web signatures
from markdown import markdown  # server-side markdown to html converter.
import bleach  # Cleans HTML. Needed as we dont wnt a script injection vulnerability.
from datetime import datetime
import hashlib
from app.exceptions import ValidationError
from . import login_manager
from . import db


# Integer powers of 2 are used to make combinations of permissions earier.
class Permission:
    FOLLOW = 1
    COMMENT = 2
    WRITE = 4
    MODERATE = 8
    ADMIN = 16


class Follow(db.Model):  # A model class has to be made instead of a Table beacuse timestamp needs updating
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# Creating Database classes
# Each instancce of a class is a model. Models make up tables.
class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)  # Primary Key is compulsary in SQLAlchemy
    role_name = db.Column(db.String(64), unique=True)  # Role assigned when new user registers
    default = db.Column(db.Boolean, default=False, index=True)  # 'index' is used to make searching for 'default' column better
    permissions = db.Column(db.Integer, default=0)  # 'default' is added after db.session.commit() i.e., during INSERT as opposed to 'server_default' which add it to the table
    users = db.relationship('User', backref='role', lazy='dynamic')  # Adds a role attribute in User model

    def __repr__(self):  # For debugging
        return f'<id {self.id} | role_name {self.role_name} | default {self.default} | permissions {self.permissions}>\n'

    ### Permissions
    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permission(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm  # Bitwise operation of powers of 2 helps in verification

    '''
        Defining this function is useful and less cubersome when adding roles.
        The function first checks if the role is already
        defined only then creates them if they dont exist.
        This is usefull if new roles are added and need updating.
        The role is reset because updated permissions can be accomodated.
        **Changes can be made by changing the dictionary**
    '''
    @staticmethod  # This doesn't require an instance of an object to be created to use it
    def insert_roles():  # 'self' argument is also not required
        roles = {
            'User': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE],
            'Moderator': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE, Permission.MODERATE],
            'Administrator': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE, Permission.MODERATE, Permission.ADMIN]
        }
        default_role = 'User'
        for r in roles:
            role = Role.query.filter_by(role_name=r).first()
            if role is None:
                role = Role(role_name=r)
            role.reset_permission()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.role_name == default_role)
            db.session.add(role)
        db.session.commit()
    ### Permissions


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))  # Stored as "<hashing_method>$<salt>$<hashed_password>"
    confirmed = db.Column(db.Boolean, default=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    avatar_hash = db.Column(db.String(32))
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)

    posts = db.relationship('Post', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')

    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),  # joined is used to that the followed person is directly querried. without having to do it twice.
                               lazy='dynamic',  # So that query object is returned so that filters can be applied.
                               cascade='all, delete-orphan')  # Useful when deleting
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')

    def to_json(self):
        json_user = {
            'url': url_for('api.get_user', id=self.id),
            'username': self.username,
            'member_since': self.member_since,
            'last_seen': self.last_seen,
            'posts_url': url_for('api.get_user_posts', id=self.id),
            'followed_posts_url': url_for('api.get_user_followed_posts', id=self.id),
            'post_count': self.posts.count()
        }
        return json_user

    # Assigns Roles hence Premissions (gives admin access to only ADMIN environment variable)
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)  # Super to user 'Role'
        if self.role is None:
            if self.email == current_app.config['TEST_ADMIN']:
                self.role = Role.query.filter_by(role_name='Administrator').first()
            else:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.gravatar_hash()
        # Self Follow
        self.follow(self)

    def __repr__(self):
        return f'<id {self.id} | username {self.username} | role_id {self.role_id} | email {self.email} | confirmed {self.confirmed}>\n'

    # ### Password Hashing ###
    @property
    def hash_password(self):   # This is done to make this function Write-Only
        raise AttributeError('password is a readable attribute')

    @hash_password.setter      # decorator for hash_password function which sets password into password_hash
    def hash_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ### login_manager calls this function to check if the user is in the database
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))     # Returns User object of PrimaryKey=user_id else None

    # ### User Confirmation
    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        token = s.dumps({'confirm': self.id})  # generated token with default expiration of 1 hr
        return token.decode('utf-8')

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        # Read token and confirm if correct
        try:
            data = s.loads(token.encode('utf-8'))  # Throws exceptions if token is invalid or timed out
        except:
            return False

        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    # ### Check Permissions
    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    # ### Update Last_Seen
    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    # ### Avatar

    # Uses MD5 to verify email account with gravatar
    # Since MD5 is computationally expensive to do it each time
    # it is cached by storing in avatar_hash. Until email is changed
    # email change is not yet implimented.
    def gravatar_hash(self):
        if not self.avatar_hash:
            self.avatar_hash = hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()
        return self.avatar_hash

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.gravatar_hash()
        return f'{url}/{hash}?s={size}&d={default}&r={rating}'

    # ### Follow Helpers
    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        if user.id is None:
            return False
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        if user.id is None:
            return False
        return self.followed.filter_by(follower_id=user.id).first() is not None

    @property  # So that function can be called without ()
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id)\
                         .filter(Follow.follower_id == self.id)

    @staticmethod  # Self follow so that they appear in followed tab.
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    # ### API Auth Token
    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
        return s.dumps({'id': self.id}).decode('utf-8')

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])


# So that the app can freely call can() and is_administrator() without first having to check whether the user is logged in
class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


login_manager.anonymous_user = AnonymousUser  # telling Flask-Login to use our custom class


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = db.relationship('Comment', backref='post', lazy='dynamic')

    def to_json(self):
        json_post = {
            'url': url_for('api.get_post', id=self.id),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author_url': url_for('api.get_user', id=self.author_id),
            'comment_url': url_for('api.get_post_comments', id=self.id),
            'comment_count': self.comments.count()
        }
        return json_post

    @staticmethod
    def from_json(json_post):
        body = json_post.get('body')
        if body is None or body == '':
            raise ValidationError('Post does not have a body')
        return Post(body=body)

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        m = markdown(value, output_format='html')
        target.body_html = bleach.linkify(bleach.clean(m, tags=allowed_tags, strip=True))  # Linkify creates anchors <a> for links


db.event.listen(Post.body, 'set', Post.on_changed_body)  # Automatically converts when body changes.


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    def to_json(self):
        json_comment = {
            'url': url_for('api.get_comment', id=self.id),
            'post_url': url_for('api.get_post', id=self.post_id),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author_url': url_for('api.get_user', id=self.author_id),
        }
        return json_comment

    @staticmethod
    def from_json(json_comment):
        body = json_comment.get('body')
        if body is None or body == '':
            raise ValidationError('comment does not have a body')
        return Comment(body=body)

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i', 'strong']
        m = markdown(value, output_format='html')
        target.body_html = bleach.linkify(bleach.clean(m, tags=allowed_tags, strip=True))  # Linkify creates anchors <a> for links


db.event.listen(Comment.body, 'set', Comment.on_changed_body)  # Automatically converts when body changes.

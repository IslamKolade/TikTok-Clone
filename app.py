import os
from urllib.parse import urlparse, urljoin
from flask import Flask, render_template, request, flash, redirect, url_for, abort, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
import uuid
from sqlalchemy import desc
from flask_humanize import Humanize
from sqlalchemy.sql.expression import func
from flask_migrate import Migrate

app = Flask(__name__)
humanize = Humanize(app)
HUMANIZE_USE_UTC = True
csrf = CSRFProtect(app)
SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
    username="tiktok",
    password="Kolade4000",
    hostname="tiktok.mysql.pythonanywhere-services.com",
    databasename="tiktok$tiktok",
)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["DEBUG"] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'nonsense'
UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_EXTENSIONS'] = [
    '.mp4', '.mov', '.wmv', '.mkv', '.png', '.jpg', '.jpeg']
# Initialize Database
db = SQLAlchemy(app)
migrate = Migrate(app, db)
# Flask Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Please login to join Tik Tok"


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))
# Routes


@app.route('/', methods=['GET', 'POST'])
def home():
    posts = Post.query.order_by(func.random())
    return render_template('home.html', posts=posts)

# Admin Page


@app.route('/admin')
@login_required
def admin():
    id = current_user.id
    if id == 1:
        my_users = Users.query.order_by(Users.id)
        return render_template('admin.html', my_users=my_users)
    else:
        flash('Access Denied!')
        return redirect(url_for('home'))


# Search
@app.route('/search', methods=['GET', 'POST'])
def search():
    posts = Post.query.order_by(func.random())
    return render_template('search.html', posts=posts)

# Search Result


@app.route('/search_result', methods=['GET', 'POST'])
def search_result():
    posts = Post.query
    if request.method == 'POST':
        # Get data from submitted form
        postsearched = request.form['searched']
        # Query the database
        posts = posts.filter(Post.content.like('%' + postsearched + '%'))
        posts = posts.order_by(Post.post_vid).all()
        return render_template('search_result.html', searched=postsearched, posts=posts)
    return render_template('search_result.html')


# Search Result User
@app.route('/search_result_users', methods=['GET', 'POST'])
def search_result_users():
    users = Users.query
    if request.method == 'POST':
        # Get data from submitted form
        usersearched = request.form['searched']
        # Query the database
        users = users.filter(Users.username.like('%' + usersearched + '%'))
        users = users.order_by(desc(Users.id)).all()
        return render_template('search_result_users.html', searched=usersearched, users=users)
    return render_template('search_result_users.html')


# Likes
@app.route('/like/<post_id>',  methods=['POST'])
@login_required
@csrf.exempt
def like(post_id):
    post = Post.query.filter_by(id=post_id).first()
    like = Like.query.filter_by(
        liker_id=current_user.id, post_id=post_id).first()
    if not post:
        return jsonify({'error': 'Post does not exist.'}, 400)
    elif like:
        db.session.delete(like)
        db.session.commit()
    else:
        like = Like(liker_id=current_user.id, post_id=post_id)
        db.session.add(like)
        db.session.commit()
    return jsonify({"likes": len(post.likes), "liked": current_user.id in map(lambda x: x.liker_id, post.likes)})


@app.route('/change_password/<int:id>', methods=['GET', 'POST'])
@login_required
def change_password(id):
    if id == current_user.id:
        if request.method == 'POST':
            old_password = request.form['old_password']
            new_password = request.form['new_password']
            id = current_user.id
            password_to_change = Users.query.get_or_404(id)
            if check_password_hash(password_to_change.password, old_password):
                password_to_change.password = generate_password_hash(
                    new_password, 'sha256')
                try:
                    db.session.commit()
                    flash('Password changed successfully.')
                    return render_template('change_password.html')
                except:
                    flash('*Oops, there was a problem changing your password')
                    return render_template('change_password.html')
            else:
                flash('*Old password is incorrect.')
                return render_template('change_password.html')
        return render_template('change_password.html')
    else:
        flash("Access Denied")
        return redirect(url_for('home'))

# Delete Post


@login_required
@app.route('/post/delete/<int:id>')
def delete_post(id):
    post_to_delete = Post.query.get_or_404(id)
    id = current_user.id
    if id == post_to_delete.poster.id or id == 1:
        try:
            db.session.delete(post_to_delete)
            db.session.commit()
            os.remove(os.path.join(app.root_path,
                      app.config['UPLOAD_FOLDER'], post_to_delete.post_vid))
            flash('Post Deleted Successfully')
            return redirect(url_for('home'))
        except:
            flash('Oops, there was a problem deleting that post. Try again')
            return redirect(url_for('home'))
    else:
        flash("Access Denied")
        return redirect(url_for('home'))


# Full Post
@app.route('/fullpost/<int:id>', methods=['GET', 'POST'])
def fullpost(id):
    fullpost = Post.query.get_or_404(id)
    return render_template('fullpost.html', fullpost=fullpost)

# Add Post Page


@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    if request.method == 'POST':
        if request.files['post_vid']:
            content = request.form['content']
            post_vid = request.files['post_vid']
            # Take Video
            vid_filename = secure_filename(post_vid.filename)
            # Set UUID to change post video name to random to avoid duplication.
            vid_name = str(uuid.uuid1()) + '' + vid_filename
            # Save Video
            savevid = request.files['post_vid']
            # Convert Video to string to save to database
            post_vid = vid_name
            poster = current_user.id
            file_ext = os.path.splitext(vid_filename)[1]
            if file_ext not in app.config['UPLOAD_EXTENSIONS']:
                flash('Sorry, we only accept videos.')
                return redirect(url_for('create_post'))
            post = Post(content=content, poster_id=poster, post_vid=post_vid)
            # Add post to database
            db.session.add(post)
            db.session.commit()
            # Save video
            savevid.save(os.path.join(
                app.root_path, app.config['UPLOAD_FOLDER'], vid_name))
            flash('Posted Successfully')
            return redirect(url_for('home'))
        else:
            flash('*Please add a video to this post')
            return render_template('post.html')
    return render_template('post.html')

# Safe redirecting after login


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
        ref_url.netloc == test_url.netloc

# Sign Up Route


@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'GET':
        return render_template('sign_up.html')
    elif request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password2 = request.form['password2']
        email_check = Users.query.filter_by(email=email).first()
        username_check = Users.query.filter_by(username=username).first()
        if email_check is None and username_check is None:
            if len(username) < 5:
                flash("*Username is too short, username must be more than 5 characters.")
                return render_template('sign_up.html', email=email, first_name=first_name, last_name=last_name, password=password, password2=password2)
            if password != password2:
                flash("*Passwords don't match")
                return render_template('sign_up.html', username=username, email=email, first_name=first_name, last_name=last_name)
            if len(password) < 5:
                flash("*Sorry, password must be more than 5 characters.")
                return render_template('sign_up.html', username=username, email=email, first_name=first_name, last_name=last_name)
            hashed_pw = generate_password_hash(password, 'sha256')
            new_tiktoker = Users(first_name=first_name, last_name=last_name,
                                 username=username, email=email, password=hashed_pw)
            db.session.add(new_tiktoker)
            db.session.commit()
            flash('*User registration successful, you can now login to TikTok')
            return redirect(url_for('login'))
        elif username_check:
            username_message = '*Username - ' + username + \
                ' already taken, please choose another username.'
            flash(username_message)
            return render_template('sign_up.html', email=email, first_name=first_name, last_name=last_name, password=password, password2=password2)
        elif email_check:
            email_message = '*This email - ' + email_check + \
                ' already exists in our database. &nbsp' '<a href="/login">Login here</a>'
            flash(email_message)
            return render_template('sign_up.html', username=username, first_name=first_name, last_name=last_name, password=password, password2=password2)
    return render_template('sign_up.html')

# Login Page


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_or_username = request.form['email_or_username']
        password = request.form['password']
        tik_toker = Users.query.filter_by(email=email_or_username).first(
        ) or Users.query.filter_by(username=email_or_username).first()
        if tik_toker:
            if check_password_hash(tik_toker.password, password):
                login_user(tik_toker)
                flash('Login successful')
                # Redirecting to the intended page before login required.
                next = request.args.get('next')
                if not is_safe_url(next):
                    return abort(400)
                return redirect(next or url_for('home'))
            else:
                flash('*Wrong password')
                return render_template('login.html', email_or_username=email_or_username)
        else:
            email_message = '*This email or username - ' + email_or_username + \
                " doesn't exist in our database, please try again."
            flash(email_message)
            return redirect(url_for('login'))
    return render_template('login.html')

# LogOut


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash('Log out successful')
    return redirect(url_for('home'))


# Profile
@app.route('/profile/<int:id>')
def profile(id):
    if id == 0:
        return render_template('profile.html')
    user_profile = Users.query.get_or_404(id)
    return render_template('profile.html', user_profile=user_profile)

# Comment


@app.route('/comment', methods=['GET', 'POST'])
@login_required
def comment():
    return render_template('comment.html')


# Update User Details
@app.route('/user/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update(id):
    tiktoker_to_update = Users.query.get_or_404(id)
    if id == current_user.id or current_user.id == 1:
        username_check = Users.query.filter(Users.username).first()
        if request.method == 'POST':
            tiktoker_to_update.username = request.form['username']
            tiktoker_to_update.bio = request.form['bio']
            if tiktoker_to_update.username == username_check:
                flash('*That username already exists, choose another username.')
                return render_template('update.html')
            elif tiktoker_to_update.username != username_check:
                # Check for Profile Picture
                if request.files['profile_picture']:
                    tiktoker_to_update.profile_picture = request.files['profile_picture']
                    # Take Image
                    pic_filename = secure_filename(
                        tiktoker_to_update.profile_picture.filename)
                    # Set UUID to change profile pic name to random to avoid duplication.
                    pic_name = str(uuid.uuid1()) + '' + pic_filename
                    # Save Image
                    saver = request.files['profile_picture']
                    # Convert Image to string to save to database
                    tiktoker_to_update.profile_picture = pic_name
                    try:
                        db.session.commit()
                        saver.save(os.path.join(app.root_path,
                                   app.config['UPLOAD_FOLDER'], pic_name))
                        flash('Profile Updated Successfully')
                        return redirect(url_for('profile', tiktoker_to_update=tiktoker_to_update))
                    except:
                        flash(
                            '*That username already exists, choose another username.')
                        return redirect(url_for('profile', tiktoker_to_update=tiktoker_to_update))
                else:
                    db.session.commit()
                    flash('Profile Updated Successfully')
                    return redirect(url_for('profile'))
        return render_template('update.html', tiktoker_to_update=tiktoker_to_update)
    else:
        flash("Access Denied")
        return redirect(url_for('home'))

# Delete User


@app.route('/user/delete/<int:id>')
def delete(id):
    tiktoker_to_delete = Users.query.get_or_404(id)
    if id == current_user.id or current_user.id == 1:
        try:
            db.session.delete(tiktoker_to_delete)
            db.session.commit()
            os.remove(os.path.join(
                app.root_path, app.config['UPLOAD_FOLDER'], tiktoker_to_delete.profile_picture))
            flash('User Deleted Successfully')
            return redirect(url_for('sign_up'))
        except:
            flash('An error occurred')
        return redirect(url_for('sign_up'))
    else:
        flash("Access Denied")
        return redirect(url_for('home'))

# Models
# Tiktok Users


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(500), nullable=False)
    last_name = db.Column(db.String(500), nullable=False)
    username = db.Column(db.String(300), nullable=False, unique=True)
    email = db.Column(db.String(300), nullable=False, unique=True)
    bio = db.Column(db.Text, nullable=True)
    profile_picture = db.Column(db.String(400), nullable=True)
    password = db.Column(db.String(300))
    date_joined = db.Column(db.DateTime(timezone=True), default=func.now())

    # A User can have many posts
    posts = db.relationship('Post', backref='poster', passive_deletes=True)
    likes = db.relationship('Like', backref='user_likes', passive_deletes=True)

    @property
    def password_hash(self):
        raise AttributeError('password is hashed')

    @password_hash.setter
    def password_hash(self, password_hash):
        self.password_hash = generate_password_hash(password_hash)

    def verify_password_hash(self, password_hash):
        return check_password_hash(self.password, password_hash)

    def __repr__(self):
        return '<Name %r>' % self.name


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    date_posted = db.Column(db.DateTime(timezone=True), default=func.now())
    post_vid = db.Column(db.String(400))
    # Foreign Key to Link Users (Going to refer to the primary key of the User)
    poster_id = db.Column(db.Integer, db.ForeignKey(
        'users.id', ondelete="CASCADE"))
    likes = db.relationship('Like', backref='liker', passive_deletes=True)


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    liker_id = db.Column(db.Integer, db.ForeignKey(
        'users.id', ondelete="CASCADE"))
    post_id = db.Column(db.Integer, db.ForeignKey(
        'post.id', ondelete="CASCADE"))
    date_posted = db.Column(db.DateTime(timezone=True), default=func.now())

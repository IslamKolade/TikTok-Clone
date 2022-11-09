import os
from urllib.parse import urlparse, urljoin
from sqlalchemy import desc
from flask import Flask, render_template, request, flash, redirect, url_for, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
import uuid

app = Flask(__name__)
csrf = CSRFProtect(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///TikTok.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["DEBUG"] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'nonsense'
UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_EXTENSIONS'] = ['.mp4', '.mov', '.wmv', '.mkv']
#Initialize Database
db = SQLAlchemy(app)
migrate = Migrate(app,db)

#Flask Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Please login to join Tik Tok"

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

#Routes
@app.route('/', methods = ['GET', 'POST'])
def home():
    posts = Post.query.order_by(desc(Post.id))
    return render_template('home.html', posts=posts)

@app.route('/tiktok/change_password/<int:id>', methods = ['GET', 'POST'])
@login_required
def change_password(id):
    if id == current_user.id:
        if request.method == 'POST':
            old_password = request.form['old_password']
            new_password = request.form['new_password']
            id = current_user.id
            password_to_change = Users.query.get_or_404(id)
            if check_password_hash(password_to_change.password, old_password):
                password_to_change.password = generate_password_hash(new_password, 'sha256')
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

#Delete Post
@login_required
@app.route('/tiktokpost/delete/<int:id>')
def delete_post(id):
    post_to_delete = Post.query.get_or_404(id)
    id = current_user.id
    if id == post_to_delete.poster.id:
        try:
            db.session.delete(post_to_delete)
            db.session.commit()
            flash('Post Deleted Successfully')
            return redirect(url_for('home'))
        except:
            flash('Oops, there was a problem deleting that post. Try again')
            return redirect(url_for('home'))
    else:
        flash("Access Denied")
        return redirect(url_for('home'))


#Full Post
@app.route('/tiktok/fullpost/<int:id>', methods=['GET', 'POST'])
def fullpost(id):
    fullpost = Post.query.get_or_404(id)
    return render_template('fullpost.html', fullpost = fullpost)

#Add Post Page
@app.route('/tiktok/post', methods=['GET','POST'])
def post():
    if request.method == 'POST':
        if request.files['post_vid']:
            content = request.form['content']
            post_vid = request.files['post_vid']
            #Take Video
            vid_filename = secure_filename(post_vid.filename)
            #Set UUID to change post video name to random to avoid duplication.
            vid_name = str(uuid.uuid1()) + '' + vid_filename
            #Save Video
            savevid = request.files['post_vid']
            #Convert Video to string to save to database
            post_vid = vid_name
            poster = current_user.id
            file_ext = os.path.splitext(vid_filename)[1]
            if file_ext not in app.config['UPLOAD_EXTENSIONS']:
                flash('Sorry, we only accept videos.')
                return redirect(url_for('post'))
            post = Post(content=content, poster_id=poster, post_vid=post_vid)
            #Add post to database
            db.session.add(post)
            db.session.commit()
            #Save video
            savevid.save(os.path.join(app.config['UPLOAD_FOLDER'], vid_name))
            flash('Posted Successfully')
            return redirect(url_for('home'))
        else:
            flash('*Please add a video to this post')
            return render_template('post.html')
    return render_template('post.html')

#Safe redirecting after login
def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

#Sign Up Route
@app.route('/tiktok/sign-up', methods= ['GET', 'POST'])
def sign_up():
    if request.method == 'GET':
        return render_template('sign_up.html')
    elif request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password2 = request.form['password2']
        user = Users.query.filter_by(email=email).first()
        username_check = Users.query.filter_by(username=username).first()
        if user is None and username_check is None:
            if len(password) < 5:
                flash("*Password is too short. Password must be up to 5 characters")
                return render_template('sign_up.html',username=username, email=email)
            if password != password2:
                flash("*Passwords don't match")
                return render_template('sign_up.html',username=username, email=email)
            hashed_pw = generate_password_hash(password, 'sha256')
            new_tiktoker = Users(username=username, email=email, password=hashed_pw)
            db.session.add(new_tiktoker)
            db.session.commit()
            flash('*User registration successful, you can now login to TikTok')
            tik_tokers = Users.query.order_by(Users.date_joined) 
            return redirect(url_for('login'))
        elif username_check:
            flash('*Username already exists, choose another username.')
            tik_tokers = Users.query.order_by(Users.date_joined) 
            return render_template('sign_up.html', tik_tokers=tik_tokers)
        elif user:
            flash('*Email already exists' '<p><a href="SignIn" style="color: blue;">Sign In</a></p>')
            tik_tokers = Users.query.order_by(Users.date_joined) 
            return render_template('sign_up.html', tik_tokers=tik_tokers)
    return render_template('sign_up.html')

#Login Page
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email_or_username = request.form['email_or_username']
        password = request.form['password']
        tik_toker = Users.query.filter_by(email=email_or_username).first() or Users.query.filter_by(username = email_or_username).first()
        if tik_toker:
            if check_password_hash(tik_toker.password, password):
                login_user(tik_toker)
                flash('Login successful')
                #Redirecting to the intended page before login required.
                next = request.args.get('next')
                if not is_safe_url(next):
                    return abort(400)
                return redirect(next or url_for('home'))
            else:
                flash('*Wrong password')
                return render_template('login.html',email_or_username=email_or_username)
        else:
            flash("*Incorrect username or email")
            return redirect(url_for('login'))
    return render_template('login.html')

#LogOut
@app.route('/logout', methods = ['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash('Log out successful')
    return redirect(url_for('home'))
        

#Profile
@app.route('/tiktok/profile')
@login_required
def profile():
    return render_template('profile.html')

#Comment
@app.route('/tiktok/comment', methods=['GET','POST'])
@login_required
def comment():
    return render_template('comment.html')


#Update User Details
@app.route('/tiktok/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update(id):
    tiktoker_to_update = Users.query.get_or_404(id)
    if id == current_user.id:
        username_check = Users.query.filter(Users.username).first()
        if request.method == 'POST':
            tiktoker_to_update.username = request.form['username']
            if tiktoker_to_update.username == username_check:
                flash('*That username already exists, choose another username.')
                return render_template('update.html')
            elif tiktoker_to_update.username != username_check:
                try:
                    db.session.commit()
                    flash('Profile Updated Successfully')
                except:
                    flash('*That username already exists, choose another username.')
        return render_template('update.html', tiktoker_to_update = tiktoker_to_update)
    else:
        flash("Access Denied")
        return redirect(url_for('home'))

#Delete User
@app.route('/tiktoker/delete/<int:id>')
def delete(id):
    tiktoker_to_delete = Users.query.get_or_404(id)
    if id == current_user.id:
        try:
            db.session.delete(tiktoker_to_delete)
            db.session.commit()
            flash('User Deleted Successfully')
            return redirect(url_for('sign_up'))
        except:
            flash('An error occurred')
        return redirect(url_for('sign_up'))
    else:
        flash("Access Denied")
        return redirect(url_for('home'))

#Models
#Tiktok Users
class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(300), nullable = False, unique = True)
    email = db.Column(db.String(300), nullable = False, unique = True)
    bio = db.Column(db.Text, nullable=True)
    profile_picture = db.Column(db.String(400), nullable=True)
    password = db.Column(db.String(300))
    date_joined = db.Column(db.DateTime, default=datetime.now())

    #A User can have many posts
    posts = db.relationship('Post', backref = 'poster')

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
    date_posted = db.Column(db.DateTime, default= datetime.now())
    post_vid = db.Column(db.String(400))
    # Foreign Key to Link Users (Going to refer to the primary key of the User)
    poster_id = db.Column(db.Integer, db.ForeignKey('users.id'))
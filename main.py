from flask import Flask, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from functools import wraps
from flask import abort
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
import os

current_year = date.today().year

app = Flask(__name__)
ckeditor = CKEditor(app)
Bootstrap(app)

app.config['SECRET_KEY'] = "8BYkEfBA6O6donWlSihBXox7C0sKR6b"

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL",  "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.config['WTF_CSRF_SECRET_KEY'] = os.environ.get("SECRET_KEY")

# decorators

def admin_only(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return function(*args, **kwargs)
    return decorated_function


login_manager = LoginManager()
login_manager.init_app(app)

# CONFIGURE TABLES

class User(UserMixin, db.Model):  # parent of BlogPost and parent of Comment
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")

    # This will act like a List of Comment objects attached to each User.
    # The "author" refers to the author property in the Comment class.
    comments = relationship("Comment", back_populates="author")


class BlogPost(db.Model):  # child of user and parent of comment
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts property in the User class.
    author = relationship("User", back_populates="posts")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    # This will act like a List of Comment objects attached to each User.
    # The "parent_post" refers to the author property in the Comment class.
    comments = relationship("Comment", back_populates="parent_post")

class Comment(db.Model):  # child of User and BlogPost
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "comments" refers to the comments property in the User class.
    author = relationship("User", back_populates="comments")

    # Create Foreign Key, "blog_posts.id" the users refers to the tablename of Blog.
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    # Create reference to the User object, the "comments" refers to the comments property in the User class.
    parent_post = relationship("BlogPost", back_populates="comments")

    text = db.Column(db.Text, nullable=False)


db.create_all()


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts,
                           logged_in=current_user.is_authenticated, year=current_year, user=current_user)


@app.route('/register', methods=["POST", "GET"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            flash("You have already signed up with this email, log in instead!")
            return redirect(url_for('login'))
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data),
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(user=new_user)
        return redirect(url_for("get_all_posts"))
    return render_template("register.html", form=form,  logged_in=current_user.is_authenticated, year=current_year)


@app.route('/login', methods=["POST", "GET"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()
        if not user:
            flash("That email does not exist, try it again!")
            return redirect("login")
        elif not check_password_hash(user.password, password):
            flash("Incorrect Password, try it again")
            return redirect("login")
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=form, logged_in=current_user.is_authenticated, year=current_year)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))

@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False,
                        force_lower=False, use_ssl=False, base_url=None)
    requested_post = BlogPost.query.get(post_id)
    form = CommentForm()
    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                author=current_user,
                text=form.comment.data,
                parent_post=requested_post,
            )
            db.session.add(new_comment)
            db.session.commit()
        else:
            flash("You need to login or register to comment!")
            return redirect(url_for('login'))
    return render_template("post.html", post=requested_post, form=form, gravatar=gravatar,
                           user=current_user,  logged_in=current_user.is_authenticated, year=current_year)


@app.route("/about")
def about():
    return render_template("about.html",  logged_in=current_user.is_authenticated, year=current_year)


@app.route("/contact")
def contact():
    return render_template("contact.html",  logged_in=current_user.is_authenticated, year=current_year)

@app.route("/new-post", methods=["POST", "GET"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form,
                           is_edit=False,  logged_in=current_user.is_authenticated, year=current_year)


@app.route("/edit-post/<int:post_id>", methods=["POST", "GET"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body,
        author=current_user,
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, is_edit=True,
                           logged_in=current_user.is_authenticated, year=current_year)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

@app.route("/delete-comment/<int:comment_id>")
@admin_only
def delete_comment(comment_id):
    comment_to_delete = Comment.query.get(comment_id)
    db.session.delete(comment_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

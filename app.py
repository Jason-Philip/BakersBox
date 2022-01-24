import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html") 


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # check if email already exists in db
        existing_user = mongo.db.users.find_one(
            {"email": request.form.get("email").lower()})

        if existing_user:
            flash("Email already Used")
            return redirect(url_for("register"))

        # check if name already exists in db
        existing_user = mongo.db.users.find_one(
            {"name": request.form.get("name").lower()})

        if existing_user:
            flash("Name already Used")
            return redirect(url_for("register"))
        
        # check passwords are the same
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        if password != confirm_password:
            flash("Passwords did not match, please try again")
            return redirect(url_for("register"))

        register = {
            "email": request.form.get("email").lower(),
            "name": request.form.get("name").lower(),
            "password": generate_password_hash(request.form.get("password")),
            "own_recipes": [],
            "planned_recipes": [],
            "tried_recipes": []
        }
        mongo.db.users.insert_one(register)

        # put the new user into 'session' cookie
        session["user"] = request.form.get("name")
        flash("Registration Successful!")
        return redirect(url_for("profile", name=session["user"]))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # check if username exists in db
        existing_user = mongo.db.users.find_one(
            {"name": request.form.get("name").lower()})

        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                        session["user"] = request.form.get("name").lower()
                        flash("Welcome, {}".format(
                            request.form.get("name")))
                        return redirect(url_for(
                            "profile", name=session["user"]))
            else:
                # invalid password match
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            # username doesn't exist
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/profile/<name>", methods=["GET", "POST"])
def profile(name):
    # grab the session user's username from db
    if session["user"]:
        recipes = list(mongo.db.recipes.find())
        user = mongo.db.users.find_one({
            "name": session["user"]
        })

        recipes_owned = []

        for recipe_id in user["own_recipes"]:
            recipes_owned.append(mongo.db.recipes.find_one(
                {"_id": ObjectId(recipe_id)}))

        return render_template("my_box.html", name=name, own_recipes=recipes_owned)

    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    # remove user from session cookie
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("login"))


@app.route("/create_recipe", methods=["GET", "POST"])
def create_recipe():
    if request.method == "POST":
        user = mongo.db.users.find_one({"name": session["user"]})
        #create new recipe
        new_recipe = {
            "recipe_name": request.form.get("recipe_name").lower(),
            "prep": request.form.get("prep"),
            "cook_time": request.form.get("cook_time"),
            "serves": request.form.get("serves"),
            "cals": request.form.get("cals"),
            "vegan": request.form.get("vegan"),
            "ingredients": request.form.get("ingredients"),
            "steps": request.form.get("steps"),
            "added_by": session["user"]
        }
        mongo.db.recipes.insert_one(new_recipe)

        mongo.db.users.update_one(
            user, {"$push": {"own_recipes": str(new_recipe["_id"])}})

        return redirect(url_for("profile", name=session["user"]))
    return render_template("create_recipe.html")


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
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
    """
    Displays the home page
    """
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Registers a new user if both email and name are unique
    """
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
        }
        mongo.db.users.insert_one(register)

        # put the new user into 'session' cookie
        session["user"] = request.form.get("name")
        flash("Registration Successful!")
        return redirect(url_for("profile", name=session["user"]))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Allows a registerred user to login
    if valid and will prevent if not
    """
    if request.method == "POST":
        # check if name exists in db
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
            # name doesn't exist
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/profile/<name>", methods=["GET", "POST"])
def profile(name):
    """
    Displays the personalised content
    of the user for them to interact with
    """
    # grab the session user's username from db
    if session["user"]:
        recipes = list(mongo.db.recipes.find())
        user = mongo.db.users.find_one({
            "name": session["user"]
        })

        recipes_owned = []
        recipes_planned = []

        for recipe_id in user["own_recipes"]:
            recipes_owned.append(mongo.db.recipes.find_one(
                {"_id": ObjectId(recipe_id)}))

        for recipe_id in user["planned_recipes"]:
            recipes_planned.append(mongo.db.recipes.find_one(
                {"_id": ObjectId(recipe_id)}))

        return render_template("my_box.html"
                               name=name,
                               own_recipes=recipes_owned,
                               recipes_planned=recipes_planned)

    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    """
    Removes user from session cookie
    """
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("login"))


@app.route("/create_recipe", methods=["GET", "POST"])
def create_recipe():
    """
    Creates a new recipes and
    adds the recipe to users owned recipes array
    """
    if request.method == "POST":
        user = mongo.db.users.find_one({"name": session["user"]})

        # create new recipe
        new_recipe = {
            "recipe_name": request.form.get("recipe_name").lower(),
            "cat": request.form.getlist("cat"),
            "prep": request.form.get("prep"),
            "cook_time": request.form.get("cook_time"),
            "serves": request.form.get("serves"),
            "cals": request.form.get("cals"),
            "ingredients": request.form.get("ingredients"),
            "steps": request.form.get("steps"),
            "added_by": session["user"]
        }
        mongo.db.recipes.insert_one(new_recipe)

        mongo.db.users.update_one(
            user, {"$push": {"own_recipes": str(new_recipe["_id"])}})

        return redirect(url_for("profile", name=session["user"]))
    return render_template("create_recipe.html")


@app.route("/recipe_view/<recipe_id>", methods=["GET", "POST"])
def recipe_view(recipe_id):
    """
    Displays a unique recipe for viewing.
    """
    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})

    check = str(recipe["_id"])

    if "user" in session:
        user = mongo.db.users.find_one({"name": session["user"]})

        return render_template("recipe.html", recipe=recipe, user=user,
                               check=check)

    return render_template("recipe.html", recipe=recipe, check=check)


@app.route("/search", methods=["GET", "POST"])
def search():
    """
    User can choose to search by name or by
    category by dropdown selection, all
    bakes will be displayed underneath otherwise
    """
    recipes = list(mongo.db.recipes.find())
    # checks if user is logged in.
    if "user" in session:
        user = mongo.db.users.find_one(
            {"name": session["user"]})
        return render_template("search.html", recipes=recipes,
                               user=user)

    return render_template("search.html", recipes=recipes)


@app.route("/search/search_cakes", methods=["GET", "POST"])
def search_cakes():
    """
    User has searched by Cakes category
    """
    category_recipe = []
    recipes = list(mongo.db.recipes.find())

    for caketry in recipes:
        if "cakes" in caketry["cat"]:
            category_recipe.append(caketry)

    recipes = list(mongo.db.recipes.find())
    # checks if user is logged in.
    if "user" in session:
        user = mongo.db.users.find_one(
            {"name": session["user"]})
        return render_template("search.html", recipes=category_recipe,
                               user=user)

    return render_template("search.html", recipes=category_recipe)


@app.route("/search/search_traybakes", methods=["GET", "POST"])
def search_traybakes():
    """
    User has searched by Traybakes category
    """
    category_recipe = []
    recipes = list(mongo.db.recipes.find())

    for traybake in recipes:
        if "traybakes" in traybake["cat"]:
            category_recipe.append(traybake)

    recipes = list(mongo.db.recipes.find())
    # checks if user is logged in.
    if "user" in session:
        user = mongo.db.users.find_one(
            {"name": session["user"]})
        return render_template("search.html", recipes=category_recipe,
                               user=user)

    return render_template("search.html", recipes=category_recipe)


@app.route("/search/search_muffins", methods=["GET", "POST"])
def search_muffins():
    """
    User has searched by Muffins category
    """
    category_recipe = []
    recipes = list(mongo.db.recipes.find())

    for muffin in recipes:
        if "muffins" in muffin["cat"]:
            category_recipe.append(muffin)

    recipes = list(mongo.db.recipes.find())
    # checks if user is logged in.
    if "user" in session:
        user = mongo.db.users.find_one(
            {"name": session["user"]})
        return render_template("search.html", recipes=category_recipe,
                               user=user)

    return render_template("search.html", recipes=category_recipe)


@app.route("/search/search_vegan", methods=["GET", "POST"])
def search_vegan():
    """
    User has searched by vegan category
    """
    category_recipe = []
    recipes = list(mongo.db.recipes.find())

    for vegan in recipes:
        if "vegan" in vegan["cat"]:
            category_recipe.append(vegan)

    recipes = list(mongo.db.recipes.find())
    # checks if user is logged in.
    if "user" in session:
        user = mongo.db.users.find_one(
            {"name": session["user"]})
        return render_template("search.html", recipes=category_recipe,
                               user=user)

    return render_template("search.html", recipes=category_recipe)


@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    """
    Similar to the create recipe form but updates for
    an existing recipe replacing old content
    with new.
    """
    if "user" in session:
        # Set out unique properties
        recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
        user = mongo.db.users.find_one({"name": session["user"]})

        if request.method == "POST":
            updated = {
                "recipe_name": request.form.get("recipe_name").lower(),
                "cat": request.form.getlist("cat"),
                "prep": request.form.get("prep"),
                "cook_time": request.form.get("cook_time"),
                "serves": request.form.get("serves"),
                "cals": request.form.get("cals"),
                "ingredients": request.form.get("ingredients"),
                "steps": request.form.get("steps"),
                "added_by": session["user"]
            }
            mongo.db.recipes.update(recipe, updated)
            flash("Recipe Has Been Editted Successfully")

            return redirect(url_for("profile", name=session["user"]))
        return render_template("edit_recipe.html", recipe=recipe, user=user)


@app.route("/delete_recipe/<recipe_id>", methods=["GET", "POST"])
def delete_recipe(recipe_id):
    """
    Removes recipe from recipes and 
    removes links with users
    """
    if "user" in session:
        # Set out unique properties

        recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})

        all_users = list(mongo.db.users.find())

        for a_user in all_users:
            if str(recipe["_id"]) in a_user["planned_recipes"]:
                mongo.db.users.update_one(a_user, {"$pull":
                                          {"planned_recipes":
                                           str(recipe["_id"])}})

        user = mongo.db.users.find_one({"name": session["user"]})

        mongo.db.users.update_one(user, {"$pull":
                                  {"own_recipes": str(recipe["_id"])}})

        mongo.db.recipes.remove({"_id": ObjectId(recipe_id)})
        flash("Recipe Has Been Deleted Successfully")

        return redirect(url_for("profile", name=session["user"]))


@app.route("/plan_recipe/<recipe_id>", methods=["GET", "POST"])
def plan_recipe(recipe_id):
    """
    button in recipe to plan a bake
    adds the bake to My baking Box
    Planning area
    """

    user = mongo.db.users.find_one({"name": session["user"]})
    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})

    mongo.db.users.update_one(
        user, {"$push": {"planned_recipes": str(recipe["_id"])}})

    return redirect(url_for("recipe_view", recipe_id=recipe_id))


@app.route("/remove_plan/<recipe_id>", methods=["GET", "POST"])
def remove_plan(recipe_id):
    """
    button in recipe to remove a planned
    bake
    """
    user = mongo.db.users.find_one({"name": session["user"]})
    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})

    mongo.db.users.update_one(user, {"$pull":
                              {"planned_recipes": str(recipe["_id"])}})

    return redirect(url_for("recipe_view", recipe_id=recipe_id))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=False)

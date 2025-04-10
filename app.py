import datetime
from flask import Flask, render_template, redirect, url_for, request, session, jsonify, flash
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/finesdb"  # Replace with your MongoDB URI
app.secret_key = "#Fines@67"  # Replace with a strong secret key
mongo = PyMongo(app)

# Import and Register the Blueprint
from admin import admin_bp  # Import the blueprint
app.register_blueprint(admin_bp)  # Register it with the app


@app.route("/")
def index():
    return render_template('index.html')

@app.route('/get_fine_amount/<category>')
def get_fine_amount(category):
    fine_category = mongo.db.fine_categories.find_one({'type': category})
    if fine_category:
        return jsonify({'amount': fine_category['amount']})
    else:
        return jsonify({'amount': None})


if __name__ == '__main__':
    app.run(debug=True)
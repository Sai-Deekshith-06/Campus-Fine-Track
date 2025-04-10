import datetime
from flask import *
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from admin import admin_bp  # Import the blueprint

app.register_blueprint(admin_bp)  # Register it with the app
app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/finesdb"
app.secret_key = "your_secret_key_here"
mongo = PyMongo(app)

@app.route("/")
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
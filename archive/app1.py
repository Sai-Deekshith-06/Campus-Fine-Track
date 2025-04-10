from flask import *
from werkzeug.security import generate_password_hash, check_password_hash
from flask_pymongo import PyMongo

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/finesdb" # Replace with your MongoDB connection string
app.secret_key = "your_secret_key_here"
mongo = PyMongo(app)


@app.route("/admin/login",methods = ["GET","POST"])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('uname')
        password = request.form.get('pswd')
        error = None

        if username and password:
            admin = mongo.db.administrators.find_one({'username': username})
            if admin and check_password_hash(admin['password'], password):
                session['admin_id'] = str(admin['_id'])  # Store admin's ID in session
                return redirect(url_for('admin_home')) # Redirect to the admin home page (which we'll create later)
            else:
                error = 'Invalid username or password'
        else:
            error = 'Please enter both username and password'

    return render_template('login.html', error=error)

@app.route('/admin/home',methods=[])
def admin_home():
    return render_template_string('<h2>login success</h2>')


if __name__ == '__main__':
    app.run(debug=True)
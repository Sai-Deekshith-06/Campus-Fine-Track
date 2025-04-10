import datetime
from flask import *
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from bson.objectid import ObjectId

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/finesdb"
app.secret_key = "your_secret_key_here"
mongo = PyMongo(app)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('uname')
        password = request.form.get('pswd')
        print(f"Username: {username}, Password: {password}")  # Debugging line

        if username and password:
            admin = mongo.db.admin.find_one({'username': username})
            print(f"Admin found: {admin}")  # Debugging line
            print(f"Password hash: {admin['password'] if admin else 'No admin found'}")  # Debugging line
            if admin and check_password_hash(admin['password'], password):
                session['admin_id'] = str(admin['_id'])
                return redirect(url_for('admin_home'))
            else:
                error = 'Invalid username or password'
        else:
            error = 'Please enter both username and password'

        return render_template('login.html', error=error)

    return render_template('login.html')

@app.route("/admin/home")
def admin_home():
    if 'admin_id' in session:
        return render_template('admin_home.html')
        # return "Welcome to the Admin Home Page!"
    else:
        return redirect(url_for('admin_login'))

@app.route('/admin/newentry', methods=['GET'])
def admin_new_fine_form():
    fine_categories = mongo.db.fine_categories.find()
    categories_list = list(fine_categories)  # Convert cursor to a list for printing
    print(f"Fine Categories fetched: {categories_list}")
    return render_template('admin_new_fine.html', fine_categories=categories_list)

@app.route('/admin/newentry', methods=['POST'])
def admin_create_fine():
    student_id = request.form.get('student_id')
    fine_category = request.form.get('fine_category')
    reason = request.form.get('reason')
    amount = request.form.get('amount')
    if(amount == ""):
        amount = 0.0
    else:
        amount = float(amount)
    due_date = request.form.get('due_date')
    print(f"\nStudent ID: {student_id}, Fine Category: {fine_category}, Reason: {reason}, Amount: {amount}, Due Date: {due_date}\n")  # Debugging line
    # Validate the input data

    student = mongo.db.students.find_one({'id': student_id})
    if student:
        new_fine = {
            'student_id': student['_id'],
            'fine_category': fine_category,
            'reason': reason,
            'amount': amount,
            'due_date': due_date,
            'issue_date': datetime.datetime.now().strftime('%Y-%m-%d'),
            'status': 'pending'
        }

        mongo.db.fines.insert_one(new_fine)  #  Corrected: Use mongo.db

        return redirect(url_for('admin_home'))
    else:
        return "Student not found", 400
    
@app.route('/admin/get_fine_amount/<category>')
def get_fine_amount(category):
    fine_category = mongo.db.fine_categories.find_one({'type': category})
    if fine_category:
        return jsonify({'amount': fine_category['amount']})
    else:
        return jsonify({'amount': None})

@app.route('/admin/fines')
def admin_view_fines():
    if 'admin_id' in session:
        fines = list(mongo.db.fines.find())  # Fetch all fines
        for fine in fines:
            student = mongo.db.students.find_one({'_id': fine['student_id']})
            if student:
                fine['student_name'] = student['name']  # Add student name to fine data
            else:
                fine['student_name'] = 'Unknown'
        return render_template('admin_view_fines.html', fines=fines)
    else:
        return redirect(url_for('admin_login'))
    
@app.route('/admin/fines/<fine_id>/pay', methods=['POST'])
def accept_payment(fine_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    try:
        result = mongo.db.fines.update_one(
            {'_id': ObjectId(fine_id)},
            {'$set': {'status': 'paid'}}
        )
        if result.modified_count > 0:
            return jsonify({'message': 'Payment accepted'}), 200
        else:
            return jsonify({'message': 'Fine not found'}), 404
    except Exception as e:
        print(f"Error accepting payment: {e}")
        return jsonify({'message': 'Error accepting payment'}), 500

if __name__ == '__main__':
    app.run(debug=True)
# admin.py
from flask import Blueprint, render_template, redirect, url_for, request, session, jsonify, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# MongoDB Connection (moved outside functions for efficiency)
client = MongoClient('mongodb://localhost:27017/')  # Replace with your MongoDB connection string
db = client.finesdb


@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    message = None
    if request.method == 'POST':
        username = request.form.get('uname')
        password = request.form.get('pswd')

        if username and password:
            admin = db.admin.find_one({'username': username})
            if admin and check_password_hash(admin['password'], password):
                session['admin_id'] = str(admin['_id'])
                return redirect(url_for('admin.admin_home'))  # Use the blueprint name
            else:
                message = 'Invalid username or password'
        else:
            message = 'Enter both username and password'

        return render_template('index.html', message=message)

    return redirect(url_for('admin.admin_home'))


@admin_bp.route('/home')
def admin_home():
    if 'admin_id' in session:
        return render_template('admin_home.html')
    else:
        return redirect(url_for('admin.admin_login'))


@admin_bp.route('/newentry', methods=['GET'])
def admin_new_fine_form():
    fine_categories = list(db.fine_categories.find())
    return render_template('admin_new_fine.html', fine_categories=fine_categories)


@admin_bp.route('/newentry', methods=['POST'])
def admin_create_fine():
    student_id = request.form.get('student_id')
    fine_category = request.form.get('fine_category')
    reason = request.form.get('reason')
    amount = float(request.form.get('amount'))
    due_date = request.form.get('due_date')

    student = db.students.find_one({'id': student_id})  # Assuming 'id' is the correct field
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
        db.fines.insert_one(new_fine)
        return redirect(url_for('admin.admin_view_fines'))
    else:
        # flash('Student not found', 'error')  # Use flash for user feedback
        message = 'Student not found'
        return redirect(url_for('admin.admin_new_fine_form'))


@admin_bp.route('/get_student_email/<student_id>', methods=['GET'])
def get_student_email(student_id):
    student = db.students.find_one({'id': student_id})
    if student:
        return jsonify({'email': student['email']})  # Or however your email field is named
    else:
        return jsonify({'email': None})


@admin_bp.route('/fines')
def admin_view_fines():
    if 'admin_id' in session:
        query = {}

        # Search by Student ID
        student_id = request.args.get('student_id')
        student = db.students.find_one({'id': student_id}) if student_id else None
        if student:
            query['student_id'] = student['_id']  # Add student_id to the query
        else:
            student_id = ""

        # Filter by Category
        fine_category = request.args.get('fine_category')
        if fine_category:
            query['fine_category'] = fine_category

        # Filter by Due Date
        due_date = request.args.get('due_date')
        if due_date:
            query['due_date'] = due_date

        # Filter by Status
        status = request.args.get('status')
        if status:
            query['status'] = status

        fines = list(db.fines.find(query).limit(75))

        for fine in fines:
            student = db.students.find_one({'_id': fine['student_id']})  # Assuming 'id' is the correct field
            if student:
                fine['student_name'] = student['name']
            else:
                fine['student_name'] = 'Unknown'

        fine_categories = list(db.fine_categories.find())
        fines.reverse()
        return render_template('admin_view_fines.html', fines=fines, fine_categories=fine_categories, std_id=student_id)
    else:
        return redirect(url_for('admin.admin_login'))

@admin_bp.route('/fines/<fine_id>/delete', methods=['POST'])
def delete_fine(fine_id):
    try:
        result = db.fines.delete_one({'_id': ObjectId(fine_id)}) 
        if result.deleted_count:
            flash("Deleted Successfully!","1")
        else:
            flash("Error!! Fine not found","0")
    except Exception as e:
        flash(f"Error deleting fine: {e} ", "0")
    return redirect(url_for('admin.admin_view_fines'))



@admin_bp.route('/fines/<fine_id>/pay', methods=['POST'])
def accept_payment(fine_id):
    if 'admin_id' not in session:
        return redirect(url_for('index'))  # Or wherever your main page is

    try:
        result = db.fines.update_one(
            {'_id': ObjectId(fine_id)},
            {'$set': {'status': 'paid'}}
        )
        if result.modified_count > 0:
            flash('Payment accepted', '1')  # Use flash for success message
        else:
            flash('Fine not found or already paid', '0')  # Use flash for warning
    except Exception as e:
        print(f"Error accepting payment: {e}")
        flash('Error accepting payment', '0')  # Use flash for error

    return redirect(url_for('admin.admin_view_fines'))
  

@admin_bp.route('/logout')
def admin_logout():
    session.pop('admin_id', None)
    return redirect(url_for('index'))
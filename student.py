#   student.py
from flask import Blueprint, render_template, redirect, url_for, request, session, jsonify, flash
from pymongo import MongoClient
from bson.objectid import ObjectId

student_bp = Blueprint('student', __name__, url_prefix='/student')

client = MongoClient('mongodb://localhost:27017/')
db = client.finesdb

@student_bp.route('/search', methods=['POST'])
def student_search():
    student_id = request.form.get('student_id')  # Consistent variable name
    if student_id:
        student = db.students.find_one({'id': student_id})
        if student:
            return redirect(url_for('student.get_student_fines', student_id=student_id))  # Correct url_for
        else:
            message = 'Student not found.'
    else:
        message = 'Please enter a Student ID.'
    return render_template('index.html', message=message)

@student_bp.route('/<string:student_id>/fines', methods=['GET'])
def get_student_fines(student_id): 
    query = {}
    
    student = db.students.find_one({'id': student_id}) if student_id else None
    if student:
        query['student_id'] = student['_id']
    fines = list(db.fines.find(query))
    obj_id = db.fines.find(query).limit(1)

    print(student_id, student['name'] if student else "error in finding")
    print(obj_id)
    if student:
        print(student['_id'])
    # print(fines)
    for fine in fines:
        fine['_id'] = str(fine['_id'])
    return render_template('student_fines.html', fines=fines)
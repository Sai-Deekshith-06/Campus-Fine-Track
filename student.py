# input_file_1.py (student.py) - Modified
from flask import Blueprint, render_template, redirect, url_for, request, session, jsonify, flash, current_app
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId
import datetime
import json
import os
from dotenv import load_dotenv

student_bp = Blueprint('student', __name__, url_prefix='/student')
load_dotenv()
client = MongoClient(os.environ.get('MONGO_URI'))
db = client.finesdb


@student_bp.route('/search', methods=['POST'])
def student_search():
     
    if db is None:
        flash('Database connection error.', '0')
        return render_template('index.html')

    student_id_str = request.form.get('student_id', '').strip()
    if not student_id_str:
        flash('Please enter your Student ID (Roll No).', '0')
        return render_template('index.html')

    try:
        # Validate student ID format (example: 23B81A05H1)
        # Add specific regex if needed: pattern = r"^[0-9]{2}[A-Z]{1}[0-9]{1}[A-Z]{1}[0-9]{1}[A-Z0-9]{2}$"
        # if not re.match(pattern, student_id_str):
        #     flash('Invalid Student ID format.', '0')
        #     return render_template('index.html')

        student = db.students.find_one({'id': student_id_str})
        if student:
            # Store student id in session for retrieval on the fines page? Optional.
            # session['viewing_student_id'] = student_id_str
            return redirect(url_for('student.get_student_fines', student_id_str=student_id_str))
        else:
            flash(f'Student ID {student_id_str} not found.', '0')
            return render_template('index.html')
    except Exception as e:
        print(f"Error searching student {student_id_str}: {e}")
        flash('An error occurred during student search.', '0')
        return render_template('index.html')


@student_bp.route('/<string:student_id_str>/fines', methods=['GET'])
def get_student_fines(student_id_str):
     
    if db is None:
        flash('Database connection error.', '0')
        # Where to redirect? Maybe a dedicated error page or back to index?
        return redirect(url_for('index'))

    student_name = "Unknown"
    fines = []
    try:
        # Find student by the string ID (roll number)
        student = db.students.find_one({'id': student_id_str})

        if student:
            student_name = student.get('name', 'N/A')
            # Find fines using the student's MongoDB _id
            # query = {'student_db_id': student['_id']} # More robust
            # Or query by the string id if consistently stored
            query = {'student_id_str': student_id_str}
            fines = list(db.fines.find(query).sort('due_date', 1)) # Sort by due date ascending

            # Convert ObjectId to string for template compatibility (JSON serialization)
            for fine in fines:
                fine['_id'] = str(fine['_id'])
                # Ensure amount is formatted nicely? Optional.
                # fine['amount_display'] = f"{fine.get('amount', 0):.2f}"

        else:
            # If student ID was valid but not found in DB (unlikely if search worked)
            flash(f'Student ID {student_id_str} not found.', '0')
            # Redirect to index as they shouldn't be here
            return redirect(url_for('index'))

    except Exception as e:
        print(f"Error fetching fines for student {student_id_str}: {e}")
        flash('An error occurred while retrieving fines.', '0')
        # Allow rendering the page with empty fines list and student name?
        # Or redirect? Let's allow rendering for now.

    return render_template('student_fines.html',
                           fines=fines,
                           student_name=student_name,
                           student_id_str=student_id_str)


# Removed the '/<string:student_id>/pay' GET route for show_payment_form
# Payment form is now integrated into student_fines.html pop-up


@student_bp.route('/<string:student_id_str>/pay', methods=['POST'])
def process_payment(student_id_str):

    if db is None:
        flash('Database connection error.', '0')
        return redirect(url_for('student.get_student_fines', student_id_str=student_id_str))

    transaction_id = request.form.get('transaction_id', '').strip()
    selected_fine_ids_json = request.form.get('selected_fine_ids')  # Expecting JSON array of strings

    # --- Validation ---
    if not transaction_id:
        flash('Transaction ID is required.', '0')
        return redirect(url_for('student.get_student_fines', student_id_str=student_id_str))

    if not selected_fine_ids_json:
        flash('No fines selected for payment.', '0')
        return redirect(url_for('student.get_student_fines', student_id_str=student_id_str))

    try:
        selected_fine_ids_str = json.loads(selected_fine_ids_json)
        if not isinstance(selected_fine_ids_str, list) or not selected_fine_ids_str:
            raise ValueError("Selected fines data is not a valid list.")
        # Convert string IDs to ObjectIds
        object_ids_to_pay = [ObjectId(fine_id) for fine_id in selected_fine_ids_str]

    except (json.JSONDecodeError, ValueError, InvalidId) as e:
        print(f"Error processing payment data for {student_id_str}: {e}")
        flash('Invalid data submitted for selected fines.', '0')
        return redirect(url_for('student.get_student_fines', student_id_str=student_id_str))

    # --- Process Payment Submission ---
    try:
        # Find the student's MongoDB _id (using the 'id' field in the students collection)
        student = db.students.find_one({'id': student_id_str}, {'_id': 1})
        if not student:
            flash(f'Student {student_id_str} not found.', '0')
            return redirect(url_for('index'))
        student_db_id = student['_id']

        # Verify selected fines belong to the student (using 'student_id' in fines) and are 'pending'
        fines_to_pay = list(db.fines.find({
            '_id': {'$in': object_ids_to_pay},
            'student_id': student_db_id,  # <--- CORRECTED FIELD NAME
            'status': 'pending'
        }))

        print(f"Fines to pay: {fines_to_pay}")  # Debugging
        print(f"\nObject IDs to pay: {object_ids_to_pay}")  # Debugging

        if len(fines_to_pay) != len(object_ids_to_pay):
            # This means some selected IDs were invalid, didn't belong to the student, or weren't pending
            flash('Some selected fines could not be processed (might be already paid, pending approval, or invalid). Please refresh and try again.', '0')
            return redirect(url_for('student.get_student_fines', student_id_str=student_id_str))

        if not fines_to_pay:
            # Should be caught above, but as a safeguard
            flash('No valid pending fines found for payment.', '0')
            return redirect(url_for('student.get_student_fines', student_id_str=student_id_str))

        # --- Update Fine Status ---
        # Change status to 'pending_approval' and store transaction ID
        update_result = db.fines.update_many(
            {'_id': {'$in': object_ids_to_pay},
             'student_id': student_db_id,  # <--- CORRECTED FIELD NAME
             'status': 'pending'},
            {'$set': {
                'status': 'pending_approval',
                'transaction_id': transaction_id,
                'last_updated': datetime.datetime.now()
            }}
        )

        if update_result.modified_count > 0:
            flash(f'Payment submitted for {update_result.modified_count} fines. Awaiting admin approval.', '1')

            #  Create a record in the 'transactions' collection
            total_amount = sum(fine.get('amount', 0) for fine in fines_to_pay)  # Calculate total amount
            db.transactions.insert_one({
                'transaction_id': transaction_id,
                'student_db_id': student_db_id,
                'student_id_str': student_id_str,
                'fine_ids': object_ids_to_pay,  # Store ObjectIds
                'amount': total_amount,
                'submission_date': datetime.datetime.now(),
                'status': 'pending_approval'
            })
            print("Transaction recorded successfully.")  # Debugging
        else:
            # This case should ideally not happen due to checks above
            flash('No fines were updated. Please check the transaction status or contact support.', '0')

    except Exception as e:
        print(f"Error processing payment for student {student_id_str}, tx {transaction_id}: {e}")
        flash(f'An error occurred while processing your payment: {e}', '0')

    return redirect(url_for('student.get_student_fines', student_id_str=student_id_str))
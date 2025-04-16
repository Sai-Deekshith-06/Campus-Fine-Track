# input_file_0.py (admin.py) - Modified
from flask import Blueprint, render_template, redirect, url_for, request, session, jsonify, flash, current_app
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from bson.errors import InvalidId
import datetime
from flask_mail import Message # Import Message
import re # For batch extraction
import pprint
import os
from dotenv import load_dotenv

load_dotenv()
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
client = MongoClient(os.environ.get('MONGO_URI'))  # Replace with your MongoDB connection string
db = client.finesdb

# Helper function for sending emails
def send_email(subject, recipients, body):
    mail = current_app.config.get('MAIL_INSTANCE')
    # print(recipients,"is redirected to",end=" ") # Debugging: Check recipients
    # recipients = os.environ.get('MAIL_DEFAULT_SENDER')
    print(recipients) # Debugging: Check recipients
    if not mail or current_app.config.get('MAIL_SUPPRESS_SEND'):
        print(f"Mail suppressed or not configured. Subject: {subject}, To: {recipients}")
        print(f"Body:\n{body}")
        return False # Indicate email not sent

    if not isinstance(recipients, list):
        recipients = [recipients]

    try:
        msg = Message("Trial Mail: "+subject, recipients=recipients)
        msg.body = body
        # msg.html = "<p>HTML version of the body</p>" # Optional HTML body
        mail.send(msg)
        print(f"Email sent to {recipients} with subject: {subject}")
        return True
    except Exception as e:
        print(f"Error sending email to {recipients}: {e}")
        flash(f'Error sending email notification: {e}', '0')
        return False


@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    
    if db is None:
        flash('Database connection error.', '0')
        return render_template('index.html') # Or an error page

    if request.method == 'POST':
        username = request.form.get('uname')
        password = request.form.get('pswd')

        if not username or not password:
            flash('Enter both username and password', '0')
            return render_template('index.html')

        try:
            admin = db.admin.find_one({'username': username})
            if admin and check_password_hash(admin.get('password', ''), password): # Use .get for safety
                session['admin_id'] = str(admin['_id'])
                session['admin_name'] = admin.get('username')
                session['admin_role'] = admin.get('role')
                print(f"Admin ID: {session['admin_id']} logged in")
                print("Session before save:", session.items())
                flash('Login successful', '1')
                return redirect(url_for('admin.admin_home'))
            else:
                flash('Invalid username or password', '0')
        except Exception as e:
            print(f"Error during admin login: {e}")
            flash('An error occurred during login. Please try again.', '0')

        return render_template('index.html') # Show login form again on failure

    # If GET request, redirect to home if already logged in, else show login
    if 'admin_id' in session:
        return redirect(url_for('admin.admin_home'))
    return render_template('index.html') # Show login form


@admin_bp.route('/home')
def admin_home():
    if 'admin_id' not in session:
        flash('Login required', '0')
        return redirect(url_for('index'))

    analytics_data = {}
    try:
        # --- Analytics Calculations (same as in admin_analytics) ---
        analytics_data['total_collected'] = db.fines.aggregate([
            {'$match': {'status': 'paid'}},
            {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
        ]).next().get('total', 0)

        analytics_data['total_pending'] = db.fines.count_documents({'status': 'pending'})

        category_pipeline = [
            {'$group': {'_id': '$category', 'count': {'$sum': 1}}}
        ]
        analytics_data['fines_by_category'] = list(db.fines.aggregate(category_pipeline))

        status_pipeline = [
            {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
        ]
        analytics_data['fines_by_status'] = list(db.fines.aggregate(status_pipeline))

        # 5. Fines by Batch/Year (Count and Amount)
        # Requires extracting year from student_id_str (e.g., '23' from '23B81A...')
        batch_pipeline = [
            {'$project': {
                'amount': 1,
                'batch_year': {'$substr': ['$student_id_str', 0, 2]} # Extract first 2 chars
            }},
            {'$match': {'batch_year': {'$regex': '^[0-9]{2}$'}}}, # Ensure it's a 2-digit year
            {'$group': {
                '_id': '$batch_year',
                'count': {'$sum': 1},
                'total_amount': {'$sum': '$amount'}
            }},
            {'$sort': {'_id': 1}} # Sort by year
        ]
        analytics_data['fines_by_batch'] = list(db.fines.aggregate(batch_pipeline))

        monthly_pipeline = [
             {'$project': {
                 'issue_month': {'$substr': ['$issue_date', 0, 7]}
             }},
             {'$group': {'_id': '$issue_month', 'count': {'$sum': 1}}},
             {'$sort': {'_id': 1}}
        ]
        analytics_data['fines_by_month'] = list(db.fines.aggregate(monthly_pipeline))

    except Exception as e:
        print(f"Error generating analytics: {e}")
        flash(f'Error generating analytics data: {e}', '0')
        # Set defaults or empty structures if error occurs
        analytics_data.setdefault('total_collected', 0)
        analytics_data.setdefault('total_pending', 0)
        analytics_data.setdefault('fines_by_category', [])
        analytics_data.setdefault('fines_by_status', [])
        analytics_data.setdefault('fines_by_batch', [])
        analytics_data.setdefault('fines_by_month', [])

    return render_template('admin_home.html', data=analytics_data)


@admin_bp.route('/newentry', methods=['GET'])
def admin_new_fine_form():
    if 'admin_id' not in session:
        flash('Login required', '0')
        return redirect(url_for('index'))

    
    if db is None:
        flash('Database connection error.', '0')
        return render_template('admin_home.html') # Redirect or show error

    try:
        fine_categories = list(db.fine_categories.find())
    except Exception as e:
        print(f"Error fetching fine categories: {e}")
        flash('Error loading fine categories.', '0')
        fine_categories = []

    # Set default due date (e.g., 7 days from now)
    default_due_date = (datetime.datetime.now() + datetime.timedelta(days=7)).strftime('%Y-%m-%d')

    return render_template('admin_new_fine.html', fine_categories=fine_categories, due_date=default_due_date)


@admin_bp.route('/newentry', methods=['POST'])
def admin_create_fine():
    if 'admin_id' not in session:
        flash('Login required', '0')
        return redirect(url_for('index'))

    
    if db is None:
        flash('Database connection error.', '0')
        return redirect(url_for('admin.admin_new_fine_form'))

    student_id_str = request.form.get('student_id')
    fine_category = request.form.get('fine_category')
    reason = request.form.get('reason')
    amount_str = request.form.get('amount')
    due_date_str = request.form.get('due_date') # Keep as string

    # Basic Validation
    if not all([student_id_str, fine_category, reason, amount_str, due_date_str]):
        flash('All fields are required.', '0')
        # Reload form with categories
        fine_categories = list(db.fine_categories.find())
        return render_template('admin_new_fine.html', fine_categories=fine_categories, due_date=due_date_str or (datetime.datetime.now() + datetime.timedelta(days=7)).strftime('%Y-%m-%d'))

    try:
        amount = float(amount_str)
        # Optional: Validate due_date format if needed, though type="date" helps
    except ValueError:
        flash('Invalid amount entered.', '0')
        fine_categories = list(db.fine_categories.find())
        return render_template('admin_new_fine.html', fine_categories=fine_categories, due_date=due_date_str)

    try:
        # Find student by their 'id' (assuming this is the unique student identifier like roll no)
        student = db.students.find_one({'id': student_id_str})

        if student:
            new_fine = {
                'student_id': student['_id'], # Store the MongoDB ObjectId of the student
                'student_id_str': student_id_str, # Store the readable student ID (roll no)
                'fine_category': fine_category,
                'reason': reason,
                'amount': amount,
                'due_date': due_date_str, # Store as YYYY-MM-DD string
                'issue_date': datetime.datetime.now().strftime('%Y-%m-%d'),
                'status': 'pending', # Initial status
                'transaction_id': None, # Add field for payment approval workflow
                'last_updated': datetime.datetime.now()
            }
            result = db.fines.insert_one(new_fine)
            flash('Fine created successfully!', '1')

            # --- Send Email Notification ---
            student_email = student.get('email')
            if student_email:
                subject = f"Trial mail : New Fine Issued: {fine_category}"
                body = f"**Trial Mail**\nDear {student.get('name', 'Student')},\n\nA new fine has been issued to you:\n\n" \
                       f"Category: {fine_category}\n" \
                       f"Reason: {reason}\n" \
                       f"Amount: {amount:.2f}\n" \
                       f"Due Date: {due_date_str}\n\n" \
                       f"Please view your fines and make the payment before the due date.\n\n" \
                       f"Regards,\nCampus Fine Track System"
                send_email(subject, student_email, body)
            else:
                flash('Fine created, but could not send email notification (student email not found).', '0')
            # --- End Email ---

            return redirect(url_for('admin.admin_view_fines'))
        else:
            flash(f'Student with ID {student_id_str} not found.', '0')
            # Reload form with categories and previously entered due date
            fine_categories = list(db.fine_categories.find())
            return render_template('admin_new_fine.html', fine_categories=fine_categories, due_date=due_date_str)

    except Exception as e:
        print(f"Error creating fine: {e}")
        flash(f'An error occurred while creating the fine: {e}', '0')
        # Reload form
        fine_categories = list(db.fine_categories.find())
        return render_template('admin_new_fine.html', fine_categories=fine_categories, due_date=due_date_str)


# Route to fetch student email via AJAX for the new fine form
@admin_bp.route('/get_student_email/<student_id_str>', methods=['GET'])
def get_student_email(student_id_str):
    # No login check needed for AJAX usually, but depends on security requirements
    
    if db is None:
         return jsonify({'email': None, 'error': 'Database unavailable'}), 503 # Service Unavailable

    try:
        student = db.students.find_one({'id': student_id_str}, {'email': 1}) # Only fetch email
        if student:
            return jsonify({'email': student.get('email')})
        else:
            return jsonify({'email': None}) # Student not found
    except Exception as e:
        print(f"Error fetching student email for {student_id_str}: {e}")
        return jsonify({'email': None, 'error': 'Server error'}), 500


@admin_bp.route('/fines')
def admin_view_fines():
    if 'admin_id' not in session:
        flash('Login required', '0')
        return redirect(url_for('index'))

    
    if db is None:
        flash('Database connection error.', '0')
        return render_template('admin_home.html')

    query = {}
    search_student_id_str = request.args.get('student_id', '').strip()
    fine_category = request.args.get('fine_category')
    due_date = request.args.get('due_date')
    status = request.args.get('status')

    if search_student_id_str:
        # Find the student's MongoDB _id first if searching by string ID
        # student = db.students.find_one({'id': search_student_id_str}, {'_id': 1})
        # if student:
        #     query['student_id'] = student['_id']
        # else:
        #     flash(f'Student ID {search_student_id_str} not found.', '0')
        #     # Return empty list if student not found? Or show all? Let's search by the string id directly
        query['student_id_str'] = search_student_id_str


    if fine_category:
        query['fine_category'] = fine_category
    if due_date:
        query['due_date'] = due_date # Assumes YYYY-MM-DD format
    if status:
        query['status'] = status

    try:
        # Sort by issue date descending, limit results for performance
        fines = list(db.fines.find(query).sort('issue_date', -1).limit(100))   # debugging
        # pprint.pprint(fines)                                                   # debugging
        fines = list(db.fines.find(query).sort('issue_date', -1).limit(100))

        # Fetch student names - inefficient N+1 query, optimize if needed
        # Optimization: Get all unique student_db_ids from fines, then query students collection once.
        student_ids = list(set(f.get('_id') for f in fines if f.get('_id')))
        students_info = {}
        if student_ids:
            students_cursor = db.students.find({'_id': {'$in': student_ids}}, {'_id': 1, 'name': 1, 'id': 1})
            students_info = {s['_id']: {'name': s.get('name', 'N/A'), 'id': s.get('id', 'N/A')} for s in students_cursor}
        # pprint.pprint(student_ids) # debugging
        # pprint.pprint(student_info) # debugging
        for fine in fines:
            student_info = students_info.get(fine.get('student_id'))
            if student_info:
                fine['student_name'] = student_info['name']
                # Ensure student_id_str is present, fallback to DB if needed
                if not fine.get('student_id_str'):
                    fine['student_id_str'] = student_info['id']
            else:
                # Keep existing student_id_str if present, otherwise mark Unknown
                student = db.students.find_one({'_id': fine['student_id']})
                # fine['student_id_str'] = fine.get('student_id_str', 'Unknown')
                fine['student_name'] = student['name'] if student else 'Unknown/Deleted'
                fine['student_id_str'] = student['id'] if student else 'Unknown'

        fine_categories = list(db.fine_categories.find())

    except Exception as e:
        print(f"Error viewing fines: {e}")
        flash(f'Error retrieving fines: {e}', '0')
        fines = []
        fine_categories = []

    return render_template('admin_view_fines.html',
                           fines=fines,
                           fine_categories=fine_categories,
                           # Pass search params back to template to keep filters populated
                           search_student_id=search_student_id_str,
                           search_category=fine_category,
                           search_due_date=due_date,
                           search_status=status
                           )

# Keep delete for PAID fines, as requested originally? Or remove?
# Let's assume admins can delete *paid* fines for cleanup.
@admin_bp.route('/fines/<fine_id>/delete', methods=['POST'])
def delete_fine(fine_id):
    if 'admin_id' not in session:
        flash('Login required', '0')
        return redirect(url_for('index'))

    
    if db is None:
        flash('Database connection error.', '0')
        return redirect(url_for('admin.admin_view_fines'))

    try:
        obj_id = ObjectId(fine_id)
        # IMPORTANT: Only allow deleting PAID fines to avoid accidental data loss
        result = db.fines.delete_one({'_id': obj_id, 'status': 'paid'})
        if result.deleted_count > 0:
            flash("Paid fine deleted successfully!", "1")
        else:
            # Could be not found, or not in 'paid' status
            flash("Error: Fine not found or is not paid. Only paid fines can be deleted.", "0")
    except InvalidId:
        flash("Invalid fine ID format.", "0")
    except Exception as e:
        print(f"Error deleting fine {fine_id}: {e}")
        flash(f"Error deleting fine: {e} ", "0")

    # Redirect back to the view fines page, preserving filters if possible
    # (Requires passing filter params back or storing them in session)
    return redirect(url_for('admin.admin_view_fines'))


# This route ('accept_payment') is now replaced by the approval workflow.
# It might be repurposed for direct *cash* payments by admin if needed,
# but based on the request, let's remove/comment it out from the primary flow.
# @admin_bp.route('/fines/<fine_id>/pay', methods=['POST'])
# def accept_payment(fine_id): ... (Old logic commented out)


# --- Payment Approval Workflow ---

@admin_bp.route('/fines/approvals', methods=['GET'])
def admin_approve_fines_list():
    if 'admin_id' not in session:
        flash('Login required', '0')
        return redirect(url_for('index'))

    
    if db is None:
        flash('Database connection error.', '0')
        return render_template('admin_home.html')

    try:
        # Find fines pending approval
        pending_fines = list(db.fines.find({'status': 'pending_approval'}).sort('last_updated', 1))

        # Group by transaction_id for display (optional but cleaner)
        approvals = {}
        for fine in pending_fines:
            tx_id = fine.get('transaction_id', 'UNKNOWN_TX')
            if tx_id not in approvals:
                # Fetch student details once per transaction
                student = db.students.find_one({'_id': fine.get('student_id')})
                approvals[tx_id] = {
                    'transaction_id': tx_id,
                    'student_id_str': fine.get('student_id_str', 'N/A'),
                    'student_name': student.get('name', 'Unknown') if student else 'Unknown',
                    'student_email': student.get('email') if student else None,
                    'fines': [],
                    'total_amount': 0
                }
            approvals[tx_id]['fines'].append(fine)
            approvals[tx_id]['total_amount'] += fine.get('amount', 0)

    except Exception as e:
        print(f"Error fetching fines for approval: {e}")
        flash(f'Error loading approvals: {e}', '0')
        approvals = {}

    return render_template('admin_approvals.html', approvals=approvals.values())


@admin_bp.route('/fines/approve/<transaction_id>', methods=['POST'])
def admin_approve_transaction(transaction_id):
    if 'admin_id' not in session:
        flash('Login required', '0')
        return redirect(url_for('index'))

    
    if db is None:
        flash('Database connection error.', '0')
        return redirect(url_for('admin.admin_approve_fines_list'))

    try:
        # Find all fines associated with this transaction ID and pending approval
        fines_to_approve = list(db.fines.find({
            'transaction_id': transaction_id,
            'status': 'pending_approval'
        }))

        if not fines_to_approve:
            flash(f'No fines found pending approval for Transaction ID: {transaction_id}', '0')
            return redirect(url_for('admin.admin_approve_fines_list'))

        # Update status to 'paid'
        result = db.fines.update_many(
            {'transaction_id': transaction_id, 'status': 'pending_approval'},
            {'$set': {'status': 'paid', 'last_updated': datetime.datetime.now()}}
        )

        if result.modified_count > 0:
            flash(f'Transaction {transaction_id} approved ({result.modified_count} fines marked as paid).', '1')

            # Send confirmation email to student
            first_fine = fines_to_approve[0] # Get details from the first fine for email
            student = db.students.find_one({'_id': first_fine.get('student_id')})
            if student and student.get('email'):
                total_amount = sum(f.get('amount', 0) for f in fines_to_approve)
                subject = "Fine Payment Approved"
                body = f"Dear {student.get('name', 'Student')},\n\n" \
                       f"Your payment with Transaction ID: {transaction_id} for the amount of {total_amount:.2f} has been approved.\n\n" \
                       f"The following fines are now marked as paid:\n"
                for fine in fines_to_approve:
                    body += f"- {fine.get('fine_category')}: {fine.get('reason')} ({fine.get('amount'):.2f})\n"
                body += f"\nThank you,\nCampus Fine Track System"
                send_email(subject, student['email'], body)
            else:
                flash('Approval successful, but could not send confirmation email.', '0')

        else:
            flash(f'Could not approve Transaction {transaction_id}. Fines may have already been processed.', '0')

    except Exception as e:
        print(f"Error approving transaction {transaction_id}: {e}")
        flash(f'An error occurred during approval: {e}', '0')

    return redirect(url_for('admin.admin_approve_fines_list'))


@admin_bp.route('/fines/reject/<transaction_id>', methods=['POST'])
def admin_reject_transaction(transaction_id):
    if 'admin_id' not in session:
        flash('Login required', '0')
        return redirect(url_for('index'))

    
    if db is None:
        flash('Database connection error.', '0')
        return redirect(url_for('admin.admin_approve_fines_list'))

    rejection_reason = request.form.get('reason', 'No reason provided.') # Optional: Add reason input in template

    try:
        # Find all fines associated with this transaction ID and pending approval
        fines_to_reject = list(db.fines.find({
            'transaction_id': transaction_id,
            'status': 'pending_approval'
        }))

        if not fines_to_reject:
            flash(f'No fines found pending approval for Transaction ID: {transaction_id}', '0')
            return redirect(url_for('admin.admin_approve_fines_list'))

        # Update status back to 'pending', clear transaction_id
        result = db.fines.update_many(
            {'transaction_id': transaction_id, 'status': 'pending_approval'},
            {'$set': {'status': 'pending', 'transaction_id': None, 'last_updated': datetime.datetime.now()}}
        )

        if result.modified_count > 0:
            flash(f'Transaction {transaction_id} rejected ({result.modified_count} fines reset to pending).', '1')

             # Send rejection email to student
            first_fine = fines_to_reject[0]
            student = db.students.find_one({'_id': first_fine.get('student_id')})
            if student and student.get('email'):
                total_amount = sum(f.get('amount', 0) for f in fines_to_reject)
                subject = "Fine Payment Rejected"
                body = f"Dear {student.get('name', 'Student')},\n\n" \
                       f"Your payment submission with Transaction ID: {transaction_id} for the amount of {total_amount:.2f} has been rejected.\n\n" \
                       f"Reason: {rejection_reason}\n\n" \
                       f"The associated fines have been reset to 'pending' status. Please review the transaction details or contact the admin office if you believe this is an error.\n\n" \
                       f"Regards,\nCampus Fine Track System"
                send_email(subject, student['email'], body)
            else:
                 flash('Rejection successful, but could not send notification email.', '0')

        else:
            flash(f'Could not reject Transaction {transaction_id}. Fines may have already been processed.', '0')

    except Exception as e:
        print(f"Error rejecting transaction {transaction_id}: {e}")
        flash(f'An error occurred during rejection: {e}', '0')

    return redirect(url_for('admin.admin_approve_fines_list'))


# --- Batch Reminder Functionality ---
@admin_bp.route('/reminders', methods=['GET', 'POST'])
def send_reminders():
    if 'admin_id' not in session:
        flash('Login required', '0')
        return redirect(url_for('index'))

    
    if db is None:
        flash('Database connection error.', '0')
        return render_template('admin_home.html')

    if request.method == 'POST':
        batch_year_str = request.form.get('batch_year') # e.g., "23" for 2023 batch
        if not batch_year_str or not batch_year_str.isdigit() or len(batch_year_str) != 2:
            flash('Invalid batch year format. Please enter two digits (e.g., 23).', '0')
            return render_template('admin_send_reminders.html') # Need to create this template

        # Find overdue pending fines for the specified batch
        try:
            today_str = datetime.datetime.now().strftime('%Y-%m-%d')
            # Regex to match student ID starting with the batch year
            student_id_regex = f"^{batch_year_str}.*"

            # Find pending fines that are overdue and match the batch regex
            overdue_fines = list(db.fines.find({
                'status': 'pending',
                'due_date': {'$lt': today_str},
                'student_id_str': {'$regex': student_id_regex}
            }))

            if not overdue_fines:
                flash(f'No overdue pending fines found for batch {batch_year_str}.', '1')
                return render_template('admin_send_reminders.html')

            # Group fines by student
            fines_by_student = {}
            student_db_ids = set()
            for fine in overdue_fines:
                s_db_id = fine.get('student_id')
                if s_db_id:
                    student_db_ids.add(s_db_id)
                    if s_db_id not in fines_by_student:
                        fines_by_student[s_db_id] = []
                    fines_by_student[s_db_id].append(fine)

            # Get student emails
            students_data = {}
            if student_db_ids:
                 students_cursor = db.students.find({'_id': {'$in': list(student_db_ids)}}, {'_id': 1, 'name': 1, 'email': 1})
                 students_data = {s['_id']: {'name': s.get('name'), 'email': s.get('email')} for s in students_cursor}

            # Send emails
            sent_count = 0
            failed_count = 0
            for s_db_id, student_fines in fines_by_student.items():
                student_info = students_data.get(s_db_id)
                if student_info and student_info.get('email'):
                    subject = "Overdue Fine Reminder"
                    body = f"Dear {student_info.get('name', 'Student')},\n\n" \
                           f"This is a reminder that you have overdue fines that require payment:\n\n"
                    total_overdue = 0
                    for fine in student_fines:
                        body += f"- Category: {fine.get('fine_category')}\n" \
                                f"  Reason: {fine.get('reason')}\n" \
                                f"  Amount: {fine.get('amount'):.2f}\n" \
                                f"  Due Date: {fine.get('due_date')}\n\n"
                        total_overdue += fine.get('amount', 0)
                    body += f"Total Overdue Amount: {total_overdue:.2f}\n\n" \
                            f"Please log in to the Campus Fine Track system to pay your fines as soon as possible.\n\n" \
                            f"Regards,\nCampus Fine Track System"

                    if send_email(subject, student_info['email'], body):
                        sent_count += 1
                    else:
                        failed_count += 1
                else:
                    failed_count += 1 # Failed because no email found

            flash(f'Sent {sent_count} reminder emails for batch {batch_year_str}. Failed to send {failed_count} (missing email or send error).', '1' if sent_count > 0 else '0')

        except Exception as e:
            print(f"Error sending reminders for batch {batch_year_str}: {e}")
            flash(f'An error occurred while sending reminders: {e}', '0')

        return render_template('admin_send_reminders.html') # Show the form again

    # GET request: Show the form to enter batch year
    return render_template('admin_send_reminders.html') # Need to create this template


# --- Analytics ---
@admin_bp.route('/analytics')
def admin_analytics():
    if 'admin_id' not in session:
        flash('Login required', '0')
        return redirect(url_for('index'))
    return redirect(url_for('admin.admin_home'))


# --- Logout ---
@admin_bp.route('/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    session.pop('admin_role', None)
    flash('You have been logged out.', '1')
    return redirect(url_for('index')) # Redirect to main index/login page
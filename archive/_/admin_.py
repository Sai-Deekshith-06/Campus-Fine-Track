@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('uname')
        password = request.form.get('pswd')

        if username and password:
            admin = mongo.db.admin.find_one({'username': username})
            if admin and check_password_hash(admin['password'], password):
                session['admin_id'] = str(admin['_id'])
                return redirect(url_for('admin_home'))
            else:
                error = 'Invalid username or password'
        else:
            error = 'Please enter both username and password'

        return render_template('login.html', error=error)

    return render_template('index.html')

@app.route("/admin/home")
def admin_home():
    if 'admin_id' in session:
        return render_template('admin_home.html')
    else:
        return redirect(url_for('index'))

@app.route('/admin/newentry', methods=['GET'])
def admin_new_fine_form():
    if 'admin_id' not in session:
        return redirect(url_for('index'))
    due_date = "2025-04-30"
    fine_categories = mongo.db.fine_categories.find()
    return render_template('admin_new_fine.html', fine_categories=fine_categories, due_date=due_date)

@app.route('/admin/newentry', methods=['POST'])
def admin_create_fine():
    if 'admin_id' not in session:
        return redirect(url_for('index'))
    
    student_id = request.form.get('student_id')
    fine_category = request.form.get('fine_category')
    reason = request.form.get('reason')
    amount = request.form.get('amount')
    due_date = request.form.get('due_date')

    student = mongo.db.students.find_one({'id': student_id})
    if student:
        new_fine = {
            'student_id': student['_id'],
            'fine_category': fine_category,
            'reason': reason,
            'amount': float(amount) if amount else 0.0,
            'due_date': due_date,
            'issue_date': datetime.datetime.now().strftime('%Y-%m-%d'),
            'status': 'pending'
        }
        mongo.db.fines.insert_one(new_fine)
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

@app.route('/admin/get_student_email/<student_id>')
def get_student_email(student_id):
    student = mongo.db.students.find_one({'id': student_id})
    if student:
        return jsonify({'email': student['email']})  # Or however your email field is named
    else:
        return jsonify({'email': None})

@app.route('/admin/fines')
def admin_view_fines():
    if 'admin_id' in session:
        query = {}  # Start with an empty query

        # Search by Student ID
        student_id = request.args.get('student_id')
        student = mongo.db.students.find_one({'id': student_id}) if student_id else None
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

        fines = list(mongo.db.fines.find(query))  # Apply the query to the find operation

        for fine in fines:
            student = mongo.db.students.find_one({'_id': fine['student_id']})
            if student:
                fine['student_name'] = student['name']
            else:
                fine['student_name'] = 'Unknown'

        fine_categories = list(mongo.db.fine_categories.find())  # Fetch categories for the filter

        return render_template('admin_view_fines.html', fines=fines, fine_categories=fine_categories, std_id=student_id)
    else:
        return redirect(url_for('admin_login'))

@app.route('/admin/fines/<fine_id>/pay', methods=['POST'])
def accept_payment(fine_id):
    if 'admin_id' not in session:
        return redirect(url_for('index'))

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
    
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    return redirect(url_for('index'))
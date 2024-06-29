from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask_paginate import Pagination, get_page_parameter
import os

app = Flask(__name__)
app.secret_key = "BIG_BADASS_SECRET_KEY"

# Initialize MongoDB client
client = MongoClient(os.environ.get('MONGODB_URI'))
db = client['db1']
collection = db['user_db']

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == os.environ.get('UNAME') and password == os.environ.get('PWORD'):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))
@app.route('/')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 10

    # Adjust aggregation to include pagination
    requested_date_count = list(collection.aggregate([
        {
            "$group": {
                "_id": "$requested_date",
                "total_requests": {"$sum": 1},
                "informed_client_count": {"$sum": {"$cond": {"if": "$informed_client", "then": 1, "else": 0}}},
                "informed_owner_count": {"$sum": {"$cond": {"if": "$informed_owner", "then": 1, "else": 0}}}
            }
        },
        {"$sort": {"_id": -1}},
        {"$skip": (page - 1) * per_page},
        {"$limit": per_page}
    ]))

    total_dates = collection.aggregate([
        {
            "$group": {
                "_id": "$requested_date"
            }
        },
        {"$count": "total"}
    ])
    total_dates = next(total_dates, {}).get('total', 0)

    # Calculate the total number of request entries
    total_requests = collection.count_documents({})

    pagination = Pagination(page=page, total=total_dates, record_name='dates', per_page=per_page)

    informed_owner_count = collection.count_documents({'informed_owner': True})
    informed_client_count = collection.count_documents({'informed_client': True})

    return render_template('dashboard.html',
                           pagination=pagination,
                           total_requests=total_requests,  # Pass total request entries to the template
                           informed_owner_count=informed_owner_count,
                           informed_client_count=informed_client_count,
                           requested_date_count=requested_date_count)


@app.route('/update_status/<user_id>/<status_type>', methods=['POST'])
def update_status(user_id, status_type):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if status_type == 'owner':
        collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'informed_owner': True}})
    elif status_type == 'client':
        collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'informed_client': True}})
    
    # Fetch the requested_date for the user being updated
    user = collection.find_one({'_id': ObjectId(user_id)})
    requested_date = user['requested_date']

    # Redirect to the date_details route for the specific requested_date
    return redirect(url_for('date_details', requested_date=requested_date))

@app.route('/date_details/<requested_date>')
def date_details(requested_date):
    if 'username' not in session:
        return redirect(url_for('login'))

    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 10

    # Fetch data for the specific requested_date
    total_requests = collection.count_documents({'requested_date': requested_date})
    informed_client_count = collection.count_documents({'requested_date': requested_date, 'informed_client': True})
    informed_owner_count = collection.count_documents({'requested_date': requested_date, 'informed_owner': True})

    # Fetch users for the specific requested_date with pagination
    users = list(collection.find({'requested_date': requested_date})
                 .skip((page - 1) * per_page)
                 .limit(per_page))

    pagination = Pagination(page=page, total=total_requests, record_name='requests', per_page=per_page)

    return render_template('date_details.html', requested_date=requested_date,
                           total_requests=total_requests,
                           informed_client_count=informed_client_count,
                           informed_owner_count=informed_owner_count,
                           users=users, pagination=pagination)

if __name__ == '__main__':
    app.run()

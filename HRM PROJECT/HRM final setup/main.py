import secrets
import smtplib
import ssl
import string
from smtpd import SMTPServer
from smtplib import SMTPServerDisconnected
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime, timedelta


app = Flask(__name__)
app.config['SECRET_KEY'] = 'VBD-Private-limited-startup-2021'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///employee.db'
engine = create_engine('sqlite:///employees.db', echo=True)
# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)
db = SQLAlchemy(app)

Session = scoped_session(sessionmaker())

users = {}
# Leave model for storing leave requests
class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    name = db.Column(db.String(100))
    eid = db.Column(db.String(100))
    start_date = db.Column(db.String(100))
    end_date = db.Column(db.String(100))
    reason = db.Column(db.String(200))
    noofdays=db.Column(db.String(200))
    approved_by_hr = db.Column(db.Boolean, default=None)
    approved_by_department_head = db.Column(db.Boolean, default=None)



@login_manager.user_loader
def load_user(user_id):
    return Employee.query.get(int(user_id))

class Employee(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    eid = db.Column(db.String(100), nullable=False, unique=True)
    name = db.Column(db.String(100))
    contactNo = db.Column(db.String(100))
    email = db.Column(db.String(100))
    address = db.Column(db.String(100))
    blood = db.Column(db.String(100))
    department = db.Column(db.String(100))
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50))
    supervisor_id = db.Column(db.String, db.ForeignKey('employee.eid'), nullable=True)
    supervisor = db.relationship('Employee', remote_side=[eid], backref='subordinates', foreign_keys=[supervisor_id])

    team_leader_id = db.Column(db.String, db.ForeignKey('employee.eid'), nullable=True)
    team_leader = db.relationship('Employee', remote_side=[eid], backref='team_members', foreign_keys=[team_leader_id])

    status = db.Column(db.String(10), nullable=False, default='stay')
    resignation_date = db.Column(db.Date)

    def update_status(self):
        if self.resignation_date and self.resignation_date + timedelta(days=30) <= datetime.now().date():
            self.status = 'exit'
            db.session.commit()
    def __init__(self, eid, email, password, role, **kwargs):
        self.eid = eid
        self.email = email
        self.password = password
        self.role = role

        # Initialize the rest of the attributes if provided
        self.name = kwargs.get('name')
        self.contactNo = kwargs.get('contactNo')
        self.address = kwargs.get('address')
        self.blood = kwargs.get('blood')
        self.department = kwargs.get('department')
        self.supervisor_id = kwargs.get('supervisor_id')
        self.team_leader_id = kwargs.get('team_leader_id')
        self.resignation_date = kwargs.get('resignation_date')


def generate_password(length=10):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(characters) for _ in range(length))
    return password

@app.route('/add_employee/<user_id>', methods=['GET', 'POST'])
@login_required
def add_employee(user_id):
    user = Employee.query.get(user_id)
    if not user:
        return "Employee not found.", 404

    if request.method == 'POST':
        name = request.form.get('name')
        eid = request.form.get('eid')
        contactNo = request.form.get('contactNo')
        address = request.form.get('address')
        blood = request.form.get('blood')
        email = request.form.get('email')
        department = request.form.get('department')
        team_leader_id = request.form.get('team_leader_id')
        supervisor_id = request.form.get('supervisor_id')

        user.name = name
        user.eid = eid
        user.contactNo = contactNo
        user.email = email
        user.address = address
        user.blood = blood
        user.department = department
        user.supervisor_id = supervisor_id
        user.team_leader_id = team_leader_id
        resignation_date = request.form.get('resignation_date')

        if resignation_date:
            user.resignation_date = datetime.strptime(resignation_date, '%Y-%m-%d')
        else:
            user.resignation_date = None

        try:
            db.session.commit()
            print('Employee details updated successfully!', 'success')
            return redirect(url_for('add_employee', user_id=user_id))
        except:
            db.session.rollback()
            print('Failed to update employee details. Please try again.', 'danger')

    return render_template('add_employee.html', user=user)

def send_email(email, password):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    sender_email = 'sandeep17rot@gmail.com'
    sender_password = 'cjtssnzgzhvgvndi'
    message = MIMEMultipart()
    message['Subject'] = 'Account Created'
    message['From'] = sender_email
    message['To'] = email
    text = f'Your automatically generated password is:{password}'
    message.attach(MIMEText(text, 'plain'))
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
        print("Email sent successfully!")
    except smtplib.SMTPAuthenticationError:
        print("Failed to authenticate with the SMTP server.")
    except Exception as e:
        print("An error occurred while sending the email:", str(e))

@app.route('/everysearch', methods=['GET', 'POST'])
def index():
    employees = Employee.query.all()
    current_date = datetime.now().date()
    for employee in employees:
        if employee.resignation_date and employee.resignation_date + timedelta(days=30) <= current_date:
            employee.status = 'exit'
        elif employee.resignation_date:
            employee.status = 'applying_for_resignation'
        else:
            employee.status = 'stay'
    db.session.commit()
    return render_template('employee_list.html', employees=employees,user=current_user)
@app.route('/apply_resignation', methods=['GET', 'POST'])
def apply_resignation():
    if request.method == 'POST':
        employee_id = request.form['eid']
        resignation_date = request.form['resignation_date']

        if not resignation_date:
          #  flash("Please select a resignation date!", "error")
            return redirect(url_for('apply_resignation'))

        employee = Employee.query.get_or_404(employee_id)
        employee.resignation_date = datetime.strptime(resignation_date, '%Y-%m-%d').date()
        db.session.commit()
       # flash("Resignation applied successfully!", "success")
        return redirect(url_for('index'))

    return render_template('apply_resignation.html', employees=Employee.query.all())

@app.route('/search', methods=['GET', 'POST'])
def search_by_team_leader():
    if request.method == 'POST':
        team_leader_id = request.form['team_leader_id']
        employees = Employee.query.filter_by(team_leader_id=team_leader_id).all()
        if employees:
            return render_template('search_result_team_leader.html', employees=employees, team_leader_id=team_leader_id)
        else:
            #('No employees found under the specified Team Leader ID', 'error')
            return redirect(url_for('search_by_team_leader'))

    return render_template('search_employee.html')
@app.route('/')
def home():
    return render_template('signup.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        if email in users:
            return render_template('signup.html', message='Email already exists.')

        password = generate_password()
        users[email] = password
        send_email(email, password)
        redirect('login.html')

    return render_template('signup.html', message='')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        eid = request.form['eid']
        password = request.form['password']

        # Query the database for the user
        user = Employee.query.filter_by(eid=eid).first()

        # Check if the user exists and the password is correct
        if user is None or user.password != password:
            return render_template('login.html', message='Invalid email or password.')
        login_user(user)

        if user.role == 'HR':
            return render_template('hr_employee_details.html', employee=user)
        elif user.role == 'Department Head':
            return render_template('DH_employee_details.html', employee=user)
        else:
            return render_template('unique_employee_details.html', employee=user)

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        eid = request.form['eid']
        password = request.form['password']
        role = request.form['role']
        existing_user = Employee.query.filter_by(email=email).first()

        if existing_user:
            # Email already exists, handle the situation (e.g., show an error message)
            return render_template('register.html', message='Email address already registered.')
        user = Employee.query.filter_by(eid=eid).first()
        if user:
            return render_template('register.html', error=True)
        new_user = Employee(eid=eid, email=email, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login',user_id=new_user.id))
    return render_template('register.html', error=False)



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/hr_again/<user_id>')
@login_required
def hr_again(user_id):
    user = Employee.query.get(user_id)
    login_user(user)
    employee = Employee.query.get(user.id)
    if user.role == 'HR':
        return render_template('hr_employee_details.html', employee=employee)
    elif user.role == 'Department Head':
        return render_template('DH_employee_details.html', employee=employee)
    else:
        return render_template('unique_employee_details.html', employee=employee)

@app.route('/dh_again/<user_id>')
@login_required
def dh_again(user_id):
    user = Employee.query.get(user_id)
    login_user(user)
    employee = Employee.query.get(user.id)
    if user.role == 'HR':
        return render_template('hr_employee_details.html', employee=employee)
    elif user.role == 'Department Head':
        return render_template('DH_employee_details.html', employee=employee)
    else:
        return render_template('unique_employee_details.html', employee=employee)

@app.route('/employee_again/<user_id>')
@login_required
def employee_again(user_id):
    user = Employee.query.get(user_id)
    login_user(user)
    employee = Employee.query.get(user.id)
    if user.role == 'HR':
        return render_template('hr_employee_details.html', employee=employee)
    elif user.role == 'Department Head':
        return render_template('DH_employee_details.html', employee=employee)
    else:
        return render_template('unique_employee_details.html', employee=employee)


@app.route('/hr_leave_requests', methods=['GET','POST'])
@login_required
def hr_leave_requests():
    if not current_user.role == 'HR':
        return redirect(url_for('login'))

    if request.method == 'POST':
        request_id = request.form['request_id']
        approval_status = request.form['approval_status']

        leave_request = LeaveRequest.query.get(request_id)
        if leave_request:
            if approval_status == 'approved':
                leave_request.approved_by_hr = True
            elif approval_status == 'disapproved':
                leave_request.approved_by_hr = False

            db.session.commit()

    leave_requests = LeaveRequest.query.all()
    return render_template('hr_leave_requests.html', leave_requests=leave_requests,user=current_user)

@app.route('/leave', methods=['GET', 'POST'])
@login_required
def leave_requests():
    if request.method == 'POST':
        request_id = request.form['request_id']
        approved = request.form['approved'] == 'True'
        leave_request = LeaveRequest.query.get(request_id)
        leave_request.approved_by_hr = approved
        db.session.commit()

    leave_requests = LeaveRequest.query.filter_by(user_id=current_user.id)
    return render_template('leave_requests.html', leave_requests=leave_requests,user=current_user)


@app.route('/department_leave_requests', methods=['GET','POST'])
@login_required
def department_leave_requests():
    if not current_user.role == 'Department Head':
        return redirect(url_for('login'))

    if request.method == 'POST':
        request_id = request.form['request_id']
        approval_status = request.form['approval_status']

        leave_request = LeaveRequest.query.get(request_id)
        if leave_request:
            if approval_status == 'approved':
                leave_request.approved_by_department_head = True
            elif approval_status == 'disapproved':
                leave_request.approved_by_department_head = False

            db.session.commit()

    leave_requests = LeaveRequest.query.all()
    return render_template('department_leave_requests.html', leave_requests=leave_requests,user=current_user)


@app.route('/req', methods=['GET', 'POST'])
@login_required
def leave_request():
    if request.method == 'POST':
        name = request.form.get('name')
        eid = request.form.get('eid')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        reason = request.form.get('reason')
        noofdays = request.form.get('noofdays')
        leave_request = LeaveRequest(user_id=current_user.id, eid=eid,name=name, start_date=start_date, end_date=end_date, reason=reason,noofdays=noofdays)
        db.session.add(leave_request)
        db.session.commit()

    return render_template('request_form.html',user=current_user)

@app.route('/update_approval_hr/<int:request_id>', methods=['POST'])
@login_required
def update_approval_hr(request_id):
    if not current_user.role == 'HR':
        return redirect(url_for('hr_leave_requests'))

    approval_status = request.form['approval_status']

    leave_request = LeaveRequest.query.get(request_id)
    if leave_request:
        leave_request.approved_by_hr = (approval_status == 'approved')
        db.session.commit()

    return redirect(url_for('hr_leave_requests'))

@app.route('/update_approval_department_head/<int:request_id>', methods=['POST'])
@login_required
def update_approval_department_head(request_id):
    if not current_user.role == 'Department Head':
        return redirect(url_for('department_head_leave_requests'))

    approval_status = request.form['approval_status']

    leave_request = LeaveRequest.query.get(request_id)
    if leave_request:
        leave_request.approved_by_department_head = (approval_status == 'approved')
        db.session.commit()

    return redirect(url_for('department_leave_requests'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True,port=4050)

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3, json, os, hashlib
from functools import wraps
from analytics.engine import AnalyticsEngine

app = Flask(__name__)
app.secret_key = 'skillquest_funmiyo_2024_xK9mP#zQ'
DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'skillquest.db')

# ── Grade config for KG–Grade 5 ──────────────────────────────────────────────
GRADE_CONFIG = {
    'KG':      {'label':'Kindergarten',  'ops':['+'],        'max_num':5,  'time':120, 'desc':'Counting & basics'},
    'Grade 1': {'label':'Grade 1',       'ops':['+'],        'max_num':10, 'time':100, 'desc':'Addition to 10'},
    'Grade 2': {'label':'Grade 2',       'ops':['+','-'],    'max_num':20, 'time':90,  'desc':'Addition & subtraction'},
    'Grade 3': {'label':'Grade 3',       'ops':['+','-'],    'max_num':50, 'time':80,  'desc':'Larger numbers'},
    'Grade 4': {'label':'Grade 4',       'ops':['+','-','×'],'max_num':99, 'time':70,  'desc':'Times tables'},
    'Grade 5': {'label':'Grade 5',       'ops':['+','-','×','÷'],'max_num':100,'time':60,'desc':'All operations'},
}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def login_required(roles=None):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login_page'))
            if roles and session.get('role') not in roles:
                return redirect(url_for('login_page'))
            return f(*args, **kwargs)
        return wrapped
    return decorator

def get_student_id():
    return session.get('student_id') if session.get('role') == 'student' else None

def ensure_column(conn, table, column, definition):
    cols = [r['name'] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def get_default_school_id(conn):
    c = conn.cursor()
    c.execute("SELECT id FROM schools WHERE code='FUNMIYO-DEMO'")
    row = c.fetchone()
    if row:
        return row['id']
    c.execute("""INSERT INTO schools (name,code,city,contact_email,grade_config)
                 VALUES (?,?,?,?,?)""",
              ('Funmiyo Demo School', 'FUNMIYO-DEMO', 'Demo City',
               'hello@funmiyo.com', json.dumps({})))
    return c.lastrowid

def migrate_db(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS schools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT UNIQUE NOT NULL,
        city TEXT,
        contact_email TEXT,
        grade_config TEXT DEFAULT '{}',
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_column(conn, 'users', 'school_id', 'INTEGER')
    ensure_column(conn, 'students', 'school_id', 'INTEGER')
    ensure_column(conn, 'teachers', 'school_id', 'INTEGER')
    ensure_column(conn, 'announcements', 'school_id', 'INTEGER')
    school_id = get_default_school_id(conn)
    conn.execute("UPDATE users SET school_id=? WHERE school_id IS NULL AND role!='admin'", (school_id,))
    conn.execute("UPDATE students SET school_id=? WHERE school_id IS NULL", (school_id,))
    conn.execute("UPDATE teachers SET school_id=? WHERE school_id IS NULL", (school_id,))
    return school_id

def school_grade_config(conn=None, school_id=None):
    owns_conn = conn is None
    conn = conn or get_db()
    cfg = {k: dict(v) for k, v in GRADE_CONFIG.items()}
    if school_id:
      try:
        row = conn.execute("SELECT grade_config FROM schools WHERE id=?", (school_id,)).fetchone()
        custom = json.loads((row['grade_config'] if row else '{}') or '{}')
        for grade, overrides in custom.items():
            if grade in cfg and isinstance(overrides, dict):
                cfg[grade].update(overrides)
      except Exception:
        pass
    if owns_conn:
        conn.close()
    return cfg

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.executescript(open(os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')).read())
    migrate_db(conn)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        seed_defaults(conn)
    conn.commit()
    conn.close()

def seed_defaults(conn):
    c = conn.cursor()
    school_id = get_default_school_id(conn)
    accounts = [
        ('admin',    hash_pw('admin123'),   'admin',   'Administrator',     'admin@skillquest.edu'),
        ('teacher1', hash_pw('teacher123'), 'teacher', 'Ms. Priya Sharma',  'priya@skillquest.edu'),
        ('teacher2', hash_pw('teacher123'), 'teacher', 'Mr. Rahul Verma',   'rahul@skillquest.edu'),
        ('parent1',  hash_pw('parent123'),  'parent',  'Mrs. Arun Patel',   'arun@skillquest.edu'),
        ('parent2',  hash_pw('parent123'),  'parent',  'Mrs. Sunita Mehra', 'sunita@skillquest.edu'),
    ]
    for uname, ph, role, name, email in accounts:
        c.execute("""INSERT INTO users
                     (username,password_hash,role,full_name,email,school_id)
                     VALUES (?,?,?,?,?,?)""",
                  (uname, ph, role, name, email, None if role == 'admin' else school_id))
    c.execute("SELECT id FROM users WHERE username='teacher1'"); t1 = c.fetchone()[0]
    c.execute("SELECT id FROM users WHERE username='teacher2'"); t2 = c.fetchone()[0]
    c.execute("INSERT INTO teachers (user_id,school_id,grades_assigned) VALUES (?,?,?)",
              (t1, school_id, json.dumps(['KG','Grade 1','Grade 2'])))
    c.execute("INSERT INTO teachers (user_id,school_id,grades_assigned) VALUES (?,?,?)",
              (t2, school_id, json.dumps(['Grade 3','Grade 4','Grade 5'])))
    c.execute("SELECT id FROM users WHERE username='parent1'"); p1 = c.fetchone()[0]
    c.execute("SELECT id FROM users WHERE username='parent2'"); p2 = c.fetchone()[0]
    kids = [
        ('SKQ001','Aarav Patel',   'KG',      'A', 5, p1, t1, 'star'),
        ('SKQ002','Priya Singh',   'Grade 1', 'A', 6, p1, t1, 'rocket'),
        ('SKQ003','Rohan Mehta',   'Grade 2', 'B', 7, p2, t1, 'rainbow'),
        ('SKQ004','Kavya Reddy',   'Grade 3', 'A', 8, p2, t2, 'unicorn'),
        ('SKQ005','Arjun Kumar',   'Grade 4', 'B', 9, None, t2, 'dragon'),
        ('SKQ006','Sneha Joshi',   'Grade 5', 'A',10, None, t2, 'wizard'),
    ]
    for roll, name, grade, sec, age, par, tch, avatar in kids:
        c.execute("""INSERT INTO users (username,password_hash,role,full_name,school_id)
                     VALUES (?,?,?,?,?)""",
                  (roll.lower(), hash_pw('fun123'), 'student', name, school_id))
        uid = c.lastrowid
        c.execute("""INSERT INTO students
                     (user_id,roll_no,full_name,grade,section,age,parent_id,teacher_id,school_id,avatar)
                     VALUES (?,?,?,?,?,?,?,?,?,?)""",
                  (uid, roll, name, grade, sec, age, par, tch, school_id, avatar))

# ── AUTH ──────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return redirect(url_for('login_page') if 'user_id' not in session else url_for('role_home'))

@app.route('/login')
def login_page():
    if 'user_id' in session: return redirect(url_for('role_home'))
    return render_template('login.html')

@app.route('/api/auth/login', methods=['POST'])
def do_login():
    data = request.json
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    if not username or not password:
        return jsonify({'success': False, 'error': 'Please enter username and password'})
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND is_active=1", (username,))
    user = c.fetchone()
    if not user or user['password_hash'] != hash_pw(password):
        conn.close(); return jsonify({'success': False, 'error': 'Wrong username or password! Try again 😊'})
    c.execute("UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?", (user['id'],))
    conn.commit()
    extra = {}
    if user['role'] == 'student':
        c.execute("""SELECT s.*,sc.name as school_name FROM students s
                     LEFT JOIN schools sc ON sc.id=s.school_id
                     WHERE s.user_id=?""", (user['id'],))
        stu = c.fetchone()
        if stu:
            extra = {'student_id': stu['id'], 'roll_no': stu['roll_no'],
                     'grade': stu['grade'], 'section': stu['section'],
                     'age': stu['age'], 'avatar': stu['avatar'],
                     'school_id': stu['school_id'], 'school_name': stu['school_name']}
    elif user['role'] == 'teacher':
        c.execute("""SELECT t.*,sc.name as school_name FROM teachers t
                     LEFT JOIN schools sc ON sc.id=t.school_id
                     WHERE t.user_id=?""", (user['id'],))
        tch = c.fetchone()
        if tch: extra = {'grades': json.loads(tch['grades_assigned'] or '[]'),
                         'school_id': tch['school_id'], 'school_name': tch['school_name']}
    else:
        extra = {'school_id': user['school_id']}
    conn.close()
    session.update({'user_id': user['id'], 'username': user['username'],
                    'role': user['role'], 'full_name': user['full_name'], **extra})
    return jsonify({'success': True, 'role': user['role'], 'name': user['full_name']})

@app.route('/api/auth/register', methods=['POST'])
def do_register():
    data = request.json
    for f in ['full_name','roll_no','grade','section','password']:
        if not (data.get(f) or '').strip():
            return jsonify({'success': False, 'error': f'{f} is required'})
    conn = get_db(); c = conn.cursor()
    school_id = get_default_school_id(conn)
    c.execute("SELECT id FROM students WHERE roll_no=?", (data['roll_no'].strip(),))
    if c.fetchone(): conn.close(); return jsonify({'success': False, 'error': 'That ID is already registered!'})
    username = data['roll_no'].strip().lower()
    c.execute("SELECT id FROM users WHERE username=?", (username,))
    if c.fetchone(): conn.close(); return jsonify({'success': False, 'error': 'Username already taken'})
    teacher_id = None
    c.execute("""SELECT user_id FROM teachers
                 WHERE school_id=? AND grades_assigned LIKE ? LIMIT 1""",
              (school_id, f'%{data["grade"]}%'))
    row = c.fetchone()
    if row: teacher_id = row[0]
    avatar = data.get('avatar', 'star')
    age = int(data.get('age', 5))
    c.execute("""INSERT INTO users (username,password_hash,role,full_name,school_id)
                 VALUES (?,?,?,?,?)""",
              (username, hash_pw(data['password']), 'student', data['full_name'].strip(), school_id))
    uid = c.lastrowid
    c.execute("""INSERT INTO students
                 (user_id,roll_no,full_name,grade,section,age,teacher_id,school_id,avatar)
                 VALUES (?,?,?,?,?,?,?,?,?)""",
              (uid, data['roll_no'].strip(), data['full_name'].strip(),
               data['grade'].strip(), data['section'].strip(), age, teacher_id, school_id, avatar))
    stu_id = c.lastrowid
    conn.commit(); conn.close()
    session.update({'user_id': uid, 'username': username, 'role': 'student',
                    'full_name': data['full_name'].strip(), 'student_id': stu_id,
                    'roll_no': data['roll_no'].strip(), 'grade': data['grade'].strip(),
                    'section': data['section'].strip(), 'age': age, 'avatar': avatar,
                    'school_id': school_id})
    return jsonify({'success': True, 'role': 'student'})

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login_page'))

@app.route('/home')
def role_home():
    role = session.get('role')
    if not role: return redirect(url_for('login_page'))
    return redirect(url_for(f'{role}_dashboard'))

# ── STUDENT ROUTES ────────────────────────────────────────────────────────────
@app.route('/student/dashboard')
@login_required(['student'])
def student_dashboard():
    return render_template('student/dashboard.html',
                           full_name=session['full_name'],
                           grade=session.get('grade','KG'),
                           avatar=session.get('avatar','star'))

@app.route('/student/hub')
@login_required(['student'])
def student_hub():
    return render_template('hub.html',
                           student_name=session['full_name'],
                           grade=session.get('grade','KG'),
                           avatar=session.get('avatar','star'))

@app.route('/game/bubble')
@login_required(['student'])
def game_bubble():
    return render_template('games/bubble_shooter.html',
                           grade=session.get('grade','KG'))

@app.route('/game/blaster')
@login_required(['student'])
def game_blaster():
    return render_template('games/math_blaster.html',
                           grade=session.get('grade','KG'))

@app.route('/game/sprint')
@login_required(['student'])
def game_sprint():
    return render_template('games/math_sprint.html',
                           grade=session.get('grade','KG'))

@app.route('/game/boss')
@login_required(['student'])
def game_boss():
    return render_template('games/boss_battle.html',
                           grade=session.get('grade','KG'))

# ── TEACHER ROUTES ────────────────────────────────────────────────────────────
@app.route('/teacher/dashboard')
@login_required(['teacher'])
def teacher_dashboard():
    return render_template('teacher/dashboard.html', full_name=session['full_name'])

# ── PARENT ROUTES ─────────────────────────────────────────────────────────────
@app.route('/parent/dashboard')
@login_required(['parent'])
def parent_dashboard():
    return render_template('parent/dashboard.html', full_name=session['full_name'])

# ── ADMIN ROUTES ──────────────────────────────────────────────────────────────
@app.route('/admin/dashboard')
@login_required(['admin'])
def admin_dashboard():
    return render_template('admin/dashboard.html', full_name=session['full_name'])

# ── GAME SESSION APIs ─────────────────────────────────────────────────────────
@app.route('/api/session/start', methods=['POST'])
@login_required(['student'])
def start_session():
    data = request.json; sid = get_student_id()
    conn = get_db(); c = conn.cursor()
    grade = session.get('grade','KG')
    c.execute("INSERT INTO game_sessions (student_id,game_type,difficulty,level,grade) VALUES (?,?,?,?,?)",
              (sid, data.get('game_type','bubble'), data.get('difficulty','easy'),
               data.get('level',1), grade))
    conn.commit(); session_id = c.lastrowid; conn.close()
    return jsonify({'success': True, 'session_id': session_id})

@app.route('/api/session/end', methods=['POST'])
@login_required(['student'])
def end_session():
    data = request.json; sid = get_student_id()
    correct = data.get('correct_attempts', 0)
    total   = max(data.get('total_attempts', 1), 1)
    accuracy = (correct / total) * 100
    # Stars: 3 = >85%, 2 = >65%, 1 = >35%, 0 = below
    stars = 3 if accuracy > 85 else 2 if accuracy > 65 else 1 if accuracy > 35 else 0
    conn = get_db(); c = conn.cursor()
    c.execute("""UPDATE game_sessions SET ended_at=CURRENT_TIMESTAMP,score=?,level=?,difficulty=?,
                 time_taken=?,accuracy=?,total_attempts=?,correct_attempts=?,combo_max=?,
                 hints_used=?,operators_used=?,stars_earned=?
                 WHERE id=? AND student_id=?""",
              (data.get('score',0), data.get('level',1), data.get('difficulty','easy'),
               data.get('time_taken',0), round(accuracy,2), total, correct,
               data.get('combo_max',0), data.get('hints_used',0),
               json.dumps(data.get('operators_used',{})), stars,
               data.get('session_id'), sid))
    c.execute("""SELECT COUNT(*) as cnt,COALESCE(SUM(score),0) as ts,
                        COALESCE(AVG(accuracy),0) as aa,COALESCE(MAX(level),1) as ml,
                        COALESCE(SUM(stars_earned),0) as st
                 FROM game_sessions WHERE student_id=? AND ended_at IS NOT NULL""", (sid,))
    agg = c.fetchone()
    c.execute("""UPDATE students SET total_sessions=?,total_score=?,avg_accuracy=?,
                 current_level=?,total_stars=? WHERE id=?""",
              (agg['cnt'], agg['ts'], round(agg['aa'],2), agg['ml'], agg['st'], sid))
    conn.commit(); conn.close()
    try: AnalyticsEngine(DB_PATH).analyze_student(sid)
    except: pass
    return jsonify({'success': True, 'stars': stars, 'accuracy': round(accuracy, 2)})

@app.route('/api/log/action', methods=['POST'])
@login_required(['student'])
def log_action():
    data = request.json; sid = get_student_id()
    conn = get_db(); c = conn.cursor()
    c.execute("""INSERT INTO action_logs
                 (session_id,student_id,action_type,reaction_time,operator_used,
                  operand1,operand2,target_value,result_value,success,
                  hint_used,combo_count,level,difficulty,score_delta,extra_data)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (data.get('session_id'), sid, data.get('action_type','action'),
               data.get('reaction_time',0), data.get('operator_used'),
               data.get('operand1'), data.get('operand2'),
               data.get('target_value'), data.get('result_value'),
               1 if data.get('success') else 0, 1 if data.get('hint_used') else 0,
               data.get('combo_count',0), data.get('level',1),
               data.get('difficulty','easy'), data.get('score_delta',0),
               json.dumps(data.get('extra_data',{}))))
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/adaptive/settings')
@login_required(['student'])
def adaptive_settings():
    sid = get_student_id()
    grade = session.get('grade', 'KG')
    grade_cfg = school_grade_config(school_id=session.get('school_id'))
    gc = grade_cfg.get(grade, grade_cfg['KG'])
    base = {'difficulty':'easy','grade':grade,'operators':gc['ops'],
            'max_num':gc['max_num'],'time_limit':gc['time'],
            'speed_multiplier':0.8,'hint_level':2}
    if not sid: return jsonify(base)
    try: return jsonify(AnalyticsEngine(DB_PATH).get_adaptive_settings(sid, grade, grade_cfg))
    except: return jsonify(base)

@app.route('/api/grade/config')
@login_required(['student'])
def grade_config():
    grade = session.get('grade', 'KG')
    grade_cfg = school_grade_config(school_id=session.get('school_id'))
    return jsonify(grade_cfg.get(grade, grade_cfg['KG']))

# ── STUDENT API ───────────────────────────────────────────────────────────────
@app.route('/api/student/overview')
@login_required(['student'])
def student_overview():
    sid = get_student_id(); conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM students WHERE id=?", (sid,))
    student = dict(c.fetchone() or {})
    c.execute("SELECT * FROM game_sessions WHERE student_id=? ORDER BY started_at DESC LIMIT 12", (sid,))
    sessions = [dict(r) for r in c.fetchall()]
    c.execute("SELECT * FROM ai_analysis WHERE student_id=? ORDER BY analyzed_at DESC LIMIT 1", (sid,))
    row = c.fetchone(); analysis = dict(row) if row else {}
    c.execute("""SELECT DATE(started_at) as date,AVG(accuracy) as avg_acc,SUM(score) as total_score,SUM(stars_earned) as stars
                 FROM game_sessions WHERE student_id=? AND ended_at IS NOT NULL
                 GROUP BY DATE(started_at) ORDER BY date ASC LIMIT 14""", (sid,))
    trend = [dict(r) for r in c.fetchall()]
    c.execute("""SELECT operator_used,COUNT(*) as total,SUM(success) as correct FROM action_logs
                 WHERE student_id=? AND operator_used IS NOT NULL GROUP BY operator_used""", (sid,))
    op_stats = [dict(r) for r in c.fetchall()]
    c.execute("""SELECT game_type,MAX(score) as best,AVG(score) as avg,COUNT(*) as played,
                        AVG(accuracy) as acc,SUM(stars_earned) as stars
                 FROM game_sessions WHERE student_id=? AND ended_at IS NOT NULL GROUP BY game_type""", (sid,))
    game_stats = [dict(r) for r in c.fetchall()]
    c.execute("""SELECT * FROM announcements
                 WHERE role_target IN ('student','all')
                   AND (school_id IS NULL OR school_id=?)
                 ORDER BY created_at DESC LIMIT 5""", (session.get('school_id'),))
    ann = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify({'student':student,'sessions':sessions,'analysis':analysis,
                    'trend':trend,'op_stats':op_stats,'game_stats':game_stats,'announcements':ann})

# ── TEACHER API ───────────────────────────────────────────────────────────────
@app.route('/api/teacher/overview')
@login_required(['teacher'])
def teacher_overview():
    uid = session['user_id']; conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM teachers WHERE user_id=?", (uid,))
    teacher = dict(c.fetchone() or {})
    grades = json.loads(teacher.get('grades_assigned','[]'))
    c.execute("""SELECT s.*,a.group_label as ai_group,a.accuracy_score,a.speed_score,
                        a.recommended_difficulty,a.improvement_areas
                 FROM students s LEFT JOIN ai_analysis a ON a.student_id=s.id
                   AND a.id=(SELECT MAX(id) FROM ai_analysis WHERE student_id=s.id)
                 WHERE s.teacher_id=? ORDER BY s.grade,s.total_score DESC""", (uid,))
    students = [dict(r) for r in c.fetchall()]
    c.execute("""SELECT DATE(gs.started_at) as date,AVG(gs.accuracy) as avg_acc,
                        SUM(gs.score) as total_score,SUM(gs.stars_earned) as stars
                 FROM game_sessions gs JOIN students s ON gs.student_id=s.id
                 WHERE s.teacher_id=? AND gs.ended_at IS NOT NULL
                 GROUP BY DATE(gs.started_at) ORDER BY date ASC LIMIT 14""", (uid,))
    class_trend = [dict(r) for r in c.fetchall()]
    c.execute("SELECT group_label,COUNT(*) as cnt FROM students WHERE teacher_id=? GROUP BY group_label", (uid,))
    groups = [dict(r) for r in c.fetchall()]
    c.execute("""SELECT gs.*,s.full_name,s.roll_no,s.grade FROM game_sessions gs
                 JOIN students s ON gs.student_id=s.id
                 WHERE s.teacher_id=? AND gs.ended_at IS NOT NULL
                 ORDER BY gs.started_at DESC LIMIT 20""", (uid,))
    recent = [dict(r) for r in c.fetchall()]
    c.execute("""SELECT full_name,roll_no,grade,total_score,avg_accuracy,total_stars,group_label
                 FROM students WHERE teacher_id=? ORDER BY total_score DESC LIMIT 5""", (uid,))
    top = [dict(r) for r in c.fetchall()]
    c.execute("""SELECT full_name,roll_no,grade,total_score,avg_accuracy,total_stars,group_label
                 FROM students WHERE teacher_id=? ORDER BY avg_accuracy ASC LIMIT 5""", (uid,))
    weak = [dict(r) for r in c.fetchall()]
    c.execute("""SELECT tn.*,s.full_name FROM teacher_notes tn JOIN students s ON tn.student_id=s.id
                 WHERE tn.teacher_id=? ORDER BY tn.created_at DESC LIMIT 10""", (uid,))
    notes = [dict(r) for r in c.fetchall()]
    total_s = len(students)
    avg_acc = sum(s.get('avg_accuracy',0) for s in students)/max(total_s,1)
    total_stars = sum(s.get('total_stars',0) for s in students)
    conn.close()
    return jsonify({'teacher':teacher,'grades':grades,'students':students,'class_trend':class_trend,
                    'groups':groups,'recent_sessions':recent,'top_students':top,'weak_students':weak,'notes':notes,
                    'summary':{'total_students':total_s,'avg_class_accuracy':round(avg_acc,2),
                               'total_sessions':sum(s.get('total_sessions',0) for s in students),
                               'total_stars':total_stars,'grades':grades}})

@app.route('/api/teacher/note', methods=['POST'])
@login_required(['teacher'])
def add_teacher_note():
    data = request.json; uid = session['user_id']
    stu_id = data.get('student_id'); note = (data.get('note') or '').strip()
    if not stu_id or not note: return jsonify({'success':False,'error':'Missing fields'}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id FROM students WHERE id=? AND teacher_id=?", (stu_id, uid))
    if not c.fetchone(): conn.close(); return jsonify({'success':False,'error':'Not authorized'}), 403
    c.execute("INSERT INTO teacher_notes (teacher_id,student_id,note) VALUES (?,?,?)", (uid,stu_id,note))
    conn.commit(); conn.close(); return jsonify({'success':True})

@app.route('/api/teacher/announce', methods=['POST'])
@login_required(['teacher'])
def teacher_announce():
    data = request.json; uid = session['user_id']; conn = get_db(); c = conn.cursor()
    c.execute("""INSERT INTO announcements (created_by,school_id,role_target,title,body)
                 VALUES (?,?,?,?,?)""",
              (uid, session.get('school_id'), data.get('role_target','student'), data.get('title',''), data.get('body','')))
    conn.commit(); conn.close(); return jsonify({'success':True})

@app.route('/api/teacher/add_student', methods=['POST'])
@login_required(['teacher'])
def teacher_add_student():
    data = request.json; uid = session['user_id']
    school_id = session.get('school_id')
    for f in ['full_name','roll_no','grade','section']:
        if not (data.get(f) or '').strip(): return jsonify({'success':False,'error':f'{f} required'}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id FROM students WHERE roll_no=?", (data['roll_no'].strip(),))
    if c.fetchone(): conn.close(); return jsonify({'success':False,'error':'Student ID already exists'}), 400
    username = data['roll_no'].strip().lower(); password = data.get('password','fun123')
    c.execute("""INSERT INTO users (username,password_hash,role,full_name,school_id)
                 VALUES (?,?,?,?,?)""",
              (username, hash_pw(password), 'student', data['full_name'].strip(), school_id))
    new_uid = c.lastrowid
    c.execute("""INSERT INTO students
                 (user_id,roll_no,full_name,grade,section,age,teacher_id,school_id,avatar)
                 VALUES (?,?,?,?,?,?,?,?,?)""",
              (new_uid, data['roll_no'].strip(), data['full_name'].strip(),
               data['grade'].strip(), data['section'].strip(),
               int(data.get('age',5)), uid, school_id, data.get('avatar','star')))
    conn.commit(); conn.close()
    return jsonify({'success':True,'username':username,'password':password})

# ── PARENT API ────────────────────────────────────────────────────────────────
@app.route('/api/parent/overview')
@login_required(['parent'])
def parent_overview():
    uid = session['user_id']; conn = get_db(); c = conn.cursor()
    c.execute("""SELECT s.*,a.group_label as ai_group,a.accuracy_score,a.speed_score,
                        a.consistency_score,a.recommended_difficulty,a.improvement_areas
                 FROM students s LEFT JOIN ai_analysis a ON a.student_id=s.id
                   AND a.id=(SELECT MAX(id) FROM ai_analysis WHERE student_id=s.id)
                 WHERE s.parent_id=?""", (uid,))
    children = [dict(r) for r in c.fetchall()]
    children_data = []
    for child in children:
        cid = child['id']
        c.execute("SELECT * FROM game_sessions WHERE student_id=? AND ended_at IS NOT NULL ORDER BY started_at DESC LIMIT 10", (cid,))
        sessions = [dict(r) for r in c.fetchall()]
        c.execute("""SELECT DATE(started_at) as date,AVG(accuracy) as avg_acc,SUM(score) as total_score,SUM(stars_earned) as stars
                     FROM game_sessions WHERE student_id=? AND ended_at IS NOT NULL
                     GROUP BY DATE(started_at) ORDER BY date ASC LIMIT 14""", (cid,))
        trend = [dict(r) for r in c.fetchall()]
        c.execute("""SELECT operator_used,COUNT(*) as total,SUM(success) as correct FROM action_logs
                     WHERE student_id=? AND operator_used IS NOT NULL GROUP BY operator_used""", (cid,))
        op_stats = [dict(r) for r in c.fetchall()]
        c.execute("""SELECT tn.note,tn.created_at,u.full_name as teacher_name FROM teacher_notes tn
                     JOIN users u ON tn.teacher_id=u.id WHERE tn.student_id=?
                     ORDER BY tn.created_at DESC LIMIT 5""", (cid,))
        notes = [dict(r) for r in c.fetchall()]
        children_data.append({'info':child,'sessions':sessions,'trend':trend,'op_stats':op_stats,'notes':notes})
    c.execute("""SELECT * FROM announcements
                 WHERE role_target IN ('parent','all')
                   AND (school_id IS NULL OR school_id=?)
                 ORDER BY created_at DESC LIMIT 5""", (session.get('school_id'),))
    ann = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify({'children':children_data,'announcements':ann})

@app.route('/api/parent/link_child', methods=['POST'])
@login_required(['parent'])
def parent_link_child():
    data = request.json; uid = session['user_id']
    school_id = session.get('school_id')
    roll = (data.get('roll_no') or '').strip()
    if not roll: return jsonify({'success':False,'error':'Student ID required'}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT id,parent_id,full_name FROM students
                 WHERE roll_no=? AND (? IS NULL OR school_id=?)""",
              (roll, school_id, school_id))
    stu = c.fetchone()
    if not stu: conn.close(); return jsonify({'success':False,'error':'Student not found 😢'}), 404
    if stu['parent_id'] and stu['parent_id'] != uid:
        conn.close(); return jsonify({'success':False,'error':'Already linked to another parent'}), 400
    c.execute("UPDATE students SET parent_id=? WHERE roll_no=?", (uid, roll))
    conn.commit(); conn.close()
    return jsonify({'success':True,'child_name':stu['full_name']})

# ── ADMIN API ─────────────────────────────────────────────────────────────────
@app.route('/api/admin/overview')
@login_required(['admin'])
def admin_overview():
    conn = get_db(); c = conn.cursor()
    def scalar(q, *a): c.execute(q, a); return c.fetchone()[0]
    summary = {
        'total_schools':  scalar("SELECT COUNT(*) FROM schools"),
        'total_students': scalar("SELECT COUNT(*) FROM users WHERE role='student'"),
        'total_teachers': scalar("SELECT COUNT(*) FROM users WHERE role='teacher'"),
        'total_parents':  scalar("SELECT COUNT(*) FROM users WHERE role='parent'"),
        'total_sessions': scalar("SELECT COUNT(*) FROM game_sessions WHERE ended_at IS NOT NULL"),
        'global_accuracy':round(scalar("SELECT COALESCE(AVG(accuracy),0) FROM game_sessions WHERE ended_at IS NOT NULL"),2),
        'total_stars':    scalar("SELECT COALESCE(SUM(stars_earned),0) FROM game_sessions WHERE ended_at IS NOT NULL"),
    }
    c.execute("""SELECT s.*,u.username,u.last_login,u.is_active,sc.name as school_name,
                        a.group_label as ai_group,
                        a.accuracy_score,a.speed_score,a.recommended_difficulty
                 FROM students s JOIN users u ON s.user_id=u.id
                 LEFT JOIN schools sc ON sc.id=s.school_id
                 LEFT JOIN ai_analysis a ON a.student_id=s.id
                   AND a.id=(SELECT MAX(id) FROM ai_analysis WHERE student_id=s.id)
                 ORDER BY s.grade,s.total_score DESC""")
    all_students = [dict(r) for r in c.fetchall()]
    c.execute("""SELECT u.id,u.full_name,u.email,u.last_login,u.username,t.grades_assigned,
                        sc.name as school_name,
                        COUNT(s.id) as student_count
                 FROM teachers t JOIN users u ON t.user_id=u.id
                 LEFT JOIN schools sc ON sc.id=t.school_id
                 LEFT JOIN students s ON s.teacher_id=t.user_id GROUP BY t.user_id""")
    all_teachers = [dict(r) for r in c.fetchall()]
    c.execute("""SELECT u.id,u.full_name,u.email,u.username,u.last_login,sc.name as school_name,
                        COUNT(s.id) as child_count
                 FROM users u LEFT JOIN students s ON s.parent_id=u.id
                 LEFT JOIN schools sc ON sc.id=u.school_id
                 WHERE u.role='parent' GROUP BY u.id""")
    all_parents = [dict(r) for r in c.fetchall()]
    c.execute("""SELECT DATE(started_at) as date,COUNT(*) as sessions,
                        COALESCE(AVG(accuracy),0) as avg_acc,COALESCE(SUM(stars_earned),0) as stars
                 FROM game_sessions WHERE ended_at IS NOT NULL
                 GROUP BY DATE(started_at) ORDER BY date ASC LIMIT 14""")
    activity_trend = [dict(r) for r in c.fetchall()]
    c.execute("SELECT group_label,COUNT(*) as cnt FROM students GROUP BY group_label")
    group_dist = [dict(r) for r in c.fetchall()]
    c.execute("SELECT grade,COUNT(*) as cnt,AVG(avg_accuracy) as avg_acc,SUM(total_stars) as stars FROM students GROUP BY grade ORDER BY grade")
    grade_stats = [dict(r) for r in c.fetchall()]
    c.execute("""SELECT game_type,COUNT(*) as played,AVG(accuracy) as avg_acc,AVG(score) as avg_score
                 FROM game_sessions WHERE ended_at IS NOT NULL GROUP BY game_type ORDER BY played DESC""")
    game_stats = [dict(r) for r in c.fetchall()]
    c.execute("""SELECT a.*,u.full_name as author FROM announcements a
                 JOIN users u ON a.created_by=u.id ORDER BY a.created_at DESC LIMIT 10""")
    announcements = [dict(r) for r in c.fetchall()]
    c.execute("SELECT full_name,role,created_at FROM users ORDER BY created_at DESC LIMIT 10")
    recent_users = [dict(r) for r in c.fetchall()]
    c.execute("""SELECT sc.*,COUNT(DISTINCT s.id) as student_count,
                        COUNT(DISTINCT t.user_id) as teacher_count
                 FROM schools sc
                 LEFT JOIN students s ON s.school_id=sc.id
                 LEFT JOIN teachers t ON t.school_id=sc.id
                 GROUP BY sc.id ORDER BY sc.name""")
    schools = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify({'summary':summary,'all_students':all_students,'all_teachers':all_teachers,
                    'all_parents':all_parents,'activity_trend':activity_trend,'group_dist':group_dist,
                    'grade_stats':grade_stats,'game_stats':game_stats,'announcements':announcements,
                    'schools':schools,
                    'recent_users':recent_users})

@app.route('/api/admin/add_user', methods=['POST'])
@login_required(['admin'])
def admin_add_user():
    data = request.json; role = data.get('role','student')
    for f in ['username','password','full_name','role']:
        if not (data.get(f) or '').strip(): return jsonify({'success':False,'error':f'{f} required'}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (data['username'].strip(),))
    if c.fetchone(): conn.close(); return jsonify({'success':False,'error':'Username taken'}), 400
    school_id = data.get('school_id') or get_default_school_id(conn)
    c.execute("""INSERT INTO users (username,password_hash,role,full_name,email,school_id)
                 VALUES (?,?,?,?,?,?)""",
              (data['username'].strip(), hash_pw(data['password']), role,
               data['full_name'].strip(), data.get('email',''), None if role == 'admin' else school_id))
    uid = c.lastrowid
    if role == 'teacher':
        c.execute("INSERT INTO teachers (user_id,school_id,grades_assigned) VALUES (?,?,?)",
                  (uid, school_id, json.dumps(data.get('grades',[]))))
    elif role == 'student':
        c.execute("""INSERT INTO students
                     (user_id,roll_no,full_name,grade,section,age,school_id,avatar)
                     VALUES (?,?,?,?,?,?,?,?)""",
                  (uid, data.get('roll_no',str(uid)), data['full_name'].strip(),
                   data.get('grade','KG'), data.get('section','A'), int(data.get('age',5)),
                   school_id, data.get('avatar','star')))
    conn.commit(); conn.close(); return jsonify({'success':True})

@app.route('/api/admin/add_school', methods=['POST'])
@login_required(['admin'])
def admin_add_school():
    data = request.json
    name = (data.get('name') or '').strip()
    code = (data.get('code') or '').strip().upper()
    if not name or not code:
        return jsonify({'success':False,'error':'School name and code required'}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id FROM schools WHERE code=?", (code,))
    if c.fetchone():
        conn.close(); return jsonify({'success':False,'error':'School code already exists'}), 400
    c.execute("""INSERT INTO schools (name,code,city,contact_email,grade_config)
                 VALUES (?,?,?,?,?)""",
              (name, code, data.get('city',''), data.get('contact_email',''), json.dumps(data.get('grade_config',{}))))
    conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/admin/toggle_user', methods=['POST'])
@login_required(['admin'])
def admin_toggle_user():
    data = request.json; conn = get_db(); c = conn.cursor()
    c.execute("UPDATE users SET is_active=((is_active+1)%2) WHERE id=?", (data.get('user_id'),))
    conn.commit(); conn.close(); return jsonify({'success':True})

@app.route('/api/admin/announce', methods=['POST'])
@login_required(['admin'])
def admin_announce():
    data = request.json; uid = session['user_id']; conn = get_db(); c = conn.cursor()
    c.execute("""INSERT INTO announcements (created_by,school_id,role_target,title,body)
                 VALUES (?,?,?,?,?)""",
              (uid, None, data.get('role_target','all'), data.get('title',''), data.get('body','')))
    conn.commit(); conn.close(); return jsonify({'success':True})

@app.route('/api/admin/reset_student', methods=['POST'])
@login_required(['admin'])
def admin_reset_student():
    stu_id = request.json.get('student_id'); conn = get_db(); c = conn.cursor()
    for tbl in ['game_sessions','action_logs','ai_analysis']:
        c.execute(f"DELETE FROM {tbl} WHERE student_id=?", (stu_id,))
    c.execute("""UPDATE students SET total_sessions=0,total_score=0,avg_accuracy=0,
                 current_level=1,total_stars=0,group_label='Beginner' WHERE id=?""", (stu_id,))
    conn.commit(); conn.close(); return jsonify({'success':True})

@app.route('/api/leaderboard')
def leaderboard():
    grade = session.get('grade')
    conn = get_db(); c = conn.cursor()
    school_id = session.get('school_id')
    grade_rows = []
    if grade:
        c.execute("""SELECT full_name,roll_no,grade,section,total_score,total_sessions,
                            avg_accuracy,total_stars,group_label,avatar
                     FROM students WHERE grade=? AND (? IS NULL OR school_id=?)
                     ORDER BY total_score DESC,total_stars DESC,avg_accuracy DESC LIMIT 30""",
                  (grade, school_id, school_id))
        grade_rows = [dict(r) for r in c.fetchall()]
    c.execute("""SELECT full_name,roll_no,grade,section,total_score,total_sessions,
                        avg_accuracy,total_stars,group_label,avatar
                 FROM students WHERE (? IS NULL OR school_id=?)
                 ORDER BY total_score DESC,total_stars DESC,avg_accuracy DESC LIMIT 30""",
              (school_id, school_id))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify({'leaderboard':rows,'all_leaderboard':rows,'grade_leaderboard':grade_rows,'grade':grade})

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

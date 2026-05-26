CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin','teacher','student','parent')),
    full_name TEXT NOT NULL,
    email TEXT,
    school_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS schools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    city TEXT,
    contact_email TEXT,
    grade_config TEXT DEFAULT '{}',
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    roll_no TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    grade TEXT NOT NULL,
    section TEXT NOT NULL,
    age INTEGER DEFAULT 5,
    parent_id INTEGER,
    teacher_id INTEGER,
    school_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_sessions INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    total_stars INTEGER DEFAULT 0,
    avg_accuracy REAL DEFAULT 0,
    avg_reaction_time REAL DEFAULT 0,
    current_level INTEGER DEFAULT 1,
    group_label TEXT DEFAULT 'Beginner',
    avatar TEXT DEFAULT 'star',
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(parent_id) REFERENCES users(id),
    FOREIGN KEY(teacher_id) REFERENCES users(id),
    FOREIGN KEY(school_id) REFERENCES schools(id)
);
CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    school_id INTEGER,
    grades_assigned TEXT DEFAULT '[]',
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(school_id) REFERENCES schools(id)
);
CREATE TABLE IF NOT EXISTS game_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    game_type TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    score INTEGER DEFAULT 0,
    stars_earned INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    grade TEXT DEFAULT 'KG',
    difficulty TEXT DEFAULT 'easy',
    time_taken REAL DEFAULT 0,
    accuracy REAL DEFAULT 0,
    total_attempts INTEGER DEFAULT 0,
    correct_attempts INTEGER DEFAULT 0,
    combo_max INTEGER DEFAULT 0,
    hints_used INTEGER DEFAULT 0,
    operators_used TEXT DEFAULT '{}',
    FOREIGN KEY(student_id) REFERENCES students(id)
);
CREATE TABLE IF NOT EXISTS action_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reaction_time REAL DEFAULT 0,
    operator_used TEXT,
    operand1 REAL,
    operand2 REAL,
    target_value REAL,
    result_value REAL,
    success INTEGER DEFAULT 0,
    hint_used INTEGER DEFAULT 0,
    combo_count INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    difficulty TEXT DEFAULT 'easy',
    score_delta INTEGER DEFAULT 0,
    extra_data TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS ai_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    group_label TEXT,
    accuracy_score REAL,
    speed_score REAL,
    consistency_score REAL,
    operator_strengths TEXT DEFAULT '{}',
    operator_weaknesses TEXT DEFAULT '{}',
    recommended_difficulty TEXT,
    improvement_areas TEXT DEFAULT '[]',
    cluster_data TEXT DEFAULT '{}',
    FOREIGN KEY(student_id) REFERENCES students(id)
);
CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_by INTEGER NOT NULL,
    school_id INTEGER,
    role_target TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(created_by) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS teacher_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    note TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(teacher_id) REFERENCES users(id),
    FOREIGN KEY(student_id) REFERENCES students(id)
);

import sqlite3
import json
import math
from datetime import datetime

class AnalyticsEngine:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def analyze_student(self, student_id):
        conn = self.get_db()
        c = conn.cursor()

        # Get all sessions
        c.execute('''SELECT * FROM game_sessions WHERE student_id=? AND ended_at IS NOT NULL
                     ORDER BY started_at DESC''', (student_id,))
        sessions = [dict(r) for r in c.fetchall()]

        if not sessions:
            conn.close()
            return

        # Get action logs
        c.execute('''SELECT * FROM action_logs WHERE student_id=? ORDER BY timestamp DESC''',
                  (student_id,))
        actions = [dict(r) for r in c.fetchall()]

        # Calculate metrics
        accuracy_score = self._calc_accuracy(sessions, actions)
        speed_score = self._calc_speed(actions)
        consistency_score = self._calc_consistency(sessions)
        operator_stats = self._calc_operator_stats(actions)
        group_label = self._classify_student(accuracy_score, speed_score, consistency_score)
        recommended_difficulty = self._recommend_difficulty(accuracy_score, speed_score)
        improvement_areas = self._find_weaknesses(operator_stats, accuracy_score, speed_score)
        cluster_data = {
            'accuracy': round(accuracy_score, 2),
            'speed': round(speed_score, 2),
            'consistency': round(consistency_score, 2),
            'sessions_count': len(sessions)
        }

        # Upsert analysis
        c.execute('''INSERT INTO ai_analysis
                     (student_id, group_label, accuracy_score, speed_score, consistency_score,
                      operator_strengths, operator_weaknesses, recommended_difficulty,
                      improvement_areas, cluster_data)
                     VALUES (?,?,?,?,?,?,?,?,?,?)''',
                  (student_id, group_label,
                   round(accuracy_score, 2), round(speed_score, 2), round(consistency_score, 2),
                   json.dumps(operator_stats.get('strengths', {})),
                   json.dumps(operator_stats.get('weaknesses', {})),
                   recommended_difficulty,
                   json.dumps(improvement_areas),
                   json.dumps(cluster_data)))

        # Update student label
        c.execute('UPDATE students SET group_label=? WHERE id=?', (group_label, student_id))
        conn.commit()
        conn.close()

    def _calc_accuracy(self, sessions, actions):
        if not actions:
            return 0.0
        recent = actions[:100]  # Last 100 actions
        correct = sum(1 for a in recent if a['success'])
        return (correct / len(recent)) * 100

    def _calc_speed(self, actions):
        rts = [a['reaction_time'] for a in actions if a['reaction_time'] and a['reaction_time'] > 0]
        if not rts:
            return 50.0
        avg_rt = sum(rts) / len(rts)
        # Normalize: <1s = 100, >10s = 0
        score = max(0, min(100, (10 - avg_rt) / 9 * 100))
        return score

    def _calc_consistency(self, sessions):
        if len(sessions) < 2:
            return 50.0
        accuracies = [s['accuracy'] for s in sessions[:10] if s['accuracy'] is not None]
        if not accuracies:
            return 50.0
        mean = sum(accuracies) / len(accuracies)
        variance = sum((a - mean) ** 2 for a in accuracies) / len(accuracies)
        std = math.sqrt(variance)
        # Low std = high consistency
        consistency = max(0, min(100, 100 - std))
        return consistency

    def _calc_operator_stats(self, actions):
        op_stats = {}
        for action in actions:
            op = action.get('operator_used')
            if not op:
                continue
            if op not in op_stats:
                op_stats[op] = {'total': 0, 'correct': 0}
            op_stats[op]['total'] += 1
            if action['success']:
                op_stats[op]['correct'] += 1

        strengths = {}
        weaknesses = {}
        for op, stats in op_stats.items():
            if stats['total'] > 0:
                acc = stats['correct'] / stats['total'] * 100
                if acc >= 70:
                    strengths[op] = round(acc, 1)
                else:
                    weaknesses[op] = round(acc, 1)

        return {'strengths': strengths, 'weaknesses': weaknesses, 'raw': op_stats}

    def _classify_student(self, accuracy, speed, consistency):
        # Rule-based classification
        if accuracy >= 80 and speed >= 70:
            return 'Advanced'
        elif accuracy >= 65 and speed >= 50:
            return 'Intermediate'
        elif accuracy >= 70 and speed < 40:
            return 'Slow but Accurate'
        elif accuracy < 50 and speed >= 65:
            return 'Fast but Error-Prone'
        else:
            return 'Needs Support'

    def _recommend_difficulty(self, accuracy, speed):
        score = (accuracy * 0.6 + speed * 0.4)
        if score >= 75:
            return 'hard'
        elif score >= 50:
            return 'medium'
        else:
            return 'easy'

    def _find_weaknesses(self, operator_stats, accuracy, speed):
        areas = []
        weaknesses = operator_stats.get('weaknesses', {})
        for op, acc in weaknesses.items():
            op_names = {'+': 'Addition', '-': 'Subtraction', '*': 'Multiplication', '/': 'Division', '×': 'Multiplication', '÷': 'Division'}
            areas.append(f"{op_names.get(op, op)} ({acc:.0f}% accuracy)")
        if accuracy < 60:
            areas.append('Overall accuracy improvement needed')
        if speed < 40:
            areas.append('Response speed improvement needed')
        return areas

    def get_student_profile(self, student_id):
        conn = self.get_db()
        c = conn.cursor()

        c.execute('SELECT * FROM students WHERE id=?', (student_id,))
        student = dict(c.fetchone() or {})

        c.execute('''SELECT * FROM ai_analysis WHERE student_id=?
                     ORDER BY analyzed_at DESC LIMIT 1''', (student_id,))
        row = c.fetchone()
        analysis = dict(row) if row else {}

        c.execute('''SELECT game_type, COUNT(*) as sessions, AVG(accuracy) as avg_acc,
                     MAX(score) as best_score, AVG(score) as avg_score
                     FROM game_sessions WHERE student_id=? AND ended_at IS NOT NULL
                     GROUP BY game_type''', (student_id,))
        game_stats = [dict(r) for r in c.fetchall()]

        c.execute('''SELECT DATE(started_at) as date, AVG(accuracy) as acc, SUM(score) as sc
                     FROM game_sessions WHERE student_id=? AND ended_at IS NOT NULL
                     GROUP BY DATE(started_at) ORDER BY date ASC LIMIT 30''', (student_id,))
        trend = [dict(r) for r in c.fetchall()]

        conn.close()
        return {
            'student': student,
            'analysis': analysis,
            'game_stats': game_stats,
            'trend': trend
        }

    def get_adaptive_settings(self, student_id):
        conn = self.get_db()
        c = conn.cursor()
        c.execute('''SELECT * FROM ai_analysis WHERE student_id=?
                     ORDER BY analyzed_at DESC LIMIT 1''', (student_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            return {'difficulty': 'easy', 'speed_multiplier': 1.0, 'hint_level': 2, 'max_operators': ['+', '-']}

        analysis = dict(row)
        difficulty = analysis.get('recommended_difficulty', 'easy')

        settings = {
            'difficulty': difficulty,
            'hint_level': 2 if difficulty == 'easy' else (1 if difficulty == 'medium' else 0),
            'speed_multiplier': 0.8 if difficulty == 'easy' else (1.0 if difficulty == 'medium' else 1.4),
            'max_operators': ['+'] if difficulty == 'easy' else (['+', '-'] if difficulty == 'medium' else ['+', '-', '×', '÷']),
            'accuracy_score': analysis.get('accuracy_score', 0),
            'speed_score': analysis.get('speed_score', 0),
            'group_label': analysis.get('group_label', 'Unclassified')
        }
        return settings

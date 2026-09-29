import unittest
import os
import sqlite3
import jinja2
import py_compile

class OnlineVotingSystemTests(unittest.TestCase):
    def test_app_compilation(self):
        """Verify that app.py compiles without syntax errors."""
        res = py_compile.compile('app.py', doraise=True)
        self.assertIsNotNone(res)

    def test_templates_exist_and_render(self):
        """Verify that all core HTML templates exist and parse cleanly."""
        templates = [
            'home.html',
            'login.html',
            'register.html',
            'vote.html',
            'results.html',
            'admin.html',
            'verify_otp.html',
            'receipt.html'
        ]
        env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))
        for t in templates:
            with self.subTest(template=t):
                tmpl = env.get_template(t)
                self.assertIsNotNone(tmpl)

    def test_database_schema(self):
        """Verify the SQLite database tables schema creation."""
        conn = sqlite3.connect(':memory:')
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                voted INTEGER DEFAULT 0
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                votes INTEGER DEFAULT 0
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS vote_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                candidate_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        conn.commit()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        self.assertIn('users', tables)
        self.assertIn('candidates', tables)
        self.assertIn('vote_logs', tables)
        conn.close()

    def test_admin_audit_filter_integration(self):
        """Verify that admin template contains search, filter, and count elements."""
        with open(os.path.join('templates', 'admin.html'), 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('id="audit-search"', content)
        self.assertIn('id="candidate-filter"', content)
        self.assertIn('id="suspicious-only"', content)
        self.assertIn('filterAuditLogs', content)

    def test_registration_last_name_validation(self):
        """Verify that registration requires a valid, non-empty last name."""
        from app import app
        client = app.test_client()
        response = client.post('/register', data={
            'firstname': 'John',
            'lastname': '   ',
            'age': '25',
            'gender': 'Male',
            'email': 'john@example.com',
            'username': 'john_empty_last',
            'password': 'password123'
        })
        self.assertIn(b'Please provide a valid last name', response.data)

    def test_registration_last_name_persistence(self):
        """Verify that last name is correctly persisted to the database on registration."""
        from app import app, get_db_connection
        client = app.test_client()
        uname = 'testuser_lastname'
        response = client.post('/register', data={
            'firstname': 'Karthikeya',
            'lastname': 'Reddy',
            'age': '22',
            'gender': 'Male',
            'email': 'karthik_ln@example.com',
            'username': uname,
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        conn = get_db_connection()
        user = conn.execute("SELECT firstname, lastname FROM users WHERE username = ?", (uname,)).fetchone()
        conn.close()
        self.assertIsNotNone(user)
        self.assertEqual(user['firstname'], 'Karthikeya')
        self.assertEqual(user['lastname'], 'Reddy')

    def test_backward_compatibility_existing_users(self):
        """Verify backward compatibility: legacy user records without lastname still authenticate and function."""
        from app import app, get_db_connection
        from werkzeug.security import generate_password_hash
        conn = get_db_connection()
        legacy_uname = 'legacy_voter_test'
        conn.execute("DELETE FROM users WHERE username = ?", (legacy_uname,))
        conn.execute('''
            INSERT INTO users (firstname, lastname, age, email, gender, username, password, is_verified)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        ''', ('Legacy', '', 30, 'legacy@example.com', 'Other', legacy_uname, generate_password_hash('legacy123')))
        conn.commit()
        conn.close()

        client = app.test_client()
        login_res = client.post('/login', data={'username': legacy_uname, 'password': 'legacy123'})
        self.assertEqual(login_res.status_code, 302)
        self.assertIn('/vote', login_res.headers['Location'])

if __name__ == '__main__':
    unittest.main()


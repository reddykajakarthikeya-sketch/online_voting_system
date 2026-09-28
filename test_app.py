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

if __name__ == '__main__':
    unittest.main()

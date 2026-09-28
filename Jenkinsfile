pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out source code from Git...'
                checkout scm
            }
        }

        stage('Environment Validation') {
            steps {
                echo 'Validating build environment and installed tools...'
                bat 'python --version'
                bat 'pip --version'
                bat 'git --version'
            }
        }

        stage('Dependency Installation') {
            steps {
                echo 'Installing required Python dependencies from requirements.txt...'
                bat 'python -m pip install --upgrade pip'
                bat 'pip install -r requirements.txt'
            }
        }

        stage('Code Validation') {
            steps {
                echo 'Running Python syntax checks and compilation validation...'
                bat 'python -m py_compile app.py test_app.py'
            }
        }

        stage('Automated Testing') {
            steps {
                echo 'Executing automated unit test suite...'
                bat 'python -m unittest test_app.py'
            }
        }

        stage('Build & Package') {
            steps {
                echo 'Packaging and verifying build artifacts...'
                bat 'python -m py_compile app.py'
            }
        }

        stage('Deployment Readiness') {
            steps {
                echo 'Verifying deployment environment readiness...'
                bat 'python -c "import sqlite3; print(\'Database driver verified.\')"'
                echo 'Build and test verification passed. Ready for deployment.'
            }
        }
    }

    post {
        always {
            echo 'Pipeline execution complete.'
        }
        success {
            echo 'SUCCESS: All build stages, syntax validations, and automated unit tests passed!'
        }
        failure {
            echo 'FAILURE: One or more stages failed. Please inspect console logs.'
        }
    }
}

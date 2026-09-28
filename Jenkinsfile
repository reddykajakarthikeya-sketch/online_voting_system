pipeline {
    agent any

    environment {
        PYTHONUTF8 = '1'
        PYTHONIOENCODING = 'utf-8'
    }

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

        stage('Deploy Approval') {
            steps {
                input message: 'Do you want to deploy the application to local staging?', ok: 'Deploy'
            }
        }

        stage('Deploy Locally (Staging)') {
            steps {
                echo 'Deploying application to C:\\deploy\\online_voting_system...'
                bat '''
                    if not exist "C:\\deploy\\online_voting_system" mkdir "C:\\deploy\\online_voting_system"
                    xcopy /Y /E /I "templates" "C:\\deploy\\online_voting_system\\templates"
                    xcopy /Y /E /I "static" "C:\\deploy\\online_voting_system\\static"
                    copy /Y "app.py" "C:\\deploy\\online_voting_system\\app.py"
                    copy /Y "requirements.txt" "C:\\deploy\\online_voting_system\\requirements.txt"
                '''
                echo 'Initializing SQLite database schemas in target environment...'
                bat '''
                    cd /d "C:\\deploy\\online_voting_system"
                    python -c "import app; app.init_db(); print('Production database initialized successfully.')"
                '''
            }
        }

        stage('Automated Health Check') {
            steps {
                echo 'Executing automated smoke test on deployed application...'
                bat '''
                    cd /d "C:\\deploy\\online_voting_system"
                    python -c "from app import app; client = app.test_client(); res = client.get('/'); assert res.status_code == 200, f'Expected 200, got {res.status_code}'; print('Health Check Passed: HTTP 200 OK')"
                '''
            }
        }
    }

    post {
        always {
            echo 'Pipeline execution complete.'
        }
        success {
            echo 'SUCCESS: All CI/CD stages, automated unit tests, deployment, and health checks passed!'
        }
        failure {
            echo 'FAILURE: One or more pipeline stages failed. Inspect console logs.'
        }
    }
}

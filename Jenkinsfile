pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        lock resource: 'cilantro'
    }

    stages {
        stage('Prepare') {
            steps {
                echo 'Preparing..'
                sh 'make init'
                sh 'docker-compose build && docker-compose up -d'
            }
        }
        stage('Test backend') {
            steps {
                echo 'Testing backend..'
                sleep 10
                sh 'make test-backend'
            }
        }
        stage('Test frontend (unit)') {
            steps {
                echo 'Testing frontend (unit)..'
                sh 'make test-frontend'
            }
        }
        stage('Build code documentation') {
            when{
                branch 'master'
            }
            steps {
                echo 'Building docu..'
                sh 'make build-doc'
            }
        }
    }
    post {
        always {
            sh 'make down'
            sh 'docker-compose logs > docker.log -t'
            // clean documentation residues
            sh 'git clean -f'
            sh 'rm -rf doc/_build/doctrees/'
            archiveArtifacts artifacts: 'docker.log', fingerprint: true
        }
        success {
            script {  // Send back-to-normal notification
                if (env.BRANCH_NAME == 'master') {
                    if (currentBuild.previousBuild.result != 'SUCCESS') {
                        hipchatSend (color: 'GREEN', notify: true, room: 'workbench',
                            credentialId: '775b13ab-9054-4e02-9bdf-406af225865e',
                            message: "Back to Normal: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' (${env.BUILD_URL})")
                    }
                }
            }
        }
        failure {
            sh 'docker-compose logs'  // write docker logs to Jenkins' logs
            script {
                if (env.BRANCH_NAME == 'master') {
                    hipchatSend (color: 'RED', notify: true, room: 'workbench',
                        credentialId: '775b13ab-9054-4e02-9bdf-406af225865e',
                        message: "FAILED: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' (${env.BUILD_URL})")
                }
            }
        }
    }
}

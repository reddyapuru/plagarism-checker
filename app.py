from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
import hashlib
from plagiarism_checker import PlagiarismChecker

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests for local testing

@app.route('/')
def home():
    return "Welcome to the plagiarism checker!"

@app.route('/quizzes/plagarism-checker/check_plagiarism', methods=['POST'])
def check_plagiarism():
    try:
        detector = PlagiarismChecker()
        file = request.files.get('file')
        text = request.form.get('text')

        if file:
            file_path = os.path.join('uploads', file.filename)
            file.save(file_path)
            submission_data = detector.process_file(file_path)
        elif text:
            submission_data = {
                'submission_id': hashlib.md5(text.encode()).hexdigest(),
                'content': text,
                'file_type': 'text',
                'timestamp': datetime.utcnow().isoformat()
            }
        else:
            return jsonify({'error': 'No file or text provided'}), 400

        results = detector.detect_plagiarism(submission_data)
        return jsonify(results)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    app.run(debug=True)

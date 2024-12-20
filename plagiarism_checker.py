import os
import json
import requests
from bs4 import BeautifulSoup
import PyPDF2
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from datetime import datetime
import hashlib
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# Download required NLTK data
nltk.download('punkt')
nltk.download('stopwords')

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests for local testing

class PlagiarismChecker:
    def __init__(self, storage_dir='plagiarism_data'):
        self.storage_dir = storage_dir
        self.chunk_size = 1000  # words per chunk
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.stop_words = set(stopwords.words('english'))
        self.search_engine_url = "https://www.google.com/search?q="
        os.makedirs(storage_dir, exist_ok=True)
        os.makedirs(os.path.join(storage_dir, "chunks"), exist_ok=True)
        os.makedirs(os.path.join(storage_dir, "scraped_data"), exist_ok=True)
        logging.basicConfig(
            filename=os.path.join(storage_dir, 'plagiarism_checker.log'),
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def process_file(self, file_path):
        file_extension = os.path.splitext(file_path)[1].lower()
        content = ""
        try:
            if file_extension == '.pdf':
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        content += page.extract_text()
            elif file_extension == '.txt':
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
            submission_id = hashlib.md5(content.encode()).hexdigest()
            return {
                'submission_id': submission_id,
                'content': content,
                'file_type': file_extension,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logging.error(f"Error processing file: {str(e)}")
            raise

    def split_into_chunks(self, text):
        sentences = sent_tokenize(text)
        chunks = []
        current_chunk = []
        current_word_count = 0
        for sentence in sentences:
            words = word_tokenize(sentence)
            if current_word_count + len(words) <= self.chunk_size:
                current_chunk.append(sentence)
                current_word_count += len(words)
            else:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_word_count = len(words)
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        return chunks

    def scrape_web(self, query):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        results = []
        try:
            response = requests.get(f"{self.search_engine_url}{query}", headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            links = [a.get('href') for a in soup.find_all('a') if a.get('href') and a.get('href').startswith('http')]
            for link in links[:5]:
                try:
                    page_response = requests.get(link, headers=headers, timeout=10)
                    page_soup = BeautifulSoup(page_response.text, 'html.parser')
                    content = ' '.join([p.text for p in page_soup.find_all('p')])
                    results.append({
                        'url': link,
                        'content': content,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    time.sleep(2)
                except Exception as e:
                    logging.warning(f"Error scraping {link}: {str(e)}")
                    continue
        except Exception as e:
            logging.error(f"Error in web scraping: {str(e)}")
        return results

    def calculate_similarity(self, text1, text2):
        try:
            tfidf_matrix = self.vectorizer.fit_transform([text1, text2])
            similarity = (tfidf_matrix * tfidf_matrix.T).toarray()[0][1]
            return similarity
        except Exception as e:
            logging.error(f"Error calculating similarity: {str(e)}")
            return 0.0

    def detect_plagiarism(self, submission_data):
        results = {
            'submission_id': submission_data['submission_id'],
            'timestamp': datetime.utcnow().isoformat(),
            'chunks': [],
            'overall_similarity': 0.0
        }
        try:
            chunks = self.split_into_chunks(submission_data['content'])
            total_similarity = 0.0
            for idx, chunk in enumerate(chunks):
                chunk_results = []
                scraped_data = self.scrape_web(chunk[:200])
                for scraped_item in scraped_data:
                    similarity = self.calculate_similarity(chunk, scraped_item['content'])
                    if similarity > 0.3:
                        chunk_results.append({
                            'url': scraped_item['url'],
                            'similarity': round(similarity * 100, 2),
                            'matched_content': scraped_item['content'][:500]
                        })
                chunk_similarity = max([r['similarity'] for r in chunk_results]) if chunk_results else 0.0
                total_similarity += chunk_similarity
                results['chunks'].append({
                    'chunk_id': idx + 1,
                    'chunk_text': chunk[:500],
                    'similarity': chunk_similarity,
                    'matches': chunk_results
                })
            results['overall_similarity'] = round(total_similarity / len(chunks), 2)
            self.save_results(results)
            return results
        except Exception as e:
            logging.error(f"Error in plagiarism detection: {str(e)}")
            raise

    def save_results(self, results):
        try:
            file_path = os.path.join(self.storage_dir, f"results_{results['submission_id']}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving results: {str(e)}")
            raise

@app.route('/check_plagiarism', methods=['POST'])
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

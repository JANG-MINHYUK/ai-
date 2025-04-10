from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from process import process_video
from pathlib import Path
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

app = Flask(__name__)
CORS(app)

# 환경 변수에서 설정 로드
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', 'uploads'))
UPLOAD_DIR.mkdir(exist_ok=True)

OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', 'outputs'))
OUTPUT_DIR.mkdir(exist_ok=True)

# 허용된 파일 확장자
ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'mp4,avi,mov,mkv').split(','))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return jsonify({
        'status': 'success',
        'message': 'AI Video Editor API is running',
        'endpoints': {
            'upload': '/api/upload (POST)'
        }
    })

@app.route('/api/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported file format'}), 400
    
    try:
        # 안전한 파일명 생성
        filename = secure_filename(file.filename)
        video_path = UPLOAD_DIR / filename
        
        # 파일 저장
        file.save(str(video_path))
        
        # 비디오 처리
        result = process_video(str(video_path))
        
        # 상대 경로를 파일명만 반환하도록 수정
        video_filename = Path(result['video_path']).name
        subtitle_filename = Path(result['subtitle_path']).name
        
        return jsonify({
            'message': 'Processing complete',
            'filename': filename,
            'video_path': video_filename,
            'subtitle_path': subtitle_filename
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<path:filename>')
def download_file(filename):
    try:
        # 파일 경로를 절대 경로로 변환
        file_path = OUTPUT_DIR / secure_filename(filename)
        
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
            
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '127.0.0.1')
    debug = os.getenv('FLASK_DEBUG', '1') == '1'
    
    app.run(host=host, port=port, debug=debug)
import os
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from PIL import Image

# Initialize the RAG pipeline
from rag_pipeline import init_rag, ask_question_stream

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'pdf'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Setup uploads folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize RAG on startup
init_rag()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat_page')
def chat_page():
    return render_template('chat.html')


@app.route('/notes_page')
def notes_page():
    return render_template('notes.html')


from flask import Response

@app.route('/chat', methods=['POST'])
def chat():
    """RAG Chatbot"""
    data = request.json
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400

    user_message = data['message']
    return Response(ask_question_stream(user_message), mimetype='text/event-stream')


@app.route('/upload', methods=['POST'])
def digitize():
    """Convert handwritten notes (image/PDF) → Markdown"""

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported file type'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        # Model
        model = genai.GenerativeModel('gemini-2.5-flash')  # faster

        prompt = """
You are an expert AI that converts handwritten notes into clean, structured study material.

INSTRUCTIONS:
1. Extract all readable content accurately.
2. Convert into well-structured Markdown.
3. Use:
   - Headings (#, ##, ###)
   - Bullet points
   - Numbered lists
4. Highlight:
   - Key terms in **bold**
   - Definitions clearly
5. Fix grammar mistakes but DO NOT change meaning.
6. If unclear, write: [unclear]

OUTPUT:
- Clean Markdown
- Readable like textbook notes
"""

        ext = filename.rsplit('.', 1)[1].lower()

        if ext == 'pdf':
            uploaded_file = genai.upload_file(filepath, mime_type='application/pdf')
            response = model.generate_content([prompt, uploaded_file])

            try:
                genai.delete_file(uploaded_file.name)
            except Exception:
                pass

        else:
            img = Image.open(filepath)
            response = model.generate_content([prompt, img])

        os.remove(filepath)

        return jsonify({'markdown': response.text})

    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)

        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
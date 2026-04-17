import os
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from PIL import Image

# Initialize the RAG pipeline
from rag_pipeline import init_rag, ask_question

load_dotenv()

# Configure raw Gemini SDK for digitizing notes
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16MB max upload size
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

@app.route('/chat', methods=['POST'])
def chat():
    """Endpoint for the RAG Chatbot"""
    data = request.json
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400
    
    user_message = data['message']
    result = ask_question(user_message)
    return jsonify({
        'answer': result.get('answer', ''),
        'sources': result.get('sources', [])
    })

@app.route('/upload', methods=['POST'])
def digitize():
    """Endpoint for handwritten notes (image or PDF) to markdown feature"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported file type. Please upload an image or PDF.'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        # Initialize the Gemini Vision model
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = (
            "You are an expert at transcribing messy handwritten notes and formatting them beautifully. "
            "1. Read the provided handwritten notes.\n"
            "2. Convert them into clean, structured Markdown.\n"
            "3. Automatically mark and highlight (using bold or headings) the main topics and important concepts.\n"
            "4. Fix any obvious typos while preserving the original intent.\n"
            "Output strictly in Markdown format."
        )
        
        ext = filename.rsplit('.', 1)[1].lower()
        
        if ext == 'pdf':
            # Use Gemini's file upload API for PDFs
            uploaded_file = genai.upload_file(filepath, mime_type='application/pdf')
            response = model.generate_content([prompt, uploaded_file])
            # Clean up the uploaded reference from Gemini
            try:
                genai.delete_file(uploaded_file.name)
            except Exception:
                pass
        else:
            # Handle image files directly via PIL
            img = Image.open(filepath)
            response = model.generate_content([prompt, img])
        
        # Clean up the local uploaded file
        os.remove(filepath)
        
        return jsonify({'markdown': response.text})
        
    except Exception as e:
        # Clean up on error too
        if os.path.exists(filepath):
            os.remove(filepath)
        print(f"Error digitizing file: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

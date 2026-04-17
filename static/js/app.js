document.addEventListener('DOMContentLoaded', () => {

    // --- Chatbot Logic ---
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const chatBox = document.getElementById('chat-box');

    if (chatInput && sendBtn && chatBox) {
        function addMessage(text, sender) {
            const msgDiv = document.createElement('div');
            msgDiv.className = `message ${sender}-message`;
            const bubble = document.createElement('div');
            bubble.className = 'bubble';
            
            // Use marked for AI to render small markdowns returned
            if(sender === 'ai') {
                bubble.innerHTML = marked.parse(text);
            } else {
                bubble.textContent = text;
            }
            
            msgDiv.appendChild(bubble);
            chatBox.appendChild(msgDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        async function handleChat() {
            const msg = chatInput.value.trim();
            if (!msg) return;

            addMessage(msg, 'user');
            chatInput.value = '';
            chatInput.disabled = true;
            sendBtn.disabled = true;

            // Temporary Loading bubble
            const tempMsgDiv = document.createElement('div');
            tempMsgDiv.className = 'message ai-message temp-load';
            tempMsgDiv.innerHTML = '<div class="bubble">...</div>';
            chatBox.appendChild(tempMsgDiv);

            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: msg })
                });
                const data = await res.json();
                
                chatBox.removeChild(tempMsgDiv);
                if (data.answer) {
                    addMessage(data.answer, 'ai');
                    if (data.sources && data.sources.length > 0) {
                        const sourcesText = "\n\n**Sources:**\n" + data.sources.map(s => `- ${s.substring(0, 100)}...`).join("\n");
                        addMessage(sourcesText, 'ai');
                    }
                } else {
                    addMessage("I'm sorry, I couldn't understand the server response.", 'ai');
                }
            } catch (error) {
                chatBox.removeChild(tempMsgDiv);
                addMessage("An error occurred. Please make sure the backend is running.", 'ai');
            } finally {
                chatInput.disabled = false;
                sendBtn.disabled = false;
                chatInput.focus();
            }
        }

        sendBtn.addEventListener('click', handleChat);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') handleChat();
        });
    }

    // --- Notes Digitizer Logic ---
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const fileNameDisplay = document.getElementById('file-name');
    const processBtn = document.getElementById('process-btn');
    const resultArea = document.getElementById('result-area');
    const loader = document.getElementById('loader');
    const markdownOutput = document.getElementById('markdown-output');
    const resetBtn = document.getElementById('reset-btn');
    const copyBtn = document.getElementById('copy-btn');
    let selectedFile = null;

    if (uploadArea && processBtn) {
        // Trigger file input dialog on area click
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });

        // Drag and drop setup
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                handleFileSelect(e.dataTransfer.files[0]);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFileSelect(e.target.files[0]);
            }
        });

        function handleFileSelect(file) {
            const validTypes = file.type.startsWith('image/') || file.type === 'application/pdf';
            if (!validTypes) {
                alert('Please select an image or PDF file.');
                return;
            }
            selectedFile = file;
            fileNameDisplay.textContent = file.name;
            processBtn.disabled = false;
        }

        processBtn.addEventListener('click', async (e) => {
            e.stopPropagation(); // Prevent triggering the click on uploadArea
            if (!selectedFile) return;

            // UI state change
            uploadArea.classList.add('hidden');
            loader.classList.remove('hidden');

            const formData = new FormData();
            formData.append('file', selectedFile);

            try {
                const res = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                
                loader.classList.add('hidden');
                resultArea.classList.remove('hidden');

                if (data.markdown) {
                    // Render markdown via Marked.js
                    markdownOutput.innerHTML = marked.parse(data.markdown);
                } else {
                    markdownOutput.innerHTML = `<p style="color: red;">Error: ${data.error || 'Failed to process image'}</p>`;
                }
            } catch (error) {
                loader.classList.add('hidden');
                uploadArea.classList.remove('hidden');
                alert('Failed to connect to backend. Is Flask running?');
                console.error(error);
            }
        });

        resetBtn.addEventListener('click', () => {
            selectedFile = null;
            fileNameDisplay.textContent = 'No file selected';
            processBtn.disabled = true;
            resultArea.classList.add('hidden');
            uploadArea.classList.remove('hidden');
            fileInput.value = ''; // Clear input
        });

        copyBtn.addEventListener('click', () => {
            // Find raw markdown if available, else copy text content
            const textToCopy = markdownOutput.innerText;
            navigator.clipboard.writeText(textToCopy).then(() => {
                const originalText = copyBtn.textContent;
                copyBtn.textContent = 'Copied!';
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                }, 2000);
            });
        });
    }
});

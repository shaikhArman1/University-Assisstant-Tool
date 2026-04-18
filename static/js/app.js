document.addEventListener('DOMContentLoaded', () => {

    // --- Chatbot Logic ---
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const chatBox = document.getElementById('chat-box');

    if (chatInput && sendBtn && chatBox) {
        function addMessage(text, sender, showSource = false) {
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

            // Add source label below AI answer bubble
            if (sender === 'ai' && showSource) {
                const sourceLabel = document.createElement('span');
                sourceLabel.className = 'source-label';
                sourceLabel.textContent = 'source: University FAQs document';
                msgDiv.appendChild(sourceLabel);
            }

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
                chatBox.removeChild(tempMsgDiv);
                
                const msgDiv = document.createElement('div');
                msgDiv.className = 'message ai-message';
                const bubble = document.createElement('div');
                bubble.className = 'bubble';
                msgDiv.appendChild(bubble);
                chatBox.appendChild(msgDiv);
                
                const reader = res.body.getReader();
                const decoder = new TextDecoder('utf-8');
                let aiText = '';

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    
                    const chunkText = decoder.decode(value, { stream: true });
                    const lines = chunkText.split('\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const dataStr = line.replace('data: ', '').trim();
                            if (!dataStr) continue;
                            
                            try {
                                const data = JSON.parse(dataStr);
                                if (data.error) {
                                    aiText += "\n\n**Error**: " + data.error;
                                    bubble.innerHTML = marked.parse(aiText);
                                } else if (data.text) {
                                    aiText += data.text;
                                    bubble.innerHTML = marked.parse(aiText);
                                } else if (data.sources && data.sources.length > 0) {
                                    const sourceLabel = document.createElement('span');
                                    sourceLabel.className = 'source-label';
                                    sourceLabel.textContent = 'source: University FAQs document';
                                    msgDiv.appendChild(sourceLabel);
                                }
                            } catch (e) {
                                console.error("Error parsing stream data:", e);
                            }
                            
                            chatBox.scrollTop = chatBox.scrollHeight;
                        }
                    }
                }
            } catch (error) {
                if (chatBox.contains(tempMsgDiv)) {
                    chatBox.removeChild(tempMsgDiv);
                }
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
            const textToCopy = markdownOutput.innerText;
            navigator.clipboard.writeText(textToCopy).then(() => {
                const originalText = copyBtn.textContent;
                copyBtn.textContent = '✓ copied';
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                }, 2000);
            });
        });
    }
});

import streamlit as st
import streamlit.components.v1 as components
import json

def render_voice_assistant(speak_text: str = ""):
    """Renders a custom HTML/JS component in Streamlit for STT and TTS using browser Web Speech API."""
    
    # Escape speak text for JavaScript
    escaped_speak_text = json.dumps(speak_text)
    
    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: transparent;
                color: #e4e4e7;
                margin: 0;
                padding: 10px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }
            .card {
                background: rgba(17, 24, 39, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.08);
                backdrop-filter: blur(12px);
                border-radius: 12px;
                padding: 15px;
                width: 100%;
                max-width: 380px;
                text-align: center;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                box-sizing: border-box;
            }
            .mic-btn {
                background: linear-gradient(135deg, #6366f1, #4f46e5);
                border: none;
                border-radius: 50%;
                width: 70px;
                height: 70px;
                font-size: 28px;
                color: white;
                cursor: pointer;
                outline: none;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                margin: 10px 0;
                transition: all 0.3s ease;
                box-shadow: 0 4px 10px rgba(79, 70, 229, 0.4);
            }
            .mic-btn:hover {
                transform: scale(1.05);
                box-shadow: 0 6px 15px rgba(79, 70, 229, 0.6);
            }
            .mic-btn.recording {
                background: linear-gradient(135deg, #ef4444, #dc2626);
                animation: pulse 1.5s infinite;
                box-shadow: 0 4px 10px rgba(239, 68, 68, 0.4);
            }
            .status {
                font-size: 0.9rem;
                color: #a1a1aa;
                margin-top: 5px;
                font-weight: 500;
                height: 20px;
            }
            .transcript {
                font-size: 0.85rem;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                padding: 10px;
                margin-top: 10px;
                max-height: 80px;
                overflow-y: auto;
                color: #cbd5e1;
                border: 1px solid rgba(255,255,255,0.03);
                text-align: left;
                display: none;
            }
            .speaker-btn {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.15);
                color: #e4e4e7;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 0.8rem;
                cursor: pointer;
                margin-top: 8px;
                display: inline-flex;
                align-items: center;
                gap: 5px;
                transition: all 0.2s;
            }
            .speaker-btn:hover {
                background: rgba(255,255,255,0.15);
            }
            @keyframes pulse {
                0% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.08); opacity: 0.8; }
                100% { transform: scale(1); opacity: 1; }
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h4 style="margin: 0 0 5px 0; color: #818cf8; font-size: 1rem;">Voice Coding Mentor</h4>
            <div style="font-size: 0.75rem; color: #71717a; margin-bottom: 10px;">Click mic to speak, AI responds in voice!</div>
            
            <button id="micBtn" class="mic-btn">🎙️</button>
            <div id="status" class="status">Click to speak</div>
            
            <div id="transcriptBox" class="transcript"></div>
            
            <button id="speakerBtn" class="speaker-btn" style="display: none;">
                🔊 Replay Response
            </button>
        </div>

        <script>
            // Streamlit communications bridge
            function sendMessageToStreamlit(data) {
                // Standard Streamlit message channel
                window.parent.postMessage({
                    isStreamlitMessage: true,
                    type: "streamlit:setComponentValue",
                    value: data
                }, "*");
            }

            const micBtn = document.getElementById('micBtn');
            const statusDiv = document.getElementById('status');
            const transcriptBox = document.getElementById('transcriptBox');
            const speakerBtn = document.getElementById('speakerBtn');
            
            let recognition;
            let isRecording = false;
            let speakTextVal = {escaped_speak_text};

            // Initialize Speech Recognition
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (SpeechRecognition) {
                recognition = new SpeechRecognition();
                recognition.continuous = false;
                recognition.lang = 'en-US';
                recognition.interimResults = false;
                
                recognition.onstart = () => {
                    isRecording = true;
                    micBtn.classList.add('recording');
                    statusDiv.textContent = 'Listening...';
                    transcriptBox.style.display = 'none';
                    transcriptBox.textContent = '';
                };
                
                recognition.onresult = (event) => {
                    const result = event.results[0][0].transcript;
                    transcriptBox.textContent = "You said: " + result;
                    transcriptBox.style.display = 'block';
                    statusDiv.textContent = 'Processing...';
                    
                    // Send transcript back to Streamlit
                    setTimeout(() => {
                        sendMessageToStreamlit(result);
                    }, 500);
                };
                
                recognition.onerror = (event) => {
                    console.error('Speech recognition error', event.error);
                    statusDiv.textContent = 'Error: ' + event.error;
                    micBtn.classList.remove('recording');
                    isRecording = false;
                };
                
                recognition.onend = () => {
                    micBtn.classList.remove('recording');
                    isRecording = false;
                    if (statusDiv.textContent === 'Listening...') {
                        statusDiv.textContent = 'Finished listening';
                    }
                };
                
            } else {
                statusDiv.textContent = 'Voice recognition not supported';
                micBtn.disabled = true;
            }

            // Click Handler
            micBtn.addEventListener('click', () => {
                if (!recognition) return;
                
                // Stop any running speech synthesis
                window.speechSynthesis.cancel();
                
                if (isRecording) {
                    recognition.stop();
                } else {
                    recognition.start();
                }
            });

            // Text to Speech Function
            function speakText(text) {
                if (!text) return;
                window.speechSynthesis.cancel(); // Stop current speech
                
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = 'en-US';
                
                utterance.onstart = () => {
                    statusDiv.textContent = 'Speaking...';
                    speakerBtn.style.display = 'inline-flex';
                };
                
                utterance.onend = () => {
                    statusDiv.textContent = 'Click to speak';
                };
                
                window.speechSynthesis.speak(utterance);
            }

            // Auto-speak on load if speakText is provided
            window.addEventListener('load', () => {
                if (speakTextVal && speakTextVal.trim().length > 0) {
                    speakText(speakTextVal);
                }
            });

            speakerBtn.addEventListener('click', () => {
                speakText(speakTextVal);
            });
        </script>
    </body>
    </html>
    """.replace("{escaped_speak_text}", escaped_speak_text)
    
    # Render component
    components.html(html_code, height=220, scrolling=False)

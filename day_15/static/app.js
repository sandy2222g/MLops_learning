document.addEventListener("DOMContentLoaded", () => {
    // --- STYLING INJECTION FOR CITATIONS ---
    const citationStyle = document.createElement("style");
    citationStyle.innerHTML = `
        .citation-badge {
            background: rgba(6, 182, 212, 0.15);
            color: var(--color-secondary);
            border: 1px solid rgba(6, 182, 212, 0.3);
            border-radius: 4px;
            padding: 1px 5px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            display: inline-block;
            margin: 0 2px;
            transition: var(--transition-smooth);
        }
        .citation-badge:hover {
            background: rgba(6, 182, 212, 0.3);
            box-shadow: 0 0 8px rgba(6, 182, 212, 0.4);
            transform: scale(1.05);
        }
        .source-card.highlighted {
            border-color: var(--color-secondary);
            box-shadow: 0 0 15px rgba(6, 182, 212, 0.3);
            transform: scale(1.02);
        }
    `;
    document.head.appendChild(citationStyle);

    // --- STATE MANAGEMENT ---
    let systemState = {
        apiKeyConfigured: false,
        documents: [],
        totalChunks: 0,
        chatHistory: [],
        currentQuerySources: []
    };

    // --- DOM ELEMENT REFERENCES ---
    // Sidebar
    const apiStatusDot = document.getElementById("api-status-dot");
    const apiStatusText = document.getElementById("api-status-text");
    const toggleSettingsBtn = document.getElementById("toggle-settings-btn");
    const docCountBadge = document.getElementById("doc-count-badge");
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const docList = document.getElementById("doc-list");

    // Chat Panel
    const connectionStatusSubtext = document.getElementById("connection-status-subtext");
    const clearChatBtn = document.getElementById("clear-chat-btn");
    const chatMessages = document.getElementById("chat-messages");
    const welcomeScreen = document.getElementById("welcome-screen");
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");

    // Inspector Panel
    const inspectorCount = document.getElementById("inspector-count");
    const inspectorEmpty = document.getElementById("inspector-empty");
    const inspectorSourcesList = document.getElementById("inspector-sources");

    // Settings Modal
    const settingsModal = document.getElementById("settings-modal");
    const apiKeyInput = document.getElementById("api-key-input");
    const revealKeyBtn = document.getElementById("reveal-key-btn");
    const modalStatusBanner = document.getElementById("modal-status-banner");
    const cancelSettingsBtn = document.getElementById("cancel-settings-btn");
    const saveSettingsBtn = document.getElementById("save-settings-btn");
    const closeSettingsBtn = document.getElementById("close-settings-btn");

    // Toast Container
    const toastContainer = document.getElementById("toast-container");

    // --- TOAST NOTIFICATIONS ---
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        
        let icon = "ℹ️";
        if (type === "success") icon = "✅";
        if (type === "error") icon = "❌";
        
        toast.innerHTML = `<span>${icon}</span> <div>${message}</div>`;
        toastContainer.appendChild(toast);
        
        // Remove toast after 4s
        setTimeout(() => {
            toast.style.animation = "fadeIn 0.3s reverse forwards";
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 4000);
    }

    // --- API KEY HIDDEN / REVEAL ---
    revealKeyBtn.addEventListener("click", () => {
        if (apiKeyInput.type === "password") {
            apiKeyInput.type = "text";
            revealKeyBtn.textContent = "Hide";
        } else {
            apiKeyInput.type = "password";
            revealKeyBtn.textContent = "Show";
        }
    });

    // --- DYNAMIC SYSTEM STATUS CHECKS ---
    async function checkSystemStatus(isFirstLoad = false) {
        try {
            const response = await fetch("/api/status");
            if (!response.ok) throw new Error("Failed to contact server status.");
            
            const data = await response.json();
            systemState.apiKeyConfigured = data.api_key_configured;
            systemState.totalChunks = data.total_chunks_count;
            
            updateAPIKeyUI();
            
            if (isFirstLoad) {
                if (systemState.apiKeyConfigured) {
                    showToast("Gemini API is active and loaded.", "success");
                } else {
                    showToast("Please configure your Gemini API key to begin.", "info");
                    openSettingsModal();
                }
            }
        } catch (error) {
            console.error("Status check error:", error);
            showToast("Cannot connect to FastAPI server. Make sure it is running.", "error");
        }
    }

    function updateAPIKeyUI() {
        if (systemState.apiKeyConfigured) {
            apiStatusDot.classList.add("active");
            apiStatusText.textContent = "Connected";
            apiStatusText.className = "status-value text-green";
            connectionStatusSubtext.textContent = `Online • ${systemState.documents.length} files indexed (${systemState.totalChunks} chunks)`;
            sendBtn.disabled = false;
            chatInput.placeholder = "Ask about artwork restoration, conservation methods, damage repair...";
        } else {
            apiStatusDot.classList.remove("active");
            apiStatusText.textContent = "Disconnected";
            apiStatusText.className = "status-value text-red";
            connectionStatusSubtext.textContent = "Offline • Configure Gemini API key in Settings";
            sendBtn.disabled = true;
            chatInput.placeholder = "Please set your Gemini API key to query the assistant.";
        }
    }

    // --- MODAL CONTROLS ---
    function openSettingsModal() {
        settingsModal.style.display = "flex";
        modalStatusBanner.style.display = "none";
        apiKeyInput.value = "";
    }

    function closeSettingsModal() {
        settingsModal.style.display = "none";
    }

    toggleSettingsBtn.addEventListener("click", openSettingsModal);
    closeSettingsBtn.addEventListener("click", closeSettingsModal);
    cancelSettingsBtn.addEventListener("click", closeSettingsModal);

    saveSettingsBtn.addEventListener("click", async () => {
        const key = apiKeyInput.value.trim();
        if (!key) {
            showModalBanner("Please enter a valid key.", "error");
            return;
        }

        saveSettingsBtn.disabled = true;
        saveSettingsBtn.textContent = "Validating Key...";
        showModalBanner("Validating with Google Generative AI servers...", "info");

        try {
            const response = await fetch("/api/settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ api_key: key })
            });

            const data = await response.json();
            if (response.ok) {
                showToast("API configuration saved successfully!", "success");
                await checkSystemStatus();
                closeSettingsModal();
            } else {
                showModalBanner(data.detail || "Validation failed. Key may be invalid.", "error");
            }
        } catch (error) {
            showModalBanner("Failed to communicate with the settings endpoint.", "error");
        } finally {
            saveSettingsBtn.disabled = false;
            saveSettingsBtn.textContent = "Save Configurations";
        }
    });

    function showModalBanner(msg, type) {
        modalStatusBanner.textContent = msg;
        modalStatusBanner.className = `status-banner ${type}`;
        modalStatusBanner.style.display = "block";
    }

    // --- DOCUMENT MANAGEMENT ---
    async function loadDocuments() {
        try {
            const response = await fetch("/api/documents");
            if (!response.ok) throw new Error("Could not fetch document list.");
            
            const docs = await response.json();
            systemState.documents = docs;
            
            renderDocuments();
            await checkSystemStatus();
        } catch (error) {
            console.error("Load documents error:", error);
            showToast("Failed to load documents list from back-end.", "error");
        }
    }

    function renderDocuments() {
        docCountBadge.textContent = `${systemState.documents.length} File${systemState.documents.length !== 1 ? 's' : ''}`;
        
        if (systemState.documents.length === 0) {
            docList.innerHTML = `<div class="empty-list-msg">No files indexed yet. Upload guidelines to feed the model context.</div>`;
            return;
        }

        docList.innerHTML = "";
        systemState.documents.forEach(doc => {
            const item = document.createElement("div");
            item.className = "doc-item";
            
            const sizeKb = (doc.size_bytes / 1024).toFixed(1);
            
            item.innerHTML = `
                <div class="doc-info">
                    <div class="doc-name" title="${doc.filename}">${doc.filename}</div>
                    <div class="doc-meta">
                        <span>${sizeKb} KB</span>
                        <span>•</span>
                        <span>${doc.chunks} chunk${doc.chunks !== 1 ? 's' : ''}</span>
                    </div>
                </div>
                <button class="btn-delete" data-filename="${doc.filename}" title="Delete document">
                    <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            `;
            
            // Delete Listener
            item.querySelector(".btn-delete").addEventListener("click", async (e) => {
                const filename = e.currentTarget.getAttribute("data-filename");
                if (confirm(`Remove "${filename}" from the Knowledge Base? All indexed chunks will be deleted.`)) {
                    await deleteDocument(filename);
                }
            });
            
            docList.appendChild(item);
        });
    }

    async function deleteDocument(filename) {
        try {
            const response = await fetch(`/api/documents/${encodeURIComponent(filename)}`, {
                method: "DELETE"
            });
            const data = await response.json();
            if (response.ok) {
                showToast(data.message || "Document deleted.", "success");
                await loadDocuments();
            } else {
                showToast(data.detail || "Failed to delete document.", "error");
            }
        } catch (error) {
            showToast("Server error during document deletion.", "error");
        }
    }

    // --- DRAG & DROP FILE UPLOADS ---
    // Trigger file selection on click
    dropZone.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            handleFileUpload(fileInput.files[0]);
            fileInput.value = ""; // Reset
        }
    });

    // Dragover effects
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    async function handleFileUpload(file) {
        const allowedExts = [".txt", ".pdf", ".docx"];
        const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
        
        if (!allowedExts.includes(ext)) {
            showToast(`Unsupported format. Please upload TXT, PDF, or DOCX documents.`, "error");
            return;
        }

        // Show uploading toast
        showToast(`Uploading and indexing "${file.name}"...`, "info");
        
        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch("/api/upload", {
                method: "POST",
                body: formData
            });

            const data = await response.json();
            if (response.ok) {
                showToast(`Success! Indexed "${file.name}" in ${data.chunks_count} chunks.`, "success");
                await loadDocuments();
            } else {
                showToast(data.detail || "Failed to index file.", "error");
            }
        } catch (error) {
            showToast("Network failure uploading file.", "error");
        }
    }

    // --- CHAT CONSOLE LOGS & SENDING ---
    // Auto expand textarea
    chatInput.addEventListener("input", () => {
        chatInput.style.height = "auto";
        chatInput.style.height = (chatInput.scrollHeight) + "px";
    });

    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const text = chatInput.value.trim();
        if (!text) return;
        
        submitUserQuery(text);
    });

    // Handle keypress enter (except Shift+Enter)
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event("submit"));
        }
    });

    // Suggested query chips
    document.querySelectorAll(".prompt-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const text = chip.getAttribute("data-prompt");
            chatInput.value = text;
            chatInput.focus();
            chatInput.dispatchEvent(new Event("input")); // trigger auto-expand
            chatForm.dispatchEvent(new Event("submit")); // auto submit
        });
    });

    clearChatBtn.addEventListener("click", () => {
        if (confirm("Reset conversation? This will clear the chat history but leave your Knowledge Base documents intact.")) {
            // Clear message list but keep welcome screen if needed
            chatMessages.innerHTML = "";
            chatMessages.appendChild(welcomeScreen);
            welcomeScreen.style.display = "flex";
            
            // Clear inspector
            inspectorEmpty.style.display = "flex";
            inspectorSourcesList.style.display = "none";
            inspectorCount.textContent = "0 Chunks";
            
            systemState.chatHistory = [];
            systemState.currentQuerySources = [];
            showToast("Conversation cleared.", "info");
        }
    });

    function addMessageUI(text, sender, isMock = false) {
        // Hide splash screen if showing
        if (welcomeScreen.style.display !== "none") {
            welcomeScreen.style.display = "none";
        }

        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${sender}`;
        
        const bubble = document.createElement("div");
        bubble.className = "message-bubble";
        
        if (sender === "user") {
            bubble.textContent = text;
        } else {
            bubble.innerHTML = parseMarkdown(text);
        }
        
        const info = document.createElement("div");
        info.className = "message-info";
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        info.innerHTML = `<span>${sender === 'user' ? 'You' : 'Assistant'}</span> <span>•</span> <span>${time}</span>`;
        
        if (isMock) {
            info.innerHTML += ` <span>•</span> <span style="color:var(--amber-glow);font-weight:bold;">Mock Mode</span>`;
        }

        msgDiv.appendChild(bubble);
        msgDiv.appendChild(info);
        chatMessages.appendChild(msgDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addTypingIndicator() {
        const indicator = document.createElement("div");
        indicator.className = "message assistant typing-node";
        indicator.innerHTML = `
            <div class="message-bubble">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
            <div class="message-info">Thinking...</div>
        `;
        chatMessages.appendChild(indicator);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return indicator;
    }

    async function submitUserQuery(query) {
        if (!systemState.apiKeyConfigured) {
            showToast("Please supply a Gemini API Key to submit a query.", "error");
            openSettingsModal();
            return;
        }

        // Add user message
        addMessageUI(query, "user");
        
        // Reset input
        chatInput.value = "";
        chatInput.style.height = "auto";
        
        // Add typing animation
        const typingNode = addTypingIndicator();
        
        try {
            const response = await fetch("/api/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: query })
            });

            const data = await response.json();
            
            // Remove typing bubble
            typingNode.remove();

            if (response.ok) {
                const isMock = data.answer.includes("[MOCK MODE");
                addMessageUI(data.answer, "assistant", isMock);
                
                // Load inspector sources
                systemState.currentQuerySources = data.sources;
                renderInspector();
            } else {
                addMessageUI(`❌ **Backend Server Error:** ${data.detail || "An unexpected error occurred while communicating with Google Gemini SDK."}`, "assistant");
                showToast("Failed to fetch query response.", "error");
            }
        } catch (error) {
            typingNode.remove();
            addMessageUI("❌ **Network Failure:** Cannot establish a connection with the backend FastAPI engine. Please verify that your backend server is running local port 8000.", "assistant");
            showToast("Connection to FastAPI failed.", "error");
        }
    }

    // --- LIGHTWEIGHT MARKDOWN RENDERING + CITATIONS ---
    function parseMarkdown(text) {
        // Escape HTML
        let html = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
        
        // Headers: ####, ###, ##, #
        html = html.replace(/^#### (.*?)$/gm, "<h4>$1</h4>");
        html = html.replace(/^### (.*?)$/gm, "<h3>$1</h3>");
        html = html.replace(/^## (.*?)$/gm, "<h2>$1</h2>");
        html = html.replace(/^# (.*?)$/gm, "<h1>$1</h1>");
        
        // Bold: **text**
        html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        
        // Code Blocks: ```code```
        html = html.replace(/```([\s\S]*?)```/g, "<pre><code>$1</code></pre>");
        
        // Inline Code: `code`
        html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
        
        // Bullet Lists: - item or * item
        html = html.replace(/^\s*[\*\-]\s+(.*?)$/gm, "<li>$1</li>");
        
        // Citations: [Source 1], [Source 2], etc.
        html = html.replace(/\[Source\s*(\d+)\]/g, '<span class="citation-badge" onclick="window.highlightSource($1)">[Source $1]</span>');
        
        // Paragraph newlines
        html = html.replace(/\n/g, "<br>");
        
        return html;
    }

    // --- VECTOR SEARCH RESULTS INSPECTOR ---
    function renderInspector() {
        const sources = systemState.currentQuerySources;
        inspectorCount.textContent = `${sources.length} Chunk${sources.length !== 1 ? 's' : ''}`;
        
        if (sources.length === 0) {
            inspectorEmpty.style.display = "flex";
            inspectorSourcesList.style.display = "none";
            return;
        }

        inspectorEmpty.style.display = "none";
        inspectorSourcesList.style.display = "flex";
        
        inspectorSourcesList.innerHTML = "";
        
        sources.forEach((src, idx) => {
            const card = document.createElement("div");
            card.className = "source-card";
            card.id = `source-card-${idx + 1}`;
            
            const scorePct = (src.similarity * 100).toFixed(0);
            
            card.innerHTML = `
                <div class="source-header">
                    <div class="source-title-wrapper">
                        <span class="source-badge">${idx + 1}</span>
                        <div class="source-filename" title="${src.filename}">${src.filename}</div>
                    </div>
                    <div class="source-score-container">
                        <span class="score-text">${scorePct}% Match</span>
                        <div class="score-bar-bg">
                            <div class="score-bar-fill" style="width: ${scorePct}%"></div>
                        </div>
                    </div>
                </div>
                <div class="source-body">
                    <div class="source-snippet">${src.text}</div>
                </div>
            `;
            
            inspectorSourcesList.appendChild(card);
        });
    }

    // Global helper so that inline onclick attribute can call it
    window.highlightSource = function(idx) {
        const card = document.getElementById(`source-card-${idx}`);
        if (card) {
            // Remove highlight from any other cards
            document.querySelectorAll(".source-card").forEach(c => c.classList.remove("highlighted"));
            
            // Add highlight class
            card.classList.add("highlighted");
            
            // Scroll inspector panel to this card
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            
            // Remove highlight after 2.5s
            setTimeout(() => {
                card.classList.remove("highlighted");
            }, 2500);
        } else {
            showToast(`Document context Source ${idx} is no longer inside the active retrieved list.`, "info");
        }
    };

    // --- INITIALIZATION ---
    async function init() {
        await loadDocuments(); // This fetches files & calls status check
    }

    init();
});

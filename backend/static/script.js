document.addEventListener("DOMContentLoaded", () => {
    const phoneInput = document.getElementById("recipientPhone");
    const activeChatLabel = document.getElementById("activeChatLabel");
    const messageInput = document.getElementById("messageInput");
    const sendBtn = document.getElementById("sendBtn");
    const chatForm = document.getElementById("chatForm");
    const messagesContainer = document.getElementById("messagesContainer");
    const welcomeScreen = document.getElementById("welcomeScreen");
    const refreshBtn = document.getElementById("refreshBtn");

    let renderedMessageIds = new Set();
    let currentRecipient = "";

    // Sync input box changes to enable/disable chat layout
    function validateRecipient() {
        const rawValue = phoneInput.value.trim();
        // Remove leading plus sign if present for validation
        const value = rawValue.startsWith('+') ? rawValue.substring(1) : rawValue;

        // Standard phone number validation (usually 10-15 digits including country code)
        if (value.length >= 10 && !isNaN(value)) {
            currentRecipient = value;
            activeChatLabel.innerText = `+${currentRecipient}`;
            messageInput.disabled = false;
            sendBtn.disabled = false;
            if (welcomeScreen) {
                welcomeScreen.style.display = "none";
            }
        } else {
            currentRecipient = "";
            activeChatLabel.innerText = "Select a Recipient";
            messageInput.disabled = true;
            sendBtn.disabled = true;
            if (welcomeScreen) {
                welcomeScreen.style.display = "flex";
            }
        }
    }

    phoneInput.addEventListener("input", validateRecipient);
    validateRecipient(); // Initial check

    // Format timestamps nicely
    function formatTime(timestamp) {
        if (!timestamp) return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        // Handle UNIX timestamp formats
        const date = isNaN(timestamp) ? new Date(timestamp) : new Date(parseInt(timestamp) * 1000);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    // Helper to get status tick mark HTML
    function getStatusTick(status) {
        if (!status) return "";
        switch (status.toLowerCase()) {
            case "sent":
                return `<span class="status-icon sent"><i class="fas fa-check"></i></span>`;
            case "delivered":
                return `<span class="status-icon delivered"><i class="fas fa-check-double"></i></span>`;
            case "read":
                return `<span class="status-icon read"><i class="fas fa-check-double"></i></span>`;
            default:
                return "";
        }
    }

    // Render a single message bubble
    function renderMessage(msg) {
        const isSent = msg.sender.includes("Me") || msg.sender.includes("You");

        const bubble = document.createElement("div");
        bubble.className = `message-bubble ${isSent ? 'sent' : 'received'}`;
        bubble.dataset.id = msg.id;

        // Message text/content
        const contentDiv = document.createElement("div");
        contentDiv.className = "bubble-content";
        contentDiv.innerHTML = msg.text; // Allows <img> tags for images
        bubble.appendChild(contentDiv);

        // Time and ticks status
        const metaDiv = document.createElement("div");
        metaDiv.className = "bubble-meta";
        metaDiv.innerHTML = `
            <span class="timestamp">${formatTime(msg.timestamp)}</span>
            ${isSent ? getStatusTick(msg.status) : ""}
        `;
        bubble.appendChild(metaDiv);

        messagesContainer.appendChild(bubble);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Pull messages from API
    async function fetchMessages() {
        if (!currentRecipient) return;

        try {
            const res = await fetch("/messages");
            if (!res.ok) throw new Error("Failed to fetch messages");
            const data = await res.json();

            // Filter messages corresponding to the active recipient or outgoing messages to them
            const filteredMessages = data.filter(msg => {
                const cleanSender = msg.sender.startsWith('+') ? msg.sender.substring(1) : msg.sender;
                const cleanRecipient = msg.recipient.startsWith('+') ? msg.recipient.substring(1) : msg.recipient;

                const matchesIncoming = cleanSender === currentRecipient;
                const matchesOutgoing = (msg.sender.includes("Me") || msg.sender.includes("You")) && cleanRecipient === currentRecipient;
                return matchesIncoming || matchesOutgoing;
            });

            // Update existing or append new ones
            filteredMessages.forEach(msg => {
                if (!renderedMessageIds.has(msg.id)) {
                    renderMessage(msg);
                    renderedMessageIds.add(msg.id);
                } else {
                    // Update status ticks of existing messages if updated
                    const bubble = messagesContainer.querySelector(`[data-id="${msg.id}"]`);
                    if (bubble) {
                        const meta = bubble.querySelector(".bubble-meta");
                        const isSent = msg.sender.includes("Me") || msg.sender.includes("You");
                        if (meta && isSent) {
                            meta.innerHTML = `
                                <span class="timestamp">${formatTime(msg.timestamp)}</span>
                                ${getStatusTick(msg.status)}
                            `;
                        }
                    }
                }
            });
        } catch (err) {
            console.error("Fetch Error:", err);
        }
    }

    // Submit new message to recipient
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const text = messageInput.value.trim();
        if (!text || !currentRecipient) return;

        messageInput.value = "";
        messageInput.focus();

        try {
            const res = await fetch("/send", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    number: currentRecipient,
                    text: text
                })
            });

            const data = await res.json();
            if (data.success) {
                // Instantly render
                if (!renderedMessageIds.has(data.message.id)) {
                    renderMessage(data.message);
                    renderedMessageIds.add(data.message.id);
                }
            } else {
                alert(`Error: ${data.error || "Failed to send message"}`);
            }
        } catch (err) {
            console.error("Send Error:", err);
            alert("Network error. Could not reach server.");
        }
    });

    // Manual Refresh button
    refreshBtn.addEventListener("click", () => {
        messagesContainer.innerHTML = "";
        renderedMessageIds.clear();
        fetchMessages();
    });

    // Auto polling every 2 seconds
    setInterval(fetchMessages, 2000);

    // Initial load
    fetchMessages();
});

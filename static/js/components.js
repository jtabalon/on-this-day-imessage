/**
 * DOM rendering components for On This Day iMessage.
 */
const Components = {
    showConversationError(errorMessage) {
        document.getElementById("conversation-list").innerHTML = `
            <div class="error-state">
                <p>Could not load conversations. Make sure Full Disk Access is granted to your terminal.</p>
                <p style="margin-top: 8px; font-size: 12px;">${this._esc(errorMessage)}</p>
            </div>
        `;
    },

    renderConversationList(conversations, activeId, onClick, searchQuery) {
        const list = document.getElementById("conversation-list");

        if (conversations.length === 0) {
            const icon = searchQuery ? "🔍" : "📭";
            const msg = searchQuery
                ? `No conversations matching "${this._esc(searchQuery)}"`
                : "No conversations found for this day";
            list.innerHTML = `
                <div class="error-state" style="color: var(--text-secondary); padding: 60px 20px;">
                    <div class="empty-icon">${icon}</div>
                    <p>${msg}</p>
                </div>
            `;
            return;
        }

        list.innerHTML = conversations
            .map((conv) => {
                const initials = this._getInitials(conv.display_name);
                const colors = this._avatarColor(conv.display_name);
                const isActive = conv.chat_id === activeId;
                const yearBadges = conv.years
                    .map((y) => `<span class="year-badge">${y}</span>`)
                    .join("");

                return `
                <div class="conversation-item${isActive ? " active" : ""}"
                     data-chat-id="${conv.chat_id}">
                    <div class="conv-avatar" style="background:${colors}">${initials}</div>
                    <div class="conv-details">
                        <div class="conv-top-row">
                            <span class="conv-name">${this._esc(conv.display_name)}</span>
                            <span class="conv-meta">${conv.message_count} msg${conv.message_count !== 1 ? "s" : ""}</span>
                        </div>
                        <div class="conv-preview">${this._esc(conv.last_message_preview || "")}</div>
                        <div class="conv-years">${yearBadges}</div>
                    </div>
                </div>
                `;
            })
            .join("");

        // Attach click handlers
        list.querySelectorAll(".conversation-item").forEach((el) => {
            el.addEventListener("click", () => {
                const chatId = parseInt(el.dataset.chatId, 10);
                onClick(chatId);
            });
        });
    },

    /**
     * Render messages grouped by year.
     */
    renderMessages(data) {
        const container = document.getElementById("messages-container");
        const chatName = document.getElementById("chat-name");
        const yearNav = document.getElementById("year-nav");

        chatName.textContent = data.display_name;

        if (!data.year_groups || data.year_groups.length === 0) {
            container.innerHTML = `
                <div class="error-state" style="color: var(--text-secondary);">
                    <p>No messages found for this day</p>
                </div>
            `;
            yearNav.innerHTML = "";
            return;
        }

        // Year navigation pills
        yearNav.innerHTML = data.year_groups
            .map(
                (g) =>
                    `<button class="year-nav-btn" data-year="${g.year}">${g.year}</button>`
            )
            .join("");

        yearNav.querySelectorAll(".year-nav-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                const yearEl = document.getElementById(`year-${btn.dataset.year}`);
                if (yearEl) yearEl.scrollIntoView({ behavior: "smooth", block: "start" });
                yearNav.querySelectorAll(".year-nav-btn").forEach((b) => b.classList.remove("active"));
                btn.classList.add("active");
            });
        });

        // Render year groups
        let html = "";
        for (const group of data.year_groups) {
            html += `<div class="year-divider" id="year-${group.year}"><span>${group.year}</span></div>`;

            let prevFromMe = null;
            for (let i = 0; i < group.messages.length; i++) {
                const msg = group.messages[i];
                const isContinuation =
                    prevFromMe !== null && prevFromMe === msg.is_from_me;

                html += this._renderMessage(msg, data.is_group, isContinuation);
                prevFromMe = msg.is_from_me;
            }
        }

        container.innerHTML = html;

        // Add lightbox click handlers for images
        container.querySelectorAll(".bubble img").forEach((img) => {
            img.addEventListener("click", () => this._openLightbox(img.src));
        });

        // Scroll to bottom of first year group
        container.scrollTop = 0;
    },

    /**
     * Render a single message bubble.
     */
    _renderMessage(msg, isGroup, isContinuation) {
        const side = msg.is_from_me ? "from-me" : "from-them";
        const contClass = isContinuation ? " continuation" : "";

        let senderLabel = "";
        if (isGroup && !msg.is_from_me && !isContinuation && msg.sender) {
            senderLabel = `<div class="sender-label">${this._esc(msg.sender)}</div>`;
        }

        // Tapbacks
        let tapbacksHtml = "";
        if (msg.tapbacks && msg.tapbacks.length > 0) {
            const emojis = msg.tapbacks.map((t) => `<span class="tapback">${t.emoji}</span>`).join("");
            tapbacksHtml = `<div class="tapbacks">${emojis}</div>`;
        }

        // Content
        let content = "";
        if (msg.text) {
            content += this._esc(msg.text);
        }

        // Attachments
        if (msg.attachments && msg.attachments.length > 0) {
            for (const att of msg.attachments) {
                const url = att.url;
                const mime = att.mime_type || "";
                if (mime === "image/gif") {
                    content += `<img src="${url}" alt="${this._esc(att.filename)}">`;
                } else if (mime.startsWith("image/")) {
                    content += `<img src="${url}" alt="${this._esc(att.filename)}" loading="lazy">`;
                } else if (mime.startsWith("video/")) {
                    content += `<video src="${url}" controls preload="metadata" playsinline></video>`;
                } else if (mime.startsWith("audio/")) {
                    content += `<audio src="${url}" controls preload="metadata"></audio>`;
                } else {
                    content += `<a class="attachment-link" href="${url}" target="_blank">📎 ${this._esc(att.filename)}</a>`;
                }
            }
        }

        if (!content.trim()) {
            return ""; // skip empty messages
        }

        // Time
        const time = msg.date ? this._formatTime(msg.date) : "";
        const showTime = !isContinuation;

        return `
        <div class="message-row ${side}${contClass}">
            ${senderLabel}
            <div class="bubble-wrapper">
                ${tapbacksHtml}
                <div class="bubble">${content}</div>
            </div>
            ${showTime ? `<div class="message-time">${time}</div>` : ""}
        </div>
        `;
    },

    /**
     * Show loading state in messages area.
     */
    showMessagesLoading() {
        document.getElementById("messages-container").innerHTML =
            '<div class="loading">Loading messages</div>';
        document.getElementById("chat-name").textContent = "";
        document.getElementById("year-nav").innerHTML = "";
    },

    /**
     * Show loading state in sidebar.
     */
    showSidebarLoading() {
        document.getElementById("conversation-list").innerHTML =
            '<div class="loading">Loading conversations</div>';
    },

    /**
     * Show error in messages area.
     */
    showMessagesError(message) {
        document.getElementById("messages-container").innerHTML = `
            <div class="error-state">
                <p>${this._esc(message)}</p>
            </div>
        `;
    },

    /**
     * Show empty state.
     */
    showEmptyState() {
        document.getElementById("messages-container").innerHTML = `
            <div id="empty-state">
                <div class="empty-icon">💬</div>
                <p>Select a conversation to view messages from this day</p>
            </div>
        `;
        document.getElementById("chat-name").textContent = "";
        document.getElementById("year-nav").innerHTML = "";
    },

    // --- Helpers ---

    _openLightbox(src) {
        let lightbox = document.getElementById("lightbox");
        if (!lightbox) {
            lightbox = document.createElement("div");
            lightbox.id = "lightbox";
            lightbox.addEventListener("click", () => lightbox.classList.remove("visible"));
            lightbox.innerHTML = '<img>';
            document.body.appendChild(lightbox);
        }
        lightbox.querySelector("img").src = src;
        lightbox.classList.add("visible");
    },

    _formatTime(isoStr) {
        if (!isoStr) return "";
        const d = new Date(isoStr);
        return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    },

    _getInitials(name) {
        if (!name) return "?";
        const parts = name.split(/[\s,]+/).filter(Boolean);
        if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
        return (name[0] || "?").toUpperCase();
    },

    _avatarColor(name) {
        const colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
            "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F",
            "#BB8FCE", "#85C1E9", "#F0B27A", "#82E0AA",
        ];
        let hash = 0;
        for (let i = 0; i < (name || "").length; i++) {
            hash = name.charCodeAt(i) + ((hash << 5) - hash);
        }
        return colors[Math.abs(hash) % colors.length];
    },

    _esc(str) {
        if (!str) return "";
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    },
};

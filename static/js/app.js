/**
 * Main application — state management and event wiring.
 */
const App = {
    state: {
        month: null,
        day: null,
        activeChatId: null,
        conversations: [],
    },

    init() {
        const now = new Date();
        this.state.month = now.getMonth() + 1;
        this.state.day = now.getDate();

        this._setupDatePicker();
        this._setupBackButton();
        this._updateDateLabel();
        this.loadConversations();
    },

    async loadConversations() {
        Components.showSidebarLoading();
        Components.showEmptyState();
        this.state.activeChatId = null;

        try {
            const data = await API.getConversations(this.state.month, this.state.day);
            this.state.conversations = data.conversations;
            Components.renderConversationList(
                data.conversations,
                null,
                (chatId) => this.selectConversation(chatId)
            );
        } catch (err) {
            document.getElementById("conversation-list").innerHTML = `
                <div class="error-state">
                    <p>Could not load conversations. Make sure Full Disk Access is granted to your terminal.</p>
                    <p style="margin-top: 8px; font-size: 12px;">${err.message}</p>
                </div>
            `;
        }
    },

    async selectConversation(chatId) {
        this.state.activeChatId = chatId;

        // Update sidebar active state
        Components.renderConversationList(
            this.state.conversations,
            chatId,
            (id) => this.selectConversation(id)
        );

        // Show message area on mobile
        document.getElementById("message-area").classList.add("visible");

        Components.showMessagesLoading();

        try {
            const data = await API.getMessages(chatId, this.state.month, this.state.day);
            Components.renderMessages(data);
        } catch (err) {
            Components.showMessagesError(
                `Could not load messages: ${err.message}`
            );
        }
    },

    _setupDatePicker() {
        const picker = document.getElementById("date-picker");
        const todayBtn = document.getElementById("today-btn");

        // Set initial value
        const now = new Date();
        picker.value = this._toDateStr(now);

        picker.addEventListener("change", () => {
            if (!picker.value) return;
            const [y, m, d] = picker.value.split("-").map(Number);
            this.state.month = m;
            this.state.day = d;
            this._updateDateLabel();
            this.loadConversations();
        });

        todayBtn.addEventListener("click", () => {
            const now = new Date();
            this.state.month = now.getMonth() + 1;
            this.state.day = now.getDate();
            picker.value = this._toDateStr(now);
            this._updateDateLabel();
            this.loadConversations();
        });
    },

    _setupBackButton() {
        document.getElementById("back-btn").addEventListener("click", () => {
            document.getElementById("message-area").classList.remove("visible");
        });
    },

    _updateDateLabel() {
        const label = document.getElementById("date-label");
        // Format: "January 30"
        const d = new Date(2024, this.state.month - 1, this.state.day);
        label.textContent = d.toLocaleDateString("en-US", {
            month: "long",
            day: "numeric",
        });
    },

    _toDateStr(date) {
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, "0");
        const d = String(date.getDate()).padStart(2, "0");
        return `${y}-${m}-${d}`;
    },
};

// Boot
document.addEventListener("DOMContentLoaded", () => App.init());

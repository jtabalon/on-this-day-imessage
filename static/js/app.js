/**
 * Main application — state management and event wiring.
 */
const App = {
    state: {
        month: null,
        day: null,
        activeChatId: null,
        conversations: [],
        searchQuery: "",
    },

    init() {
        const now = new Date();
        this.state.month = now.getMonth() + 1;
        this.state.day = now.getDate();

        this._setupDatePicker();
        this._setupSearch();
        this._setupBackButton();
        this._updateDateLabel();
        this.loadConversations();
    },

    async loadConversations() {
        Components.showSidebarLoading();
        Components.showEmptyState();
        this.state.activeChatId = null;
        this.state.searchQuery = "";
        document.getElementById("search-input").value = "";

        try {
            const data = await API.getConversations(this.state.month, this.state.day);
            this.state.conversations = data.conversations;
            this._filterAndRenderConversations();
        } catch (err) {
            Components.showConversationError(err.message);
        }
    },

    async selectConversation(chatId) {
        this.state.activeChatId = chatId;

        // Update sidebar active state
        this._filterAndRenderConversations();

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

    _setupSearch() {
        const input = document.getElementById("search-input");
        input.addEventListener("input", () => {
            this.state.searchQuery = input.value;
            this._filterAndRenderConversations();
        });
    },

    _filterAndRenderConversations() {
        const q = this.state.searchQuery.toLowerCase().trim();
        let filtered = this.state.conversations;

        if (q) {
            filtered = filtered.filter((conv) => {
                if (conv.display_name && conv.display_name.toLowerCase().includes(q)) return true;
                if (conv.participants && conv.participants.some((p) => p.toLowerCase().includes(q))) return true;
                return false;
            });
        }

        Components.renderConversationList(
            filtered,
            this.state.activeChatId,
            (id) => this.selectConversation(id),
            this.state.searchQuery
        );
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

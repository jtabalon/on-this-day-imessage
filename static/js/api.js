/**
 * API fetch helpers for On This Day iMessage.
 */
const API = {
    async getConversations(month, day) {
        const params = new URLSearchParams({ month, day });
        const res = await fetch(`/api/conversations?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },

    async getMessages(chatId, month, day) {
        const params = new URLSearchParams({ month, day });
        const res = await fetch(`/api/conversations/${chatId}/messages?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },

    attachmentUrl(attachmentId) {
        return `/api/attachments/${attachmentId}`;
    },
};

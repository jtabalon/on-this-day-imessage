# On This Day — iMessage

A local web app that lets you browse your iMessage history by calendar day. Select any date and see all conversations that had messages on that month/day across every year — a "time hop" for your texts.

![macOS only](https://img.shields.io/badge/platform-macOS-lightgrey)

## Prerequisites

- **macOS** (reads the local iMessage database at `~/Library/Messages/chat.db`)
- **Python 3.10+**
- **Full Disk Access** granted to your terminal app (Terminal, iTerm2, etc.)

### Granting Full Disk Access

The app needs to read `chat.db`, which macOS protects. To grant access:

1. Open **System Settings > Privacy & Security > Full Disk Access**
2. Click the **+** button and add your terminal application
3. Restart your terminal

Without this, the app will show an error when loading conversations.

## Setup

```bash
# Clone the repository
git clone https://github.com/jtabalon/on-this-day-imessage.git
cd on-this-day-imessage

# Install dependencies
pip install -r requirements.txt

# Run the app
python run.py
```

The app starts at **http://127.0.0.1:8000**.

## Usage

### Browsing conversations

When the app loads, it shows all conversations that have messages on today's date. The sidebar lists each conversation with:

- Contact name (resolved from your macOS Contacts)
- Message count for this day
- A preview of the last message
- Year badges showing which years have messages on this day

Click a conversation to view its messages, grouped by year.

### Navigating dates

- **Date picker** — Select any date using the calendar input
- **Previous/Next buttons** — Click `‹` or `›` next to the date label to step one day at a time
- **Today button** — Jump back to today's date

### Searching conversations

Type a name in the search bar to filter conversations. The search matches against:

- **Display names** — The conversation name shown in the sidebar
- **Participant names** — Individual contact names within group chats

This means searching "Mom" will find a group chat named "Family" if Mom is a participant.

### Viewing messages

Messages are displayed in an iMessage-like bubble layout:

- **Blue bubbles** — Messages you sent
- **Gray bubbles** — Messages from others
- **Year dividers** — Separate messages by year
- **Year navigation pills** — Click a year to jump to that section
- **Tapback reactions** — Displayed as emoji badges on messages
- **Media** — Images, GIFs, videos, and audio play inline
- **HEIC images** — Automatically converted to JPEG for browser display

### Mobile layout

On narrow screens, the app switches to a single-panel layout. Tap a conversation to view messages, and use the back arrow to return to the conversation list.

## Architecture

```
on-this-day-imessage/
├── run.py                  # Entry point (uvicorn server)
├── requirements.txt        # Python dependencies
├── server/
│   ├── main.py             # FastAPI app setup
│   ├── database.py         # Read-only SQLite access to chat.db
│   ├── contacts.py         # macOS AddressBook name resolution
│   ├── message_parser.py   # Attributed body text extraction
│   └── routes/
│       ├── conversations.py  # GET /api/conversations
│       └── messages.py       # GET /api/conversations/:id/messages
│                             # GET /api/attachments/:id
└── static/
    ├── index.html           # Single-page app shell
    ├── css/styles.css       # All styles
    └── js/
        ├── api.js           # Fetch wrapper
        ├── components.js    # DOM rendering
        └── app.js           # State management and event wiring
```

### Key design decisions

- **Read-only database access** — The app opens `chat.db` in read-only mode and never modifies your iMessage data
- **Local only** — Runs on `127.0.0.1`, never exposed to the network
- **No external services** — All data stays on your machine; contact resolution uses the local AddressBook database
- **MIME type inference** — Older attachments with missing MIME types are identified by file extension so they render as media instead of download links

## API

| Endpoint | Description |
|---|---|
| `GET /api/conversations?month=M&day=D` | List conversations with messages on month/day |
| `GET /api/conversations/{chat_id}/messages?month=M&day=D` | Get messages for a conversation on month/day, grouped by year |
| `GET /api/attachments/{attachment_id}` | Serve an attachment file (with HEIC→JPEG conversion) |

## Troubleshooting

| Problem | Solution |
|---|---|
| "Could not load conversations" | Grant Full Disk Access to your terminal (see [Prerequisites](#granting-full-disk-access)) |
| Contact names show as phone numbers | Ensure your terminal has access to Contacts, or check that contacts exist in the macOS Contacts app |
| Attachments show as download links | Older attachments may have been purged from disk by macOS; the file no longer exists at the original path |
| Blank page on load | Check the terminal for Python errors; ensure you're on macOS with an iMessage account |

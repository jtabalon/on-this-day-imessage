"""Pydantic response models."""

from pydantic import BaseModel


class Attachment(BaseModel):
    id: int
    filename: str | None
    mime_type: str | None
    url: str


class Tapback(BaseModel):
    type: int  # 2000=loved, 2001=liked, 2002=disliked, 2003=laughed, 2004=emphasized, 2005=questioned
    emoji: str
    from_me: bool


class Message(BaseModel):
    id: int
    text: str | None
    is_from_me: bool
    date: str  # ISO 8601
    date_read: str | None
    year: int
    sender: str | None  # contact name or handle for group chats
    handle: str | None  # raw phone/email
    attachments: list[Attachment]
    tapbacks: list[Tapback]


class YearGroup(BaseModel):
    year: int
    messages: list[Message]


class ConversationSummary(BaseModel):
    chat_id: int
    display_name: str
    handles: list[str]
    is_group: bool
    message_count: int
    years: list[int]
    last_message_preview: str | None
    last_message_date: str | None


class ConversationMessages(BaseModel):
    chat_id: int
    display_name: str
    is_group: bool
    year_groups: list[YearGroup]

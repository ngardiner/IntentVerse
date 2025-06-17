import pytest
from fastapi import HTTPException
from app.state_manager import StateManager
from app.modules.email.tool import EmailTool

@pytest.fixture
def email_tool() -> EmailTool:
    """Provides a clean EmailTool instance for each test, initialized with a fresh StateManager."""
    state_manager = StateManager()
    return EmailTool(state_manager)

def test_initialization(email_tool: EmailTool):
    """Tests that the email tool initializes the state correctly."""
    email_state = email_tool.state_manager.get('email')
    assert email_state is not None
    assert 'sent_items' in email_state
    assert isinstance(email_state['sent_items'], list)
    assert len(email_state['sent_items']) == 0

def test_send_email(email_tool: EmailTool):
    """Tests the basic functionality of sending an email."""
    to = ["test@example.com"]
    subject = "Test Subject"
    body = "This is a test email."
    
    result = email_tool.send_email(to=to, subject=subject, body=body)

    # Check the return value
    assert result["status"] == "Email sent successfully"
    assert "email_id" in result
    assert result["email_id"].startswith("sent-")

    # Check the state
    sent_items = email_tool.state_manager.get('email')['sent_items']
    assert len(sent_items) == 1
    
    sent_email = sent_items[0]
    assert sent_email["to"] == to
    assert sent_email["subject"] == subject
    assert sent_email["body"] == body
    assert sent_email["cc"] == []

def test_send_email_with_cc(email_tool: EmailTool):
    """Tests sending an email with CC recipients."""
    to = ["primary@example.com"]
    cc = ["secondary@example.com"]
    subject = "Meeting Invite"
    body = "Please join us for the meeting."

    email_tool.send_email(to=to, subject=subject, body=body, cc=cc)

    sent_email = email_tool.state_manager.get('email')['sent_items'][0]
    assert sent_email["cc"] == cc

def test_list_sent_items(email_tool: EmailTool):
    """Tests listing sent items."""
    # Send a couple of emails
    email_tool.send_email(to=["one@example.com"], subject="First Email", body="Body 1")
    email_tool.send_email(to=["two@example.com"], subject="Second Email", body="Body 2")
    
    sent_list = email_tool.list_sent_items()
    
    assert len(sent_list) == 2
    sent_list.sort(key=lambda x: x['subject'])

    # Check that the list contains summaries, not full emails (no body)
    first_summary = sent_list[0]
    assert first_summary["email_id"].startswith("sent-")
    assert first_summary["subject"] == "First Email"
    assert "body" not in first_summary

def test_list_sent_items_with_limit(email_tool: EmailTool):
    """Tests the limit parameter when listing sent items."""
    for i in range(5):
        email_tool.send_email(to=[f"user{i}@test.com"], subject=f"Email {i}", body=f"Body {i}")

    sent_list = email_tool.list_sent_items(limit=3)
    assert len(sent_list) == 3
    assert sent_list[0]["subject"] == "Email 4"
    assert sent_list[1]["subject"] == "Email 3"
    assert sent_list[2]["subject"] == "Email 2"

def test_list_sent_items_empty(email_tool: EmailTool):
    """Tests listing when no emails have been sent."""
    assert email_tool.list_sent_items() == []

def test_read_email(email_tool: EmailTool):
    """Tests reading a specific email by its ID."""
    result = email_tool.send_email(to=["reader@example.com"], subject="Readable Email", body="Full content here.")
    email_id = result["email_id"]
    
    read_result = email_tool.read_email(email_id=email_id)
    
    # Check that the full email content is returned
    assert read_result["email_id"] == email_id
    assert read_result["subject"] == "Readable Email"
    assert read_result["body"] == "Full content here."

def test_read_nonexistent_email(email_tool: EmailTool):
    """Tests that reading a non-existent email ID raises a 404 HTTPException."""
    with pytest.raises(HTTPException) as excinfo:
        email_tool.read_email(email_id="nonexistent-id")
    assert excinfo.value.status_code == 404
    assert "not found" in excinfo.value.detail
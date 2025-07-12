import logging
from datetime import datetime, timezone, timedelta
import uuid
from ..base_tool import BaseTool
from fastapi import HTTPException
from typing import Any, Dict, List, Optional


class EmailTool(BaseTool):
    """
    Implements the logic for a fully functional email client.
    This class interacts with the global state managed by the StateManager.
    """

    def __init__(self, state_manager: Any):
        """
        Initializes the EmailTool with a reference to the state manager.

        Args:
            state_manager: An instance of the StateManager class.
        """
        super().__init__(state_manager)
        # Ensure the email state exists with 'inbox', 'sent_items', and 'drafts' lists
        if "email" not in self.state_manager.get_full_state():
            self.state_manager.set(
                "email", {"inbox": [], "sent_items": [], "drafts": []}
            )

    def get_ui_schema(self) -> Dict[str, Any]:
        """Returns the UI schema for the email module."""
        from .schema import UI_SCHEMA

        return UI_SCHEMA

    def send_email(
        self, to: List[str], subject: str, body: str, cc: List[str] = None
    ) -> Dict[str, str]:
        """
        Composes and sends an email to one or more recipients, recording it in the sent items.
        """
        sent_items = self.state_manager.get("email").get("sent_items", [])
        email_id = f"sent-{uuid.uuid4()}"

        email_data = {
            "email_id": email_id,
            "from": "user@intentverse.ai",
            "to": to,
            "cc": cc or [],
            "subject": subject,
            "body": body,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        sent_items.append(email_data)
        self.state_manager.get("email")["sent_items"] = sent_items

        logging.info(f"SENDING EMAIL to {to}: with subject: '{subject}'")
        return {"status": "Email sent successfully", "email_id": email_id}

    def list_emails(self, folder: str = "inbox", limit: int = 25) -> List[Dict[str, Any]]:
        """
        Lists a summary of emails from the specified folder.
        
        Args:
            folder: The folder to list emails from ('inbox', 'sent_items', or 'drafts')
            limit: Maximum number of emails to return
            
        Returns:
            List of email summaries
        """
        # Validate folder name
        valid_folders = ["inbox", "sent_items", "drafts"]
        if folder not in valid_folders:
            raise ValueError(f"Invalid folder name. Must be one of: {', '.join(valid_folders)}")
        
        # Ensure the email state exists
        if "email" not in self.state_manager.get_full_state():
            self.state_manager.set(
                "email", {"inbox": [], "sent_items": [], "drafts": []}
            )
        
        # Get emails from the specified folder
        email_state = self.state_manager.get("email") or {}
        emails = email_state.get(folder, [])
        
        # Return a summary, not the full body
        summaries = []
        for e in reversed(emails):
            # Ensure each email has an ID
            if "email_id" not in e:
                e["email_id"] = f"{folder}-{uuid.uuid4()}"
                
            summary = {
                "email_id": e["email_id"],
                "from": e.get("from", ""),
                "to": e.get("to", []),
                "subject": e.get("subject", ""),
                "timestamp": e.get("timestamp", ""),
                "read": e.get("read", True) if folder == "inbox" else None
            }
            summaries.append(summary)
        return summaries[:limit]

    def read_email(self, email_id: str) -> Dict[str, Any]:
        """
        Reads the full content of a specific email in any folder using its unique ID.
        """
        # Ensure the email state exists
        if "email" not in self.state_manager.get_full_state():
            self.state_manager.set(
                "email", {"inbox": [], "sent_items": [], "drafts": []}
            )
            
        email_state = self.state_manager.get("email") or {}
        inbox = email_state.get("inbox", [])
        sent_items = email_state.get("sent_items", [])
        drafts = email_state.get("drafts", [])

        for email in inbox + sent_items + drafts:
            if email.get("email_id") == email_id:
                # If this is an inbox email, mark it as read
                if email.get("read") is False and email in inbox:
                    email["read"] = True
                return email

        raise HTTPException(
            status_code=404, detail=f"Email with ID '{email_id}' not found."
        )

    def create_draft(
        self,
        to: Optional[List[str]] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Creates a draft email without sending it. Returns the email_id of the draft.
        """
        drafts = self.state_manager.get("email").get("drafts", [])
        draft_id = f"draft-{uuid.uuid4()}"

        draft_data = {
            "email_id": draft_id,
            "to": to or [],
            "cc": [],
            "subject": subject or "",
            "body": body or "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        drafts.append(draft_data)
        self.state_manager.get("email")["drafts"] = drafts

        return {"status": "Draft created successfully", "email_id": draft_id}

    def update_draft(
        self,
        email_id: str,
        to: Optional[List[str]] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        Updates the fields of an existing draft email.
        NOTE: Attachment logic is a placeholder and depends on the FileSystemTool.
        """
        drafts = self.state_manager.get("email").get("drafts", [])
        draft_to_update = None
        for draft in drafts:
            if draft["email_id"] == email_id:
                draft_to_update = draft
                break

        if not draft_to_update:
            raise HTTPException(
                status_code=404, detail=f"Draft with ID '{email_id}' not found."
            )

        if to is not None:
            draft_to_update["to"] = to
        if subject is not None:
            draft_to_update["subject"] = subject
        if body is not None:
            draft_to_update["body"] = body
        if attachments is not None:
            # Placeholder for future logic to verify file paths exist
            draft_to_update["attachments"] = attachments

        self.state_manager.get("email")["drafts"] = drafts
        return {"status": "Draft updated successfully", "email_id": email_id}

    def update_email(
        self,
        email_id: str,
        from_address: Optional[str] = None,
        to: Optional[List[str]] = None,
        cc: Optional[List[str]] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Updates the fields of an existing email (inbox or sent items).
        """
        email_state = self.state_manager.get("email")
        inbox = email_state.get("inbox", [])
        sent_items = email_state.get("sent_items", [])

        # Check inbox first
        for email in inbox:
            if email["email_id"] == email_id:
                if from_address is not None:
                    email["from"] = from_address
                if to is not None:
                    email["to"] = to
                if cc is not None:
                    email["cc"] = cc
                if subject is not None:
                    email["subject"] = subject
                if body is not None:
                    email["body"] = body
                return {"status": "Email updated successfully", "email_id": email_id}

        # Then check sent items
        for email in sent_items:
            if email["email_id"] == email_id:
                if from_address is not None:
                    email["from"] = from_address
                if to is not None:
                    email["to"] = to
                if cc is not None:
                    email["cc"] = cc
                if subject is not None:
                    email["subject"] = subject
                if body is not None:
                    email["body"] = body
                return {"status": "Email updated successfully", "email_id": email_id}

        raise HTTPException(
            status_code=404, detail=f"Email with ID '{email_id}' not found."
        )

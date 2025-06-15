from ..base_tool import BaseTool
from typing import Any, Dict, List

class EmailTool(BaseTool):
    """
    Implements the logic for email tools.
    This class interacts with the global state managed by the StateManager.
    """

    def __init__(self, state_manager: Any):
        """
        Initializes the EmailTool with a reference to the state manager.

        Args:
            state_manager: An instance of the StateManager class.
        """
        self.state_manager = state_manager
        # Ensure the email state exists with a 'sent_items' list
        if 'email' not in self.state_manager.get_full_state():
            self.state_manager.set('email', {'sent_items': []})

    def send_email(self, to: List[str], subject: str, body: str, cc: List[str] = None) -> Dict[str, str]:
        """
        Simulates sending an email and records it in the state.
        NOTE: Placeholder logic.
        """
        sent_items = self.state_manager.get('email')['sent_items']
        email_id = f"sent-{len(sent_items) + 1}"
        
        email_data = {
            "email_id": email_id,
            "to": to,
            "cc": cc or [],
            "subject": subject,
            "body": body,
            "timestamp": "YYYY-MM-DDTHH:MM:SSZ" # Placeholder for a real timestamp
        }

        sent_items.append(email_data)
        self.state_manager.set('email', {'sent_items': sent_items})
        
        print(f"SENDING EMAIL to {to}: {subject}")
        return {"status": "Email sent successfully", "email_id": email_id}

    def list_sent_items(self, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Lists a summary of emails that have been sent.
        NOTE: Placeholder logic.
        """
        sent_items = self.state_manager.get('email').get('sent_items', [])
        # Return a summary, not the full body
        summaries = [
            {"email_id": e["email_id"], "to": e["to"], "subject": e["subject"], "timestamp": e["timestamp"]}
            for e in sent_items
        ]
        return summaries[:limit]

    def read_email(self, email_id: str) -> Dict[str, Any]:
        """
        Reads the full content of a specific sent email.
        NOTE: Placeholder logic.
        """
        sent_items = self.state_manager.get('email').get('sent_items', [])
        for email in sent_items:
            if email["email_id"] == email_id:
                return email
        return {"error": "Email not found."}

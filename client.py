import requests
import logging
from typing import List, Optional, Dict
from .types import Domain, Account, TokenResponse, Message, MessageDetail, MessageSource, Attachment, MessageRecipient

# Set up logging
logger = logging.getLogger(__name__)

class MailTMClient:
    BASE_URL = "https://api.mail.tm"

    def __init__(self, account: Optional[str] = None, password: Optional[str] = None, token: Optional[str] = None, proxies: Optional[Dict[str, str]] = None):
        self.session = requests.Session()
        self.account: Optional[Account] = None
        self.token: Optional[str] = token
        self.account_address: Optional[str] = account
        self.account_password: Optional[str] = password
        self.proxies: Optional[Dict[str, str]] = proxies

        # Set proxies if provided
        if self.proxies:
            logger.debug(f"Setting proxies: {self.proxies}")
            self.session.proxies.update(self.proxies)

        if account and password:
            logger.debug("Fetching token using account and password.")
            self.token = self.get_token(account, password).token
            self.account = self.get_account(self.token)
        elif token:
            logger.debug("Fetching account information using provided token.")
            self.account = self.get_account(token)
        else:
            logger.error("No account or token provided.")
            raise ValueError("No account or token provided.")

        # Set default headers for the session
        if self.token:
            logger.debug(f"Setting authorization header with token: {self.token}")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    @staticmethod
    def _convert_special_keys(data: dict) -> dict:
        """Convert special keys like @id to a_id."""
        converted = {key.replace('@', 'a_'): value for key, value in data.items()}
        if 'from' in converted:
            converted['from_'] = converted.pop('from')  # Handle 'from' keyword
        return converted

    @staticmethod
    def get_domains(page: int = 1, proxies: Optional[Dict[str, str]] = None) -> List[Domain]:
        """Fetch available domains."""
        logger.debug(f"Fetching domains from page: {page}")
        response = requests.get(f"{MailTMClient.BASE_URL}/domains", params={"page": page}, proxies=proxies)
        response.raise_for_status()
        domains_data = response.json().get('hydra:member', [])
        logger.debug(f"Domains fetched: {domains_data}")
        return [Domain(**MailTMClient._convert_special_keys(domain)) for domain in domains_data]

    @staticmethod
    def get_domain_by_id(domain_id: str, proxies: Optional[Dict[str, str]] = None) -> Domain:
        """Retrieve a domain by its id."""
        logger.debug(f"Fetching domain by ID: {domain_id}")
        response = requests.get(f"{MailTMClient.BASE_URL}/domains/{domain_id}", proxies=proxies)
        response.raise_for_status()
        logger.debug(f"Domain fetched: {response.json()}")
        return Domain(**MailTMClient._convert_special_keys(response.json()))

    @staticmethod
    def create_account(address: str, password: str, proxies: Optional[Dict[str, str]] = None) -> Account:
        """Create a new account."""
        logger.debug(f"Creating account with address: {address}")
        payload = {"address": address, "password": password}
        response = requests.post(f"{MailTMClient.BASE_URL}/accounts", json=payload, proxies=proxies)
        response.raise_for_status()
        logger.debug(f"Account created: {response.json()}")
        return Account(**MailTMClient._convert_special_keys(response.json()))

    def get_token(self, address: str, password: str) -> TokenResponse:
        """Authenticate and get a token."""
        logger.debug(f"Getting token for address: {address}")
        payload = {"address": address, "password": password}
        response = self.session.post(f"{self.BASE_URL}/token", json=payload)
        response.raise_for_status()
        logger.debug(f"Token received: {response.json()}")
        return TokenResponse(**self._convert_special_keys(response.json()))

    def get_account(self, token: Optional[str] = None) -> Account:
        """Get account details for the authenticated account."""
        logger.debug("Fetching account details.")
        if token:
            headers = {"Authorization": f"Bearer {token}"}
            response = self.session.get(f"{self.BASE_URL}/me", headers=headers)
        else:
            response = self.session.get(f"{self.BASE_URL}/me")
        response.raise_for_status()
        logger.debug(f"Account details fetched: {response.json()}")
        return Account(**self._convert_special_keys(response.json()))

    def get_account_by_id(self, account_id: str) -> Account:
        """Get account details by account ID."""
        logger.debug(f"Fetching account by ID: {account_id}")
        response = self.session.get(f"{self.BASE_URL}/accounts/{account_id}")
        response.raise_for_status()
        logger.debug(f"Account details fetched: {response.json()}")
        return Account(**self._convert_special_keys(response.json()))

    def delete_account(self, account_id: str) -> bool:
        """Delete an account."""
        logger.debug(f"Deleting account with ID: {account_id}")
        response = self.session.delete(f"{self.BASE_URL}/accounts/{account_id}")
        if response.status_code == 204:
            logger.debug("Account successfully deleted.")
            return True
        response.raise_for_status()
        return False

    def get_messages(self, page: int = 1) -> List[Message]:
        """Get messages for the authenticated account."""
        logger.debug(f"Fetching messages from page: {page}")
        response = self.session.get(f"{self.BASE_URL}/messages", params={"page": page})
        response.raise_for_status()
        messages_data = response.json().get('hydra:member', [])
        logger.debug(f"Messages fetched: {messages_data}")
        return [Message(**self._convert_special_keys(message)) for message in messages_data]

    def get_message_by_id(self, message_id: str) -> MessageDetail:
        """Retrieve a specific message by its ID."""
        logger.debug(f"Fetching message by ID: {message_id}")
        response = self.session.get(f"{self.BASE_URL}/messages/{message_id}")
        response.raise_for_status()
        logger.debug(f"Message details fetched: {response.json()}")
        return MessageDetail(**self._convert_special_keys(response.json()))

    def delete_message(self, message_id: str) -> bool:
        """Delete a specific message by its ID."""
        logger.debug(f"Deleting message with ID: {message_id}")
        response = self.session.delete(f"{self.BASE_URL}/messages/{message_id}")
        if response.status_code == 204:
            logger.debug("Message successfully deleted.")
            return True
        response.raise_for_status()
        return False

    def mark_message_as_read(self, message_id: str) -> MessageDetail:
        """Mark a message as read."""
        logger.debug(f"Marking message as read with ID: {message_id}")
        response = self.session.patch(f"{self.BASE_URL}/messages/{message_id}")
        response.raise_for_status()
        logger.debug(f"Message marked as read: {response.json()}")
        return MessageDetail(**self._convert_special_keys(response.json()))

    def get_message_source(self, message_id: str) -> MessageSource:
        """Get the raw source of a message."""
        logger.debug(f"Fetching message source for ID: {message_id}")
        response = self.session.get(f"{self.BASE_URL}/sources/{message_id}")
        response.raise_for_status()
        logger.debug(f"Message source fetched: {response.json()}")
        return MessageSource(**self._convert_special_keys(response.json()))

    def get_message_attachments(self, message_id: str) -> List[Attachment]:
        """Get the attachments of a specific message by its ID."""
        logger.debug(f"Fetching attachments for message ID: {message_id}")
        response = self.session.get(f"{self.BASE_URL}/messages/{message_id}/attachments")
        response.raise_for_status()
        attachments_data = response.json()
        logger.debug(f"Attachments fetched: {attachments_data}")
        return [Attachment(**self._convert_special_keys(attachment)) for attachment in attachments_data]

    def get_attachment(self, message_id: str, attachment_id: str) -> Attachment:
        """Get a specific attachment by its ID."""
        logger.debug(f"Fetching attachment with ID: {attachment_id} for message ID: {message_id}")
        response = self.session.get(f"{self.BASE_URL}/messages/{message_id}/attachments/{attachment_id}")
        response.raise_for_status()
        logger.debug(f"Attachment fetched: {response.json()}")
        return Attachment(**self._convert_special_keys(response.json()))

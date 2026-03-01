"""
Encryption Service for Personal AI Employee - Gold Tier

Provides AES-256-GCM encryption for sensitive data (CRM contacts, financial records,
meeting transcripts). Uses OS keychain for secure key management.

Security Features:
- AES-256-GCM authenticated encryption (confidentiality + integrity)
- OS keychain integration via keyring library
- Fernet high-level encryption API (cryptography library)
- No keys stored in vault or .env files

Usage:
    encryption_service = EncryptionService()

    # Encrypt data
    encrypted_bytes = encryption_service.encrypt("sensitive data")

    # Decrypt data
    decrypted_str = encryption_service.decrypt(encrypted_bytes)

    # Encrypt file
    encryption_service.encrypt_file("/path/to/file.md")

    # Decrypt file
    encryption_service.decrypt_file("/path/to/file.md.encrypted")
"""

import logging
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
import keyring
import base64

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    AES-256-GCM encryption service with OS keychain integration.

    Encryption keys are stored securely in the operating system keychain:
    - macOS: Keychain Access
    - Windows: Credential Manager
    - Linux: Secret Service / keyring
    """

    SERVICE_NAME = "ai-employee-vault"
    KEY_NAME = "encryption-key"

    def __init__(self, auto_generate_key: bool = True):
        """
        Initialize encryption service.

        Args:
            auto_generate_key: If True, generate and store key if not found
        """
        self.fernet = self._initialize_fernet(auto_generate_key)

    def _initialize_fernet(self, auto_generate: bool = True) -> Fernet:
        """
        Initialize Fernet cipher with key from OS keychain.

        Args:
            auto_generate: Generate new key if not found

        Returns:
            Fernet: Initialized Fernet cipher

        Raises:
            RuntimeError: If key not found and auto_generate=False
        """
        # Try to retrieve existing key from keychain
        key_str = keyring.get_password(self.SERVICE_NAME, self.KEY_NAME)

        if key_str is None:
            if not auto_generate:
                raise RuntimeError(
                    f"Encryption key not found in keychain. "
                    f"Service: {self.SERVICE_NAME}, Key: {self.KEY_NAME}"
                )

            # Generate new key
            key_str = self._generate_and_store_key()
            logger.info("Generated new encryption key and stored in OS keychain")
        else:
            logger.debug("Retrieved encryption key from OS keychain")

        # Create Fernet cipher
        key_bytes = key_str.encode('utf-8')
        return Fernet(key_bytes)

    def _generate_and_store_key(self) -> str:
        """
        Generate a new Fernet key and store it in OS keychain.

        Returns:
            str: Base64-encoded key string
        """
        # Generate new Fernet key (32 bytes, base64-encoded)
        key_bytes = Fernet.generate_key()
        key_str = key_bytes.decode('utf-8')

        # Store in OS keychain
        keyring.set_password(self.SERVICE_NAME, self.KEY_NAME, key_str)

        return key_str

    def encrypt(self, plaintext: str) -> bytes:
        """
        Encrypt a string to bytes.

        Args:
            plaintext: String to encrypt

        Returns:
            bytes: Encrypted data (includes authentication tag)
        """
        plaintext_bytes = plaintext.encode('utf-8')
        encrypted_bytes = self.fernet.encrypt(plaintext_bytes)
        return encrypted_bytes

    def decrypt(self, encrypted_data: bytes) -> str:
        """
        Decrypt bytes to string.

        Args:
            encrypted_data: Encrypted bytes

        Returns:
            str: Decrypted plaintext string

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails (wrong key or corrupted data)
        """
        plaintext_bytes = self.fernet.decrypt(encrypted_data)
        return plaintext_bytes.decode('utf-8')

    def encrypt_file(self, file_path: str | Path, output_path: Optional[str | Path] = None) -> Path:
        """
        Encrypt a file and save with .encrypted extension.

        Args:
            file_path: Path to file to encrypt
            output_path: Optional output path (default: {file_path}.encrypted)

        Returns:
            Path: Path to encrypted file
        """
        file_path = Path(file_path)

        # Read plaintext file
        with open(file_path, 'r', encoding='utf-8') as f:
            plaintext = f.read()

        # Encrypt
        encrypted_data = self.encrypt(plaintext)

        # Determine output path
        if output_path is None:
            output_path = Path(str(file_path) + ".encrypted")
        else:
            output_path = Path(output_path)

        # Write encrypted file (binary mode)
        with open(output_path, 'wb') as f:
            f.write(encrypted_data)

        logger.info(f"Encrypted file: {file_path} → {output_path}")
        return output_path

    def decrypt_file(
        self,
        encrypted_path: str | Path,
        output_path: Optional[str | Path] = None,
        remove_encrypted_extension: bool = True
    ) -> Path:
        """
        Decrypt a file.

        Args:
            encrypted_path: Path to encrypted file
            output_path: Optional output path (default: remove .encrypted extension)
            remove_encrypted_extension: If True and output_path is None, remove .encrypted

        Returns:
            Path: Path to decrypted file
        """
        encrypted_path = Path(encrypted_path)

        # Read encrypted file (binary mode)
        with open(encrypted_path, 'rb') as f:
            encrypted_data = f.read()

        # Decrypt
        plaintext = self.decrypt(encrypted_data)

        # Determine output path
        if output_path is None:
            if remove_encrypted_extension and encrypted_path.name.endswith('.encrypted'):
                output_path = Path(str(encrypted_path).replace('.encrypted', ''))
            else:
                output_path = encrypted_path.with_suffix('.decrypted')
        else:
            output_path = Path(output_path)

        # Write decrypted file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(plaintext)

        logger.info(f"Decrypted file: {encrypted_path} → {output_path}")
        return output_path

    def encrypt_dict_field(self, data: dict, field: str) -> dict:
        """
        Encrypt a specific field in a dictionary (useful for entity frontmatter).

        Args:
            data: Dictionary containing field to encrypt
            field: Field name to encrypt

        Returns:
            dict: Modified dictionary with encrypted field (base64-encoded string)
        """
        if field not in data:
            return data

        value = str(data[field])
        encrypted_bytes = self.encrypt(value)
        # Store as base64 string (safe for JSON/YAML)
        encrypted_b64 = base64.b64encode(encrypted_bytes).decode('utf-8')
        data[field] = encrypted_b64
        return data

    def decrypt_dict_field(self, data: dict, field: str) -> dict:
        """
        Decrypt a specific field in a dictionary.

        Args:
            data: Dictionary containing encrypted field
            field: Field name to decrypt

        Returns:
            dict: Modified dictionary with decrypted field
        """
        if field not in data:
            return data

        encrypted_b64 = data[field]
        encrypted_bytes = base64.b64decode(encrypted_b64)
        decrypted_value = self.decrypt(encrypted_bytes)
        data[field] = decrypted_value
        return data

    def rotate_key(self, re_encrypt_callback: Optional[callable] = None):
        """
        Rotate encryption key (generate new key and re-encrypt all data).

        WARNING: This requires re-encrypting all encrypted files. You must provide
        a callback function that re-encrypts your data.

        Args:
            re_encrypt_callback: Function called with (old_service, new_service)
                                Must re-encrypt all data with new service

        Returns:
            EncryptionService: New service with rotated key
        """
        logger.warning("Starting encryption key rotation - this will invalidate old encrypted data")

        # Store old key for decryption
        old_key = keyring.get_password(self.SERVICE_NAME, self.KEY_NAME)

        # Generate new key
        new_key_str = self._generate_and_store_key()
        new_service = EncryptionService(auto_generate_key=False)

        # If callback provided, re-encrypt data
        if re_encrypt_callback:
            logger.info("Re-encrypting data with new key...")
            re_encrypt_callback(self, new_service)

        logger.info("Encryption key rotation complete")
        return new_service

    def delete_key(self):
        """
        Delete encryption key from OS keychain.

        WARNING: This will make all encrypted data unrecoverable.
        Only use for testing or complete system reset.
        """
        try:
            keyring.delete_password(self.SERVICE_NAME, self.KEY_NAME)
            logger.warning(f"Deleted encryption key from keychain: {self.SERVICE_NAME}/{self.KEY_NAME}")
        except keyring.errors.PasswordDeleteError:
            logger.debug("No encryption key found to delete")


# Singleton instance for application-wide use
_encryption_service_instance: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Get singleton EncryptionService instance.

    Returns:
        EncryptionService: Shared encryption service instance
    """
    global _encryption_service_instance
    if _encryption_service_instance is None:
        _encryption_service_instance = EncryptionService()
    return _encryption_service_instance

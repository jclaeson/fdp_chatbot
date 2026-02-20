"""Azure-specific configuration"""
import os
from pathlib import Path
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

class AzureConfig:
    """Azure environment configuration"""

    def __init__(self):
        # Azure Key Vault
        self.key_vault_name = os.getenv("KEY_VAULT_NAME", "")
        self.use_key_vault = bool(self.key_vault_name)

        # Storage
        self.storage_connection_string = os.getenv("STORAGE_CONNECTION_STRING", "")

        # Paths (Azure App Service specific)
        self.home_dir = Path("/home/site")
        self.chroma_persist_dir = self.home_dir / "chromadb"
        self.app_data_dir = self.home_dir / "appdata"

        # Ensure directories exist
        self.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
        self.app_data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Key Vault client if configured
        self.kv_client = None
        if self.use_key_vault:
            try:
                credential = DefaultAzureCredential()
                vault_url = f"https://{self.key_vault_name}.vault.azure.net"
                self.kv_client = SecretClient(vault_url=vault_url, credential=credential)
            except Exception as e:
                print(f"Warning: Could not initialize Key Vault client: {e}")

    def get_secret(self, secret_name: str, default: str = "") -> str:
        """Get secret from Key Vault or environment variable"""
        # Try Key Vault first
        if self.kv_client:
            try:
                secret = self.kv_client.get_secret(secret_name)
                return secret.value
            except Exception as e:
                print(f"Warning: Could not get secret {secret_name} from Key Vault: {e}")

        # Fall back to environment variable
        env_var = secret_name.replace("-", "_").upper()
        return os.getenv(env_var, default)

    def get_anthropic_api_key(self) -> str:
        """Get Anthropic API key"""
        return self.get_secret("ANTHROPIC-API-KEY", os.getenv("ANTHROPIC_API_KEY", ""))

    def get_storage_connection_string(self) -> str:
        """Get storage connection string"""
        return self.get_secret("STORAGE-CONNECTION-STRING", self.storage_connection_string)

# Global instance
azure_config = AzureConfig()

import json
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


@dataclass
class Message:
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        return cls(**data)


@dataclass
class ConversationThread:
    thread_id: str
    created_at: str
    last_updated: str
    messages: List[Message]
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "messages": [msg.to_dict() for msg in self.messages],
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationThread':
        messages = [Message.from_dict(msg_data) for msg_data in data.get("messages", [])]
        return cls(
            thread_id=data["thread_id"],
            created_at=data["created_at"],
            last_updated=data["last_updated"],
            messages=messages,
            metadata=data.get("metadata")
        )


class MemoryManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.memory_dir = Path(config.get("memory_dir", "data/memory"))
        self.max_session_messages = config.get("max_session_messages", 50)
        self.max_context_length = config.get("max_context_length", 4000)
        self.enable_persistence = config.get("enable_persistent_memory", True)
        self.retention_days = config.get("memory_retention_days", 30)
        self.enable_encryption = config.get("use_encrypted_storage", True)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Session memory (in-memory)
        self.current_thread: Optional[ConversationThread] = None
        self.session_messages: List[Message] = []
        
        # Encryption setup
        self._fernet = None
        if self.enable_encryption and self.enable_persistence:
            self._setup_encryption()
        
        # Initialize storage
        self._init_storage()
    
    def _setup_encryption(self):
        """Setup encryption for persistent storage."""
        try:
            key_file = self.memory_dir / ".memory_key"
            
            if key_file.exists():
                # Load existing key
                with open(key_file, 'rb') as f:
                    key = f.read()
            else:
                # Generate new key
                # Use a simple password-based key derivation for now
                password = "PersonaOS_Memory_Key".encode()  # In production, this should be user-configurable
                salt = os.urandom(16)
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(password))
                
                # Save key securely
                self.memory_dir.mkdir(parents=True, exist_ok=True)
                with open(key_file, 'wb') as f:
                    f.write(key)
                
                # Secure key file permissions (Unix-like systems)
                try:
                    os.chmod(key_file, 0o600)
                except (AttributeError, OSError):
                    pass  # Windows or permission error
            
            self._fernet = Fernet(key)
        
        except Exception as e:
            print(f"Warning: Failed to setup encryption: {e}. Falling back to unencrypted storage.")
            self.enable_encryption = False
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt data if encryption is enabled."""
        if self.enable_encryption and self._fernet:
            try:
                encrypted = self._fernet.encrypt(data.encode())
                return base64.urlsafe_b64encode(encrypted).decode()
            except Exception:
                return data  # Fallback to unencrypted
        return data
    
    def _decrypt_data(self, data: str) -> str:
        """Decrypt data if encryption is enabled."""
        if self.enable_encryption and self._fernet:
            try:
                encrypted_data = base64.urlsafe_b64decode(data.encode())
                decrypted = self._fernet.decrypt(encrypted_data)
                return decrypted.decode()
            except Exception:
                return data  # Fallback assuming unencrypted
        return data
    
    def _init_storage(self):
        if self.enable_persistence:
            self.memory_dir.mkdir(parents=True, exist_ok=True)
            
            # Use encrypted file extensions if encryption is enabled
            file_ext = ".enc" if self.enable_encryption else ".json"
            self.threads_file = self.memory_dir / f"conversation_threads{file_ext}"
            self.index_file = self.memory_dir / f"memory_index{file_ext}"
    
    def start_new_session(self) -> str:
        with self._lock:
            thread_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            timestamp = datetime.now().isoformat()
            
            self.current_thread = ConversationThread(
                thread_id=thread_id,
                created_at=timestamp,
                last_updated=timestamp,
                messages=[],
                metadata={"session_type": "interactive"}
            )
            
            self.session_messages = []
            return thread_id
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        with self._lock:
            if not self.current_thread:
                self.start_new_session()
            
            message = Message(
                role=role,
                content=content,
                timestamp=datetime.now().isoformat(),
                metadata=metadata
            )
            
            # Add to session memory
            self.session_messages.append(message)
            self.current_thread.messages.append(message)
            self.current_thread.last_updated = message.timestamp
            
            # Trim session memory if too long
            if len(self.session_messages) > self.max_session_messages:
                self.session_messages = self.session_messages[-self.max_session_messages:]
            
            # Save to persistent storage if enabled
            if self.enable_persistence:
                self._save_thread_to_storage()
    
    def get_context_for_llm(self, max_tokens: Optional[int] = None) -> List[Dict[str, str]]:
        with self._lock:
            if not self.session_messages:
                return []
            
            # Convert messages to LLM format
            context = []
            for message in self.session_messages:
                if message.role in ['user', 'assistant']:
                    context.append({
                        "role": message.role,
                        "content": message.content
                    })
            
            # Trim context if token limit specified
            if max_tokens and max_tokens < self.max_context_length:
                # Simple character-based approximation (4 chars H 1 token)
                char_limit = max_tokens * 4
                current_chars = 0
                trimmed_context = []
                
                for msg in reversed(context):
                    msg_chars = len(msg["content"])
                    if current_chars + msg_chars <= char_limit:
                        trimmed_context.insert(0, msg)
                        current_chars += msg_chars
                    else:
                        break
                
                context = trimmed_context
            
            return context
    
    def search_conversations(self, query: str, limit: int = 10) -> List[ConversationThread]:
        if not self.enable_persistence or not self.threads_file.exists():
            return []
        
        with self._lock:
            try:
                with open(self.threads_file, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # Decrypt if needed
                decrypted_content = self._decrypt_data(file_content)
                threads_data = json.loads(decrypted_content)
                
                matching_threads = []
                query_lower = query.lower()
                
                for thread_data in threads_data:
                    thread = ConversationThread.from_dict(thread_data)
                    
                    # Search in message content
                    for message in thread.messages:
                        if query_lower in message.content.lower():
                            matching_threads.append(thread)
                            break
                
                return matching_threads[:limit]
            
            except (FileNotFoundError, json.JSONDecodeError):
                return []
    
    def get_conversation_summary(self) -> Optional[str]:
        if not self.session_messages:
            return None
        
        # Simple summary: return first user message and last assistant message
        first_user_msg = None
        last_assistant_msg = None
        
        for msg in self.session_messages:
            if msg.role == 'user' and not first_user_msg:
                first_user_msg = msg.content
            elif msg.role == 'assistant':
                last_assistant_msg = msg.content
        
        if first_user_msg and last_assistant_msg:
            return f"Started with: {first_user_msg[:100]}... | Last response: {last_assistant_msg[:100]}..."
        elif first_user_msg:
            return f"Topic: {first_user_msg[:150]}..."
        
        return None
    
    def clear_session(self):
        with self._lock:
            if self.current_thread and self.enable_persistence:
                self._save_thread_to_storage()
            
            self.session_messages = []
            self.current_thread = None
    
    def _save_thread_to_storage(self):
        if not self.current_thread or not self.enable_persistence:
            return
        
        try:
            threads_data = []
            if self.threads_file.exists():
                with open(self.threads_file, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # Decrypt if needed
                decrypted_content = self._decrypt_data(file_content)
                threads_data = json.loads(decrypted_content)
            
            # Update or add current thread
            thread_updated = False
            for i, thread_data in enumerate(threads_data):
                if thread_data["thread_id"] == self.current_thread.thread_id:
                    threads_data[i] = self.current_thread.to_dict()
                    thread_updated = True
                    break
            
            if not thread_updated:
                threads_data.append(self.current_thread.to_dict())
            
            # Prepare data for saving
            json_data = json.dumps(threads_data, indent=2, ensure_ascii=False)
            
            # Encrypt if needed
            encrypted_data = self._encrypt_data(json_data)
            
            # Save to file
            with open(self.threads_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
        
        except Exception as e:
            # Log error but don't crash
            print(f"Warning: Failed to save conversation to persistent storage: {e}")
    
    def cleanup_old_conversations(self):
        if not self.enable_persistence or not self.threads_file.exists():
            return
        
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        with self._lock:
            try:
                with open(self.threads_file, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # Decrypt if needed
                decrypted_content = self._decrypt_data(file_content)
                threads_data = json.loads(decrypted_content)
                
                # Filter out old threads
                filtered_threads = []
                for thread_data in threads_data:
                    last_updated = datetime.fromisoformat(thread_data["last_updated"])
                    if last_updated >= cutoff_date:
                        filtered_threads.append(thread_data)
                
                # Prepare data for saving
                json_data = json.dumps(filtered_threads, indent=2, ensure_ascii=False)
                
                # Encrypt if needed
                encrypted_data = self._encrypt_data(json_data)
                
                # Save filtered data
                with open(self.threads_file, 'w', encoding='utf-8') as f:
                    f.write(encrypted_data)
            
            except Exception as e:
                print(f"Warning: Failed to cleanup old conversations: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        stats = {
            "session_messages": len(self.session_messages),
            "current_thread_id": self.current_thread.thread_id if self.current_thread else None,
            "persistent_storage_enabled": self.enable_persistence,
            "memory_dir": str(self.memory_dir),
            "max_session_messages": self.max_session_messages,
            "retention_days": self.retention_days
        }
        
        if self.enable_persistence and self.threads_file.exists():
            try:
                with open(self.threads_file, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # Decrypt if needed
                decrypted_content = self._decrypt_data(file_content)
                threads_data = json.loads(decrypted_content)
                stats["total_persisted_threads"] = len(threads_data)
            except Exception:
                stats["total_persisted_threads"] = "error_reading"
        
        return stats
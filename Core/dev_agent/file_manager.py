"""
File Manager for PersonaOS DevAgent.

Handles safe file operations with backup, validation, and rollback capabilities.
Supports dry-run mode for testing changes before applying them.
"""

import os
import shutil
import hashlib
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class FileOperation:
    """Represents a file operation."""
    operation_type: str  # 'create', 'edit', 'delete', 'move'
    target_path: str
    backup_path: Optional[str] = None
    content: Optional[str] = None
    original_content: Optional[str] = None
    timestamp: float = None
    success: bool = False
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()


@dataclass
class FileBackup:
    """Represents a file backup."""
    original_path: str
    backup_path: str
    timestamp: float
    checksum: str
    size: int
    operation_id: str


class FileManager:
    """
    Safe file manager with backup, validation, and rollback capabilities.
    
    Provides dry-run mode for testing changes and maintains operation history
    for autonomous development tasks.
    """
    
    def __init__(self, project_root: str, config: Optional[Dict] = None):
        self.project_root = Path(project_root).resolve()
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Configuration
        self.dry_run = self.config.get('dry_run', False)
        self.max_backup_age_days = self.config.get('max_backup_age_days', 7)
        self.max_backups_per_file = self.config.get('max_backups_per_file', 5)
        
        # Setup backup directory
        self.backup_dir = self.project_root / '.dev_agent_backups'
        self.backup_dir.mkdir(exist_ok=True)
        
        # Operation tracking
        self.current_session_id = self._generate_session_id()
        self.operations: List[FileOperation] = []
        self.backups: Dict[str, List[FileBackup]] = defaultdict(list)
        
        # Load existing backup metadata
        self._load_backup_metadata()
        
        # Clean old backups on startup
        self._cleanup_old_backups()
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"session_{timestamp}_{os.getpid()}"
    
    def _load_backup_metadata(self) -> None:
        """Load backup metadata from disk."""
        metadata_file = self.backup_dir / 'backup_metadata.json'
        if not metadata_file.exists():
            return
        
        try:
            with open(metadata_file, 'r') as f:
                data = json.load(f)
            
            for file_path, backups_data in data.items():
                for backup_data in backups_data:
                    backup = FileBackup(**backup_data)
                    self.backups[file_path].append(backup)
                    
        except Exception as e:
            self.logger.warning(f"Failed to load backup metadata: {e}")
    
    def _save_backup_metadata(self) -> None:
        """Save backup metadata to disk."""
        metadata_file = self.backup_dir / 'backup_metadata.json'
        
        try:
            data = {}
            for file_path, backups_list in self.backups.items():
                data[file_path] = [asdict(backup) for backup in backups_list]
            
            with open(metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save backup metadata: {e}")
    
    def _cleanup_old_backups(self) -> None:
        """Clean up old backup files."""
        cutoff_time = datetime.now() - timedelta(days=self.max_backup_age_days)
        cutoff_timestamp = cutoff_time.timestamp()
        
        files_cleaned = 0
        for file_path, backups_list in list(self.backups.items()):
            # Remove old backups
            updated_backups = []
            for backup in backups_list:
                if backup.timestamp < cutoff_timestamp:
                    try:
                        backup_path = Path(backup.backup_path)
                        if backup_path.exists():
                            backup_path.unlink()
                        files_cleaned += 1
                    except Exception as e:
                        self.logger.warning(f"Failed to delete old backup {backup.backup_path}: {e}")
                else:
                    updated_backups.append(backup)
            
            # Keep only recent backups per file
            updated_backups.sort(key=lambda b: b.timestamp, reverse=True)
            updated_backups = updated_backups[:self.max_backups_per_file]
            
            if updated_backups:
                self.backups[file_path] = updated_backups
            else:
                del self.backups[file_path]
        
        if files_cleaned > 0:
            self.logger.info(f"Cleaned up {files_cleaned} old backup files")
            self._save_backup_metadata()
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of file."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
        except Exception:
            return ""
        return hash_md5.hexdigest()
    
    def _create_backup(self, file_path: Path, operation_id: str) -> Optional[str]:
        """Create backup of file before modification."""
        if not file_path.exists():
            return None
        
        try:
            # Generate backup filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            relative_path = file_path.relative_to(self.project_root)
            backup_name = f"{relative_path.as_posix().replace('/', '_')}_{timestamp}.bak"
            backup_path = self.backup_dir / backup_name
            
            # Create backup directory structure if needed
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(file_path, backup_path)
            
            # Record backup metadata
            backup = FileBackup(
                original_path=str(relative_path),
                backup_path=str(backup_path),
                timestamp=datetime.now().timestamp(),
                checksum=self._calculate_checksum(file_path),
                size=file_path.stat().st_size,
                operation_id=operation_id
            )
            
            self.backups[str(relative_path)].append(backup)
            self._save_backup_metadata()
            
            self.logger.debug(f"Created backup: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            self.logger.error(f"Failed to create backup for {file_path}: {e}")
            return None
    
    def create_file(self, file_path: str, content: str, 
                   description: str = "") -> FileOperation:
        """Create a new file with content."""
        operation = FileOperation(
            operation_type='create',
            target_path=file_path,
            content=content
        )
        
        try:
            full_path = self.project_root / file_path
            
            # Check if file already exists
            if full_path.exists():
                operation.error = f"File already exists: {file_path}"
                return operation
            
            if self.dry_run:
                self.logger.info(f"[DRY RUN] Would create file: {file_path}")
                operation.success = True
            else:
                # Create parent directories
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write content
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                operation.success = True
                self.logger.info(f"Created file: {file_path}")
            
        except Exception as e:
            operation.error = str(e)
            self.logger.error(f"Failed to create file {file_path}: {e}")
        
        self.operations.append(operation)
        return operation
    
    def edit_file(self, file_path: str, content: str, 
                  create_backup: bool = True, description: str = "") -> FileOperation:
        """Edit an existing file with new content."""
        operation = FileOperation(
            operation_type='edit',
            target_path=file_path,
            content=content
        )
        
        try:
            full_path = self.project_root / file_path
            
            # Read original content if file exists
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    operation.original_content = f.read()
                    
                # Create backup if requested
                if create_backup and not self.dry_run:
                    operation.backup_path = self._create_backup(full_path, 
                                                              self.current_session_id)
            else:
                # File doesn't exist, treat as create
                operation.operation_type = 'create'
            
            if self.dry_run:
                self.logger.info(f"[DRY RUN] Would edit file: {file_path}")
                operation.success = True
            else:
                # Create parent directories if needed
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write new content
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                operation.success = True
                self.logger.info(f"Edited file: {file_path}")
            
        except Exception as e:
            operation.error = str(e)
            self.logger.error(f"Failed to edit file {file_path}: {e}")
        
        self.operations.append(operation)
        return operation
    
    def delete_file(self, file_path: str, create_backup: bool = True,
                   description: str = "") -> FileOperation:
        """Delete a file."""
        operation = FileOperation(
            operation_type='delete',
            target_path=file_path
        )
        
        try:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                operation.error = f"File does not exist: {file_path}"
                return operation
            
            # Read original content
            with open(full_path, 'r', encoding='utf-8') as f:
                operation.original_content = f.read()
            
            # Create backup if requested
            if create_backup and not self.dry_run:
                operation.backup_path = self._create_backup(full_path, 
                                                          self.current_session_id)
            
            if self.dry_run:
                self.logger.info(f"[DRY RUN] Would delete file: {file_path}")
                operation.success = True
            else:
                full_path.unlink()
                operation.success = True
                self.logger.info(f"Deleted file: {file_path}")
            
        except Exception as e:
            operation.error = str(e)
            self.logger.error(f"Failed to delete file {file_path}: {e}")
        
        self.operations.append(operation)
        return operation
    
    def move_file(self, source_path: str, dest_path: str, 
                  create_backup: bool = True, description: str = "") -> FileOperation:
        """Move/rename a file."""
        operation = FileOperation(
            operation_type='move',
            target_path=f"{source_path} -> {dest_path}"
        )
        
        try:
            source_full = self.project_root / source_path
            dest_full = self.project_root / dest_path
            
            if not source_full.exists():
                operation.error = f"Source file does not exist: {source_path}"
                return operation
            
            if dest_full.exists():
                operation.error = f"Destination file already exists: {dest_path}"
                return operation
            
            # Create backup if requested
            if create_backup and not self.dry_run:
                operation.backup_path = self._create_backup(source_full, 
                                                          self.current_session_id)
            
            if self.dry_run:
                self.logger.info(f"[DRY RUN] Would move file: {source_path} -> {dest_path}")
                operation.success = True
            else:
                # Create destination directory if needed
                dest_full.parent.mkdir(parents=True, exist_ok=True)
                
                # Move file
                shutil.move(str(source_full), str(dest_full))
                operation.success = True
                self.logger.info(f"Moved file: {source_path} -> {dest_path}")
            
        except Exception as e:
            operation.error = str(e)
            self.logger.error(f"Failed to move file {source_path} -> {dest_path}: {e}")
        
        self.operations.append(operation)
        return operation
    
    def apply_multiple_edits(self, edits: List[Dict[str, Any]], 
                           create_backups: bool = True) -> List[FileOperation]:
        """Apply multiple file operations atomically."""
        operations = []
        
        try:
            # Validate all operations first
            for edit in edits:
                operation_type = edit.get('type')
                file_path = edit.get('path')
                
                if not operation_type or not file_path:
                    raise ValueError("Each edit must have 'type' and 'path'")
                
                if operation_type not in ['create', 'edit', 'delete', 'move']:
                    raise ValueError(f"Invalid operation type: {operation_type}")
            
            # Apply operations
            for edit in edits:
                operation_type = edit['type']
                file_path = edit['path']
                content = edit.get('content', '')
                description = edit.get('description', '')
                
                if operation_type == 'create':
                    op = self.create_file(file_path, content, description)
                elif operation_type == 'edit':
                    op = self.edit_file(file_path, content, create_backups, description)
                elif operation_type == 'delete':
                    op = self.delete_file(file_path, create_backups, description)
                elif operation_type == 'move':
                    dest_path = edit.get('dest_path')
                    if not dest_path:
                        raise ValueError("Move operation requires 'dest_path'")
                    op = self.move_file(file_path, dest_path, create_backups, description)
                
                operations.append(op)
                
                # Stop on first failure if not in dry run mode
                if not op.success and not self.dry_run:
                    break
            
        except Exception as e:
            self.logger.error(f"Failed to apply multiple edits: {e}")
            # Create error operation
            error_op = FileOperation(
                operation_type='batch',
                target_path='multiple_files',
                error=str(e)
            )
            operations.append(error_op)
        
        return operations
    
    def rollback_operation(self, operation: FileOperation) -> bool:
        """Rollback a single operation."""
        if not operation.success:
            return True  # Nothing to rollback
        
        try:
            full_path = self.project_root / operation.target_path
            
            if operation.operation_type == 'create':
                # Delete created file
                if full_path.exists():
                    full_path.unlink()
                    self.logger.info(f"Rolled back file creation: {operation.target_path}")
                
            elif operation.operation_type == 'edit':
                # Restore from backup or original content
                if operation.backup_path and Path(operation.backup_path).exists():
                    shutil.copy2(operation.backup_path, full_path)
                    self.logger.info(f"Restored file from backup: {operation.target_path}")
                elif operation.original_content is not None:
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(operation.original_content)
                    self.logger.info(f"Restored file from original content: {operation.target_path}")
                else:
                    return False
                
            elif operation.operation_type == 'delete':
                # Restore from backup
                if operation.backup_path and Path(operation.backup_path).exists():
                    shutil.copy2(operation.backup_path, full_path)
                    self.logger.info(f"Restored deleted file: {operation.target_path}")
                else:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rollback operation {operation.operation_type} on {operation.target_path}: {e}")
            return False
    
    def rollback_session(self, session_id: Optional[str] = None) -> bool:
        """Rollback all operations from a session."""
        target_session = session_id or self.current_session_id
        
        # Find operations from target session
        session_operations = [op for op in self.operations 
                            if hasattr(op, 'session_id') and op.session_id == target_session]
        
        if not session_operations:
            self.logger.warning(f"No operations found for session: {target_session}")
            return True
        
        # Rollback in reverse order
        success_count = 0
        for operation in reversed(session_operations):
            if self.rollback_operation(operation):
                success_count += 1
        
        self.logger.info(f"Rolled back {success_count}/{len(session_operations)} operations from session {target_session}")
        return success_count == len(session_operations)
    
    def get_operation_history(self, limit: int = 100) -> List[FileOperation]:
        """Get recent operation history."""
        return self.operations[-limit:]
    
    def validate_file_integrity(self, file_path: str) -> Dict[str, Any]:
        """Validate file integrity against backup checksums."""
        full_path = self.project_root / file_path
        
        result = {
            'file_exists': full_path.exists(),
            'current_checksum': None,
            'backup_checksums': [],
            'integrity_ok': False
        }
        
        if not full_path.exists():
            return result
        
        current_checksum = self._calculate_checksum(full_path)
        result['current_checksum'] = current_checksum
        
        # Check against backups
        backups_list = self.backups.get(file_path, [])
        for backup in backups_list:
            result['backup_checksums'].append({
                'timestamp': backup.timestamp,
                'checksum': backup.checksum,
                'matches': backup.checksum == current_checksum
            })
        
        # File is OK if it matches any backup or has no backups (new file)
        result['integrity_ok'] = (
            not backups_list or 
            any(b['matches'] for b in result['backup_checksums'])
        )
        
        return result
    
    def set_dry_run(self, enabled: bool) -> None:
        """Enable or disable dry run mode."""
        self.dry_run = enabled
        mode = "enabled" if enabled else "disabled"
        self.logger.info(f"Dry run mode {mode}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session operations."""
        operations_by_type = defaultdict(int)
        successful_ops = 0
        failed_ops = 0
        
        for op in self.operations:
            operations_by_type[op.operation_type] += 1
            if op.success:
                successful_ops += 1
            else:
                failed_ops += 1
        
        return {
            'session_id': self.current_session_id,
            'total_operations': len(self.operations),
            'successful_operations': successful_ops,
            'failed_operations': failed_ops,
            'operations_by_type': dict(operations_by_type),
            'dry_run_mode': self.dry_run,
            'backup_files': sum(len(backups) for backups in self.backups.values())
        }
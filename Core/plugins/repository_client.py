"""
Plugin Repository Client for PersonaOS

This module provides client functionality for interacting with plugin
repositories, including plugin discovery, downloading, and metadata
management.
"""

import json
import logging
import hashlib
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

@dataclass
class RepositoryPluginInfo:
    """Information about a plugin from a repository."""
    name: str
    version: str
    description: str
    author: str
    download_url: str
    checksum: str
    size: int
    dependencies: List[Dict[str, Any]]
    permissions: List[Dict[str, Any]]
    tags: List[str]
    repository_name: str
    last_updated: str
    metadata: Dict[str, Any]

@dataclass
class DownloadResult:
    """Result of a plugin download operation."""
    success: bool
    plugin_path: Optional[Path] = None
    error: Optional[str] = None
    checksum_verified: bool = False
    size: int = 0
    download_time: float = 0.0

class RepositoryClient:
    """
    Client for interacting with PersonaOS plugin repositories.
    
    Provides functionality for:
    - Plugin discovery and search
    - Plugin metadata retrieval
    - Plugin downloading and verification
    - Repository health checking
    - Authentication handling
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize repository client.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger("repository_client")
        
        # Download configuration
        self.download_directory = Path(self.config.get("plugin_download_directory", "downloads/plugins"))
        self.verify_checksums = self.config.get("plugin_verify_checksums", True)
        self.max_download_size = self.config.get("plugin_max_download_size", 100 * 1024 * 1024)  # 100MB
        self.download_timeout = self.config.get("plugin_download_timeout", 300)  # 5 minutes
        
        # HTTP session configuration
        self.session = requests.Session()
        self._configure_session()
        
        # Download cache
        self.download_cache: Dict[str, Path] = {}
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "downloads_attempted": 0,
            "downloads_successful": 0,
            "downloads_failed": 0,
            "bytes_downloaded": 0,
            "checksum_verifications": 0,
            "checksum_failures": 0
        }
        
        # Ensure download directory exists
        self.download_directory.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("RepositoryClient initialized")
    
    def _configure_session(self):
        """Configure HTTP session with retry strategy."""
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def search_plugins(self, repository_url: str, query: str = "", 
                      tags: List[str] = None, auth_token: str = None,
                      limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        Search for plugins in a repository.
        
        Args:
            repository_url: Base URL of the repository
            query: Search query string
            tags: List of tags to filter by
            auth_token: Optional authentication token
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            Search results dictionary
        """
        self.stats["total_requests"] += 1
        
        try:
            search_url = urljoin(repository_url, "plugins/search")
            
            params = {
                "q": query,
                "limit": limit,
                "offset": offset
            }
            
            if tags:
                params["tags"] = ",".join(tags)
            
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            self.logger.info(f"Searching plugins: query='{query}', tags={tags}")
            
            response = self.session.get(
                search_url,
                params=params,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            
            search_results = response.json()
            plugins = []
            
            # Parse plugin information
            for plugin_data in search_results.get("plugins", []):
                try:
                    plugin_info = self._parse_plugin_info(plugin_data, repository_url)
                    plugins.append(plugin_info)
                except Exception as e:
                    self.logger.warning(f"Failed to parse plugin info: {e}")
            
            self.stats["successful_requests"] += 1
            
            return {
                "success": True,
                "plugins": plugins,
                "total_count": search_results.get("total", len(plugins)),
                "query": query,
                "tags": tags,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "has_more": search_results.get("has_more", False)
                }
            }
            
        except requests.RequestException as e:
            self.stats["failed_requests"] += 1
            self.logger.error(f"Repository search failed: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "plugins": [],
                "total_count": 0
            }
    
    def get_plugin_info(self, repository_url: str, plugin_name: str, 
                       version: str = "latest", auth_token: str = None) -> Dict[str, Any]:
        """
        Get detailed information about a specific plugin.
        
        Args:
            repository_url: Base URL of the repository
            plugin_name: Name of the plugin
            version: Plugin version (default: latest)
            auth_token: Optional authentication token
            
        Returns:
            Plugin information dictionary
        """
        self.stats["total_requests"] += 1
        
        try:
            if version == "latest":
                plugin_url = urljoin(repository_url, f"plugins/{plugin_name}")
            else:
                plugin_url = urljoin(repository_url, f"plugins/{plugin_name}/{version}")
            
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            self.logger.info(f"Fetching plugin info: {plugin_name} v{version}")
            
            response = self.session.get(
                plugin_url,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            
            plugin_data = response.json()
            plugin_info = self._parse_plugin_info(plugin_data, repository_url)
            
            self.stats["successful_requests"] += 1
            
            return {
                "success": True,
                "plugin": plugin_info
            }
            
        except requests.RequestException as e:
            self.stats["failed_requests"] += 1
            self.logger.error(f"Failed to get plugin info for {plugin_name}: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "plugin": None
            }
    
    def list_plugin_versions(self, repository_url: str, plugin_name: str,
                           auth_token: str = None) -> Dict[str, Any]:
        """
        List all available versions of a plugin.
        
        Args:
            repository_url: Base URL of the repository
            plugin_name: Name of the plugin
            auth_token: Optional authentication token
            
        Returns:
            Version list dictionary
        """
        self.stats["total_requests"] += 1
        
        try:
            versions_url = urljoin(repository_url, f"plugins/{plugin_name}/versions")
            
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            response = self.session.get(
                versions_url,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            
            versions_data = response.json()
            versions = versions_data.get("versions", [])
            
            self.stats["successful_requests"] += 1
            
            return {
                "success": True,
                "plugin_name": plugin_name,
                "versions": versions,
                "latest_version": versions_data.get("latest", "")
            }
            
        except requests.RequestException as e:
            self.stats["failed_requests"] += 1
            self.logger.error(f"Failed to list versions for {plugin_name}: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "versions": [],
                "latest_version": ""
            }
    
    def download_plugin(self, plugin_info: RepositoryPluginInfo, 
                       target_directory: Path = None,
                       verify_checksum: bool = None) -> DownloadResult:
        """
        Download a plugin from repository.
        
        Args:
            plugin_info: Plugin information with download URL
            target_directory: Target download directory
            verify_checksum: Whether to verify checksum (default: use config)
            
        Returns:
            Download result
        """
        import time
        
        self.stats["downloads_attempted"] += 1
        start_time = time.time()
        
        target_dir = target_directory or self.download_directory
        verify_checksum = verify_checksum if verify_checksum is not None else self.verify_checksums
        
        try:
            # Check if already downloaded and cached
            cache_key = f"{plugin_info.name}:{plugin_info.version}:{plugin_info.checksum}"
            if cache_key in self.download_cache:
                cached_path = self.download_cache[cache_key]
                if cached_path.exists():
                    self.logger.info(f"Using cached download: {plugin_info.name} v{plugin_info.version}")
                    return DownloadResult(
                        success=True,
                        plugin_path=cached_path,
                        checksum_verified=True,
                        size=cached_path.stat().st_size,
                        download_time=0.0
                    )
            
            self.logger.info(f"Downloading plugin: {plugin_info.name} v{plugin_info.version}")
            
            # Determine file extension and target path
            parsed_url = urlparse(plugin_info.download_url)
            file_extension = Path(parsed_url.path).suffix or ".zip"
            
            target_path = target_dir / f"{plugin_info.name}-{plugin_info.version}{file_extension}"
            
            # Check download size limit
            if plugin_info.size > self.max_download_size:
                return DownloadResult(
                    success=False,
                    error=f"Plugin size ({plugin_info.size} bytes) exceeds limit ({self.max_download_size} bytes)"
                )
            
            # Download with progress tracking
            response = self.session.get(
                plugin_info.download_url,
                stream=True,
                timeout=self.download_timeout
            )
            
            response.raise_for_status()
            
            # Verify content length
            content_length = response.headers.get('content-length')
            if content_length:
                expected_size = int(content_length)
                if expected_size > self.max_download_size:
                    return DownloadResult(
                        success=False,
                        error=f"Actual download size ({expected_size} bytes) exceeds limit"
                    )
            
            # Download to temporary file first
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                downloaded_size = 0
                hash_md5 = hashlib.md5() if verify_checksum else None
                
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if hash_md5:
                            hash_md5.update(chunk)
                        
                        # Check size limit during download
                        if downloaded_size > self.max_download_size:
                            temp_file.close()
                            Path(temp_file.name).unlink()
                            return DownloadResult(
                                success=False,
                                error=f"Download exceeded size limit during transfer"
                            )
                
                temp_path = Path(temp_file.name)
            
            # Verify checksum if required
            checksum_verified = False
            if verify_checksum and plugin_info.checksum:
                calculated_checksum = hash_md5.hexdigest()
                
                if calculated_checksum.lower() == plugin_info.checksum.lower():
                    checksum_verified = True
                    self.stats["checksum_verifications"] += 1
                else:
                    self.stats["checksum_failures"] += 1
                    temp_path.unlink()
                    return DownloadResult(
                        success=False,
                        error=f"Checksum verification failed: expected {plugin_info.checksum}, got {calculated_checksum}"
                    )
            
            # Move to final location
            target_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.rename(target_path)
            
            # Update statistics
            self.stats["downloads_successful"] += 1
            self.stats["bytes_downloaded"] += downloaded_size
            download_time = time.time() - start_time
            
            # Cache the download
            self.download_cache[cache_key] = target_path
            
            self.logger.info(f"Successfully downloaded {plugin_info.name} v{plugin_info.version} ({downloaded_size} bytes)")
            
            return DownloadResult(
                success=True,
                plugin_path=target_path,
                checksum_verified=checksum_verified,
                size=downloaded_size,
                download_time=download_time
            )
            
        except Exception as e:
            self.stats["downloads_failed"] += 1
            self.logger.error(f"Download failed for {plugin_info.name} v{plugin_info.version}: {e}")
            
            return DownloadResult(
                success=False,
                error=str(e),
                download_time=time.time() - start_time
            )
    
    def verify_plugin_file(self, plugin_path: Path, expected_checksum: str) -> bool:
        """
        Verify a downloaded plugin file against its checksum.
        
        Args:
            plugin_path: Path to plugin file
            expected_checksum: Expected MD5 checksum
            
        Returns:
            True if checksum matches, False otherwise
        """
        try:
            if not plugin_path.exists():
                return False
            
            hash_md5 = hashlib.md5()
            
            with open(plugin_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_md5.update(chunk)
            
            calculated_checksum = hash_md5.hexdigest()
            
            if calculated_checksum.lower() == expected_checksum.lower():
                self.stats["checksum_verifications"] += 1
                return True
            else:
                self.stats["checksum_failures"] += 1
                self.logger.warning(f"Checksum mismatch for {plugin_path}: expected {expected_checksum}, got {calculated_checksum}")
                return False
                
        except Exception as e:
            self.logger.error(f"Checksum verification failed for {plugin_path}: {e}")
            return False
    
    def extract_plugin(self, plugin_path: Path, extract_to: Path) -> Dict[str, Any]:
        """
        Extract a downloaded plugin archive.
        
        Args:
            plugin_path: Path to plugin archive
            extract_to: Directory to extract to
            
        Returns:
            Extraction result dictionary
        """
        try:
            self.logger.info(f"Extracting plugin: {plugin_path}")
            
            extract_to.mkdir(parents=True, exist_ok=True)
            
            if plugin_path.suffix.lower() == '.zip':
                with zipfile.ZipFile(plugin_path, 'r') as zip_ref:
                    # Security check: validate file paths
                    for member in zip_ref.namelist():
                        if member.startswith('/') or '..' in member:
                            raise ValueError(f"Unsafe path in archive: {member}")
                    
                    zip_ref.extractall(extract_to)
                    extracted_files = zip_ref.namelist()
            else:
                return {
                    "success": False,
                    "error": f"Unsupported archive format: {plugin_path.suffix}"
                }
            
            self.logger.info(f"Successfully extracted {len(extracted_files)} files to {extract_to}")
            
            return {
                "success": True,
                "extract_path": extract_to,
                "extracted_files": extracted_files,
                "file_count": len(extracted_files)
            }
            
        except Exception as e:
            self.logger.error(f"Plugin extraction failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_repository_health(self, repository_url: str, 
                              auth_token: str = None) -> Dict[str, Any]:
        """
        Check the health status of a repository.
        
        Args:
            repository_url: Base URL of the repository
            auth_token: Optional authentication token
            
        Returns:
            Health check result dictionary
        """
        self.stats["total_requests"] += 1
        
        try:
            health_url = urljoin(repository_url, "health")
            
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            response = self.session.get(
                health_url,
                headers=headers,
                timeout=10
            )
            
            response.raise_for_status()
            
            health_data = response.json()
            
            self.stats["successful_requests"] += 1
            
            return {
                "success": True,
                "status": health_data.get("status", "unknown"),
                "version": health_data.get("version", ""),
                "plugin_count": health_data.get("plugin_count", 0),
                "last_updated": health_data.get("last_updated", ""),
                "response_time": response.elapsed.total_seconds()
            }
            
        except requests.RequestException as e:
            self.stats["failed_requests"] += 1
            self.logger.error(f"Repository health check failed: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "status": "error"
            }
    
    def _parse_plugin_info(self, plugin_data: Dict[str, Any], 
                         repository_url: str) -> RepositoryPluginInfo:
        """Parse plugin data from repository response."""
        return RepositoryPluginInfo(
            name=plugin_data.get("name", ""),
            version=plugin_data.get("version", ""),
            description=plugin_data.get("description", ""),
            author=plugin_data.get("author", ""),
            download_url=plugin_data.get("download_url", ""),
            checksum=plugin_data.get("checksum", ""),
            size=plugin_data.get("size", 0),
            dependencies=plugin_data.get("dependencies", []),
            permissions=plugin_data.get("permissions", []),
            tags=plugin_data.get("tags", []),
            repository_name=urlparse(repository_url).netloc,
            last_updated=plugin_data.get("last_updated", ""),
            metadata=plugin_data.get("metadata", {})
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get repository client statistics."""
        return {
            **self.stats,
            "download_cache_size": len(self.download_cache),
            "download_directory": str(self.download_directory)
        }
    
    def clear_download_cache(self):
        """Clear the download cache."""
        self.download_cache.clear()
        self.logger.info("Download cache cleared")
    
    def cleanup_downloads(self, max_age_days: int = 30):
        """
        Clean up old downloaded files.
        
        Args:
            max_age_days: Maximum age of files to keep in days
        """
        try:
            import time
            
            cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
            cleaned_count = 0
            
            for file_path in self.download_directory.rglob("*"):
                if file_path.is_file():
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        cleaned_count += 1
            
            # Update cache to remove references to deleted files
            self.download_cache = {
                key: path for key, path in self.download_cache.items()
                if path.exists()
            }
            
            self.logger.info(f"Cleaned up {cleaned_count} old download files")
            
        except Exception as e:
            self.logger.error(f"Download cleanup failed: {e}")
    
    def shutdown(self):
        """Shutdown repository client."""
        self.logger.info("Shutting down repository client")
        
        # Close HTTP session
        self.session.close()
        
        # Clear cache
        self.download_cache.clear()
        
        self.logger.info("Repository client shutdown complete")
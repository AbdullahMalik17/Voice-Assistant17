"""
Google Drive API Service
Provides programmatic access to Google Drive for file operations.
"""

import io
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from .google_auth import get_google_auth

logger = logging.getLogger(__name__)


class DriveAPIService:
    """
    Google Drive API service for file operations.
    Provides methods to list, search, download, and upload files.
    """

    def __init__(self):
        """Initialize Drive API service."""
        self.service = None
        logger.info("DriveAPIService initialized")

    def _get_service(self):
        """Get or create Drive API service instance."""
        if self.service is None:
            try:
                from googleapiclient.discovery import build

                auth_service = get_google_auth()
                credentials = auth_service.get_credentials(auth_service.DRIVE_SCOPES)

                self.service = build('drive', 'v3', credentials=credentials)
                logger.info("Drive API service created")

            except ImportError:
                raise RuntimeError(
                    "Google API client not installed. "
                    "Install with: pip install google-api-python-client"
                )
            except Exception as e:
                logger.error(f"Failed to create Drive service: {e}")
                raise

        return self.service

    def list_files(
        self,
        max_results: int = 10,
        query: Optional[str] = None,
        order_by: str = 'modifiedTime desc'
    ) -> Dict[str, Any]:
        """
        List files in Google Drive.

        Args:
            max_results: Maximum number of files to return
            query: Drive search query (e.g., "mimeType='application/pdf'")
            order_by: Sort order (e.g., 'modifiedTime desc', 'name')

        Returns:
            Dict with file list
        """
        try:
            service = self._get_service()

            params = {
                'pageSize': max_results,
                'orderBy': order_by,
                'fields': 'files(id, name, mimeType, size, modifiedTime, webViewLink, owners)'
            }

            if query:
                params['q'] = query

            response = service.files().list(**params).execute()
            files = response.get('files', [])

            logger.info(f"Listed {len(files)} files")

            return {
                "success": True,
                "files": files,
                "count": len(files),
                "next_page_token": response.get('nextPageToken')
            }

        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return {
                "success": False,
                "error": str(e),
                "files": []
            }

    def search_files(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Search files by name or query.

        Args:
            query: Search query (filename or Drive query)
            max_results: Maximum results

        Returns:
            Dict with search results
        """
        # If simple filename, build query
        if not any(op in query for op in ['=', '>', '<', 'and', 'or']):
            drive_query = f"name contains '{query}'"
        else:
            drive_query = query

        return self.list_files(max_results=max_results, query=drive_query)

    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Get file metadata.

        Args:
            file_id: Drive file ID

        Returns:
            Dict with file metadata
        """
        try:
            service = self._get_service()

            file = service.files().get(
                fileId=file_id,
                fields='id, name, mimeType, size, modifiedTime, webViewLink, owners, description'
            ).execute()

            logger.info(f"Retrieved metadata for: {file.get('name')}")

            return {
                "success": True,
                "file": file
            }

        except Exception as e:
            logger.error(f"Failed to get file metadata: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def download_file(
        self,
        file_id: str,
        destination: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Download a file from Drive.

        Args:
            file_id: Drive file ID
            destination: Local path to save file (optional)

        Returns:
            Dict with download status and content
        """
        try:
            from googleapiclient.http import MediaIoBaseDownload
            import base64

            service = self._get_service()

            # Get file metadata
            file_metadata = service.files().get(fileId=file_id).execute()
            filename = file_metadata.get('name', 'download')

            # Download file
            request = service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.info(f"Download progress: {int(status.progress() * 100)}%")

            file_buffer.seek(0)
            file_content = file_buffer.read()

            # Save to file if destination provided
            if destination:
                dest_path = Path(destination)
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                with open(dest_path, 'wb') as f:
                    f.write(file_content)

                logger.info(f"File downloaded to: {destination}")

                return {
                    "success": True,
                    "message": f"File downloaded: {filename}",
                    "path": str(dest_path),
                    "size_bytes": len(file_content)
                }
            else:
                # Return as base64
                content_b64 = base64.b64encode(file_content).decode()

                logger.info(f"File downloaded (base64): {filename}")

                return {
                    "success": True,
                    "message": f"File downloaded: {filename}",
                    "filename": filename,
                    "content": content_b64,
                    "size_bytes": len(file_content)
                }

        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def upload_file(
        self,
        file_path: str,
        folder_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to Drive.

        Args:
            file_path: Local file path
            folder_id: Drive folder ID (optional)
            description: File description (optional)

        Returns:
            Dict with upload status
        """
        try:
            from googleapiclient.http import MediaFileUpload

            service = self._get_service()

            file_path_obj = Path(file_path)

            if not file_path_obj.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }

            # File metadata
            file_metadata = {
                'name': file_path_obj.name
            }

            if folder_id:
                file_metadata['parents'] = [folder_id]

            if description:
                file_metadata['description'] = description

            # Upload file
            media = MediaFileUpload(
                file_path,
                resumable=True
            )

            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()

            logger.info(f"File uploaded: {file.get('name')}")

            return {
                "success": True,
                "message": f"File uploaded: {file.get('name')}",
                "file_id": file.get('id'),
                "web_view_link": file.get('webViewLink')
            }

        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a folder in Drive.

        Args:
            folder_name: Name of the folder
            parent_id: Parent folder ID (optional)

        Returns:
            Dict with folder creation status
        """
        try:
            service = self._get_service()

            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }

            if parent_id:
                file_metadata['parents'] = [parent_id]

            folder = service.files().create(
                body=file_metadata,
                fields='id, name, webViewLink'
            ).execute()

            logger.info(f"Folder created: {folder.get('name')}")

            return {
                "success": True,
                "message": f"Folder created: {folder.get('name')}",
                "folder_id": folder.get('id'),
                "web_view_link": folder.get('webViewLink')
            }

        except Exception as e:
            logger.error(f"Failed to create folder: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def delete_file(self, file_id: str) -> Dict[str, Any]:
        """
        Delete a file from Drive.

        Args:
            file_id: Drive file ID

        Returns:
            Dict with deletion status
        """
        try:
            service = self._get_service()

            service.files().delete(fileId=file_id).execute()

            logger.info(f"File deleted: {file_id}")

            return {
                "success": True,
                "message": "File deleted successfully"
            }

        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
_drive_service: Optional[DriveAPIService] = None


def get_drive_service() -> DriveAPIService:
    """
    Get or create Drive API service instance.

    Returns:
        DriveAPIService instance
    """
    global _drive_service

    if _drive_service is None:
        _drive_service = DriveAPIService()

    return _drive_service

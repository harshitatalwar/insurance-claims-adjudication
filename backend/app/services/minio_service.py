"""
Production-grade MinIO storage service with interface abstraction
"""
from abc import ABC, abstractmethod
from typing import BinaryIO, Optional
from minio import Minio
from minio.error import S3Error
from datetime import timedelta
import logging
import os

from app.config import settings

logger = logging.getLogger(__name__)

class StorageInterface(ABC):
    """Abstract interface for storage operations"""
    
    @abstractmethod
    def upload_file(self, file_path: str, file_data: BinaryIO, content_type: str = None) -> str:
        """Upload file and return object name"""
        pass
    
    @abstractmethod
    def download_file(self, file_path: str) -> bytes:
        """Download file and return bytes"""
        pass
    
    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """Delete file and return success status"""
        pass
    
    @abstractmethod
    def generate_presigned_upload_url(self, object_name: str, expires: timedelta = None) -> str:
        """Generate presigned URL for upload"""
        pass
    
    @abstractmethod
    def generate_presigned_download_url(self, object_name: str, expires: timedelta = None) -> str:
        """Generate presigned URL for download"""
        pass

class MinIOStorageService(StorageInterface):
    """Production-grade MinIO implementation"""
    
    def __init__(self):
        logger.info(f"[MINIO] Initializing MinIO client")
        logger.info(f"[MINIO] Endpoint: {settings.MINIO_HOST}:{settings.MINIO_PORT}")
        logger.info(f"[MINIO] Bucket: {settings.MINIO_BUCKET_NAME}")
        
        try:
            # 1. Internal Client (Backend <-> MinIO)
            # This handles the internal docker connection (always http internally)
            self.client = Minio(
                endpoint=f"{settings.MINIO_HOST}:{settings.MINIO_PORT}",
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
                region="us-east-1"
            )

            # 2. Public Client (Browser <-> MinIO)
            # Get the URL from env. Default to localhost if missing.
            public_url = os.getenv("MINIO_PUBLIC_URL", f"localhost:{settings.MINIO_PORT}")
            
            # Auto-detect SSL: If the URL starts with https, use secure=True
            use_ssl = public_url.startswith("https://")
            
            # Clean the endpoint string (MinIO hates 'http://' prefixes)
            public_endpoint = public_url.replace("http://", "").replace("https://", "")

            logger.info(f"[MINIO] Public Endpoint: {public_endpoint} | SSL: {use_ssl}")

            self.public_client = Minio(
                endpoint=public_endpoint,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=use_ssl,  # <--- DYNAMICALLY SET TO TRUE/FALSE
                region="us-east-1"
            )

            self.bucket_name = settings.MINIO_BUCKET_NAME
            logger.info(f"[MINIO] Client created successfully")
            self._ensure_bucket_exists()
            
        except Exception as e:
            logger.error(f"[MINIO] Failed to initialize: {str(e)}")
            raise
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            logger.info(f"[MINIO] Checking bucket: {self.bucket_name}")
            bucket_exists = self.client.bucket_exists(self.bucket_name)
            logger.info(f"[MINIO] Bucket exists: {bucket_exists}")
            
            if not bucket_exists:
                logger.info(f"[MINIO] Creating bucket: {self.bucket_name}")
                self.client.make_bucket(self.bucket_name)
                logger.info(f"[MINIO] ✅ Bucket created: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"[MINIO] S3Error: {e}")
            raise
        except Exception as e:
            logger.error(f"[MINIO] Unexpected error: {str(e)}")
            raise
    
    def upload_file(self, file_path: str, file_data: BinaryIO, content_type: str = None) -> str:
        """Upload file to MinIO"""
        try:
            logger.info(f"[MINIO] Uploading: {file_path}")
            logger.info(f"[MINIO] Content-Type: {content_type}")
            
            # Get file size
            file_data.seek(0, 2)
            file_size = file_data.tell()
            file_data.seek(0)
            logger.info(f"[MINIO] Size: {file_size} bytes")
            
            # Upload to MinIO
            result = self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=file_path,
                data=file_data,
                length=file_size,
                content_type=content_type
            )
            
            logger.info(f"[MINIO] ✅ Uploaded: {file_path}")
            return file_path
            
        except S3Error as e:
            logger.error(f"[MINIO] S3Error uploading {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"[MINIO] Error uploading {file_path}: {str(e)}")
            raise
    
    def download_file(self, file_path: str) -> bytes:
        """Download file from MinIO"""
        try:
            logger.info(f"[MINIO] Downloading: {file_path}")
            response = self.client.get_object(self.bucket_name, file_path)
            data = response.read()
            response.close()
            response.release_conn()
            logger.info(f"[MINIO] ✅ Downloaded: {file_path}")
            return data
        except S3Error as e:
            logger.error(f"[MINIO] S3Error downloading {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"[MINIO] Error downloading {file_path}: {str(e)}")
            raise
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from MinIO"""
        try:
            logger.info(f"[MINIO] Deleting: {file_path}")
            self.client.remove_object(self.bucket_name, file_path)
            logger.info(f"[MINIO] ✅ Deleted: {file_path}")
            return True
        except S3Error as e:
            logger.error(f"[MINIO] S3Error deleting {file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"[MINIO] Error deleting {file_path}: {str(e)}")
            return False
    
    def generate_presigned_upload_url(
        self, 
        object_name: str, 
        expires: timedelta = None
    ) -> str:
        """Generate presigned URL for upload"""
        try:
            if expires is None:
                expires = timedelta(minutes=15)
            
            # Use public_client to generate URL with localhost signature
            url = self.public_client.presigned_put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=expires
            )
            logger.info(f"[MINIO] ✅ Generated upload URL for: {object_name}")
            return url
        except S3Error as e:
            logger.error(f"[MINIO] S3Error generating upload URL: {e}")
            raise
        except Exception as e:
            logger.error(f"[MINIO] Error generating upload URL: {str(e)}")
            raise
    
    def generate_presigned_download_url(
        self,
        object_name: str,
        expires: timedelta = None
    ) -> str:
        """Generate presigned URL for download"""
        try:
            if expires is None:
                expires = timedelta(hours=1)
            
            # Use public_client to generate URL with localhost signature
            url = self.public_client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=expires
            )
            logger.info(f"[MINIO] ✅ Generated download URL for: {object_name}")
            return url
        except S3Error as e:
            logger.error(f"[MINIO] S3Error generating download URL: {e}")
            raise
        except Exception as e:
            logger.error(f"[MINIO] Error generating download URL: {str(e)}")
            raise

# Global storage service instance (singleton pattern)
_storage_service: Optional[MinIOStorageService] = None

def get_storage_service() -> StorageInterface:
    """Get global storage service instance (lazy initialization)"""
    global _storage_service
    if _storage_service is None:
        _storage_service = MinIOStorageService()
    return _storage_service

# Convenience alias - DO NOT instantiate here, use get_storage_service() instead
# This allows .env to be loaded before MinIO client is created
MinIOService = get_storage_service


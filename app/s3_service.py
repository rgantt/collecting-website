"""
S3 Photo Service
Handles AWS S3 integration for photo storage including pre-signed URLs and direct upload policies.
"""
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.client import Config
from flask import current_app
from typing import Dict, Optional, List
import json
from datetime import datetime, timedelta
import logging
import urllib.parse

logger = logging.getLogger(__name__)


class S3PhotoService:
    """Service class for S3 photo operations"""
    
    def __init__(self):
        self.bucket_name = current_app.config['S3_PHOTOS_BUCKET']
        self.region = current_app.config['S3_REGION']
        self.access_key = current_app.config['S3_ACCESS_KEY']
        self.secret_key = current_app.config['S3_SECRET_KEY']
        
        # Initialize S3 client with explicit credentials
        if not self.access_key or not self.secret_key:
            raise ValueError("S3 credentials not configured. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=Config(signature_version='s3v4')
        )
    
    def generate_presigned_post(self, s3_key: str, content_type: str, 
                              max_size: Optional[int] = None) -> Dict:
        """
        Generate pre-signed POST policy for direct client upload to S3
        
        Args:
            s3_key: S3 object key for the upload
            content_type: MIME type of the file
            max_size: Maximum file size in bytes (defaults to config)
        
        Returns:
            Dict containing upload URL, fields, and policy information
        """
        if max_size is None:
            max_size = current_app.config['MAX_PHOTO_SIZE']
        
        expiry_minutes = current_app.config['PHOTO_UPLOAD_EXPIRY_MINUTES']
        
        # Conditions for the upload
        conditions = [
            {"bucket": self.bucket_name},
            {"key": s3_key},
            {"Content-Type": content_type},
            ["content-length-range", 1, max_size],  # File size constraints
        ]
        
        # Fields that must be included in the form data
        fields = {
            "Content-Type": content_type,
            "key": s3_key,
        }
        
        try:
            response = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=s3_key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expiry_minutes * 60  # Convert to seconds
            )
            
            # Ensure we use the region-specific endpoint to avoid 307 redirects
            if self.region != 'us-east-1':  # us-east-1 can use generic endpoint
                generic_url = f"https://{self.bucket_name}.s3.amazonaws.com/"
                region_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/"
                response['url'] = response['url'].replace(generic_url, region_url)
            
            logger.info(f"Generated pre-signed POST for key: {s3_key}")
            return response
            
        except ClientError as e:
            logger.error(f"Error generating pre-signed POST: {e}")
            raise
        except NoCredentialsError:
            logger.error("AWS credentials not available")
            raise
    
    def generate_signed_url(self, s3_key: str, expiry: int = 3600) -> str:
        """
        Generate a signed URL for accessing a photo
        
        Args:
            s3_key: S3 object key
            expiry: URL expiry in seconds (default: 1 hour)
        
        Returns:
            Signed URL string
        """
        try:
            # For keys with special characters, we need to be more explicit about the configuration
            config = Config(
                signature_version='s3v4',
                region_name=self.region,
                s3={
                    'addressing_style': 'virtual'
                }
            )
            
            # Create a temporary client with explicit configuration
            temp_client = boto3.client(
                's3',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
                config=config
            )
            
            # Generate signed URL with explicit region endpoint
            url = temp_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiry
            )
            
            logger.debug(f"Generated signed URL for key: {s3_key}")
            return url
            
        except ClientError as e:
            logger.error(f"Error generating signed URL for {s3_key}: {e}")
            raise
    
    def verify_object_exists(self, s3_key: str) -> Optional[Dict]:
        """
        Verify that an object exists in S3 and return its metadata
        
        Args:
            s3_key: S3 object key to verify
        
        Returns:
            Dict with object metadata if exists, None otherwise
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            
            return {
                'file_size': response.get('ContentLength', 0),
                'content_type': response.get('ContentType', ''),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag', '').strip('"'),  # Remove quotes from ETag
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.warning(f"Object not found: {s3_key}")
                return None
            else:
                logger.error(f"Error checking object {s3_key}: {e}")
                raise
    
    def delete_object(self, s3_key: str) -> bool:
        """
        Delete an object from S3
        
        Args:
            s3_key: S3 object key to delete
        
        Returns:
            True if deletion was successful
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Deleted object: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting object {s3_key}: {e}")
            return False
    
    def list_objects_by_prefix(self, prefix: str, max_keys: int = 1000) -> List[Dict]:
        """
        List objects with a given prefix (useful for listing game photos)
        
        Args:
            prefix: S3 key prefix to search for
            max_keys: Maximum number of objects to return
        
        Returns:
            List of object metadata dicts
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            objects = []
            for obj in response.get('Contents', []):
                objects.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj.get('ETag', '').strip('"'),
                })
            
            logger.debug(f"Found {len(objects)} objects with prefix: {prefix}")
            return objects
            
        except ClientError as e:
            logger.error(f"Error listing objects with prefix {prefix}: {e}")
            raise
    
    def get_bucket_info(self) -> Dict:
        """
        Get information about the configured S3 bucket
        Returns bucket name, region, and basic metadata
        """
        try:
            # Check if bucket exists and is accessible
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            
            # Get bucket location
            location_response = self.s3_client.get_bucket_location(Bucket=self.bucket_name)
            bucket_region = location_response.get('LocationConstraint') or 'us-east-1'
            
            return {
                'bucket_name': self.bucket_name,
                'region': bucket_region,
                'configured_region': self.region,
                'accessible': True
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Error accessing bucket {self.bucket_name}: {e}")
            
            return {
                'bucket_name': self.bucket_name,
                'region': self.region,
                'accessible': False,
                'error': error_code
            }
    
    def validate_configuration(self) -> Dict:
        """
        Validate S3 configuration and credentials
        Returns status information for troubleshooting
        """
        validation_result = {
            'bucket_configured': bool(self.bucket_name),
            'credentials_configured': bool(self.access_key and self.secret_key),
            'region_configured': bool(self.region),
            'bucket_accessible': False,
            'errors': []
        }
        
        if not validation_result['bucket_configured']:
            validation_result['errors'].append('S3_PHOTOS_BUCKET not configured')
        
        if not validation_result['credentials_configured']:
            validation_result['errors'].append('AWS credentials not configured')
        
        if not validation_result['region_configured']:
            validation_result['errors'].append('S3_REGION not configured')
        
        # Test bucket access if basic config is present
        if validation_result['bucket_configured'] and validation_result['credentials_configured']:
            try:
                bucket_info = self.get_bucket_info()
                validation_result['bucket_accessible'] = bucket_info['accessible']
                
                if not bucket_info['accessible']:
                    validation_result['errors'].append(f"Bucket not accessible: {bucket_info.get('error', 'Unknown error')}")
                
                validation_result['bucket_info'] = bucket_info
                
            except Exception as e:
                validation_result['errors'].append(f"Error testing bucket access: {str(e)}")
        
        validation_result['is_valid'] = (
            validation_result['bucket_configured'] and
            validation_result['credentials_configured'] and
            validation_result['region_configured'] and
            validation_result['bucket_accessible'] and
            len(validation_result['errors']) == 0
        )
        
        return validation_result


def create_s3_service() -> S3PhotoService:
    """Factory function to create S3 service instance"""
    return S3PhotoService()
from typing import Any, Dict
from urllib.parse import urlparse
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config


async def generate_presigned_url(
    image_url: str, expiration: int = 3600
) -> Dict[str, Any]:
    """
    Generate a pre-signed URL for any S3 image that follows the structure:
    https://[bucket-name].s3.amazonaws.com/[path-to-image]

    Args:
        image_url: S3 URL of the image
        expiration: Time in seconds until the pre-signed URL expires (default: 1 hour)

    Returns:
        Dictionary containing status, pre-signed URL (if successful), and error (if unsuccessful)
    """
    result = {"status": "error", "url": None, "error": None}

    if not image_url:
        result["error"] = "No image URL provided"

        return result

    try:
        # Parse the URLgenerate_presigned_url
        parsed_url = urlparse(image_url)

        if not parsed_url.netloc.endswith("amazonaws.com"):
            result["error"] = f"URL does not appear to be an S3 URL: {image_url}"

            return result

        # Extract bucket name from the hostname
        # The format is: bucket-name.s3.amazonaws.com
        bucket_name = parsed_url.netloc.split(".s3.")[0]

        # Extract the object key (everything after the hostname)
        object_key = parsed_url.path.lstrip("/")

        if not bucket_name or not object_key:
            result["error"] = f"Could not parse bucket and key from URL: {image_url}"

            return result

        # Log the attempt for debugging
        try:
            # Create an S3 client with signature version 4
            s3_client = boto3.client("s3", config=Config(signature_version="s3v4"))

            # Generate the pre-signed URL
            presigned_url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket_name, "Key": object_key},
                ExpiresIn=expiration,
            )

            result["status"] = "success"

            result["url"] = presigned_url

            return result

        except ClientError as ce:
            error_code = ce.response.get("Error", {}).get("Code", "Unknown")

            if error_code == "AccessDenied":
                result["error"] = (
                    f"Access denied when generating pre-signed URL. Check IAM permissions for bucket '{bucket_name}'"
                )

            else:
                result["error"] = f"S3 client error: {str(ce)}"

            return result

    except Exception as e:
        result["error"] = f"Error generating pre-signed URL: {str(e)}"

        return result

import os
import uuid
import logging
import requests
from io import BytesIO
from typing import Optional, Any, Dict
import boto3
from elevenlabs import VoiceSettings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024  # Chunk size for reading the response

def get_s3_client(
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    aws_region_name: Optional[str] = None,
) -> boto3.client:
    """
    Initializes the AWS S3 client.
    """
    aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region_name = aws_region_name or os.getenv("AWS_REGION_NAME")

    if not all([aws_access_key_id, aws_secret_access_key, aws_region_name]):
        raise ValueError("AWS credentials not provided and not set in environment variables.")

    session = boto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region_name,
    )
    return session.client("s3")


def upload_audio_stream_to_s3(
    audio_stream: BytesIO,
    s3_client,
    bucket_name: str,
    s3_file_name: str,
    s3_output_folder: Optional[str] = None,
) -> None:
    """
    Uploads the audio stream to AWS S3.
    """
    audio_stream.seek(0)

    # Combine output folder and filename if folder is provided
    if s3_output_folder:
        s3_file_name = os.path.join(s3_output_folder, s3_file_name)

    s3_client.upload_fileobj(audio_stream, bucket_name, s3_file_name)
    logger.info(f"Audio file uploaded to S3 bucket {bucket_name} with key {s3_file_name}")


def generate_presigned_url(
    s3_client,
    bucket_name: str,
    s3_file_name: str,
    expires_in: int = 3600,
) -> str:
    """
    Generates a presigned URL for the S3 object.
    """
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": s3_file_name},
        ExpiresIn=expires_in,
    )


def convert_voice_settings(voice_settings: Any) -> Dict[str, Any]:
    """
    Converts a VoiceSettings object to a dictionary, if applicable.
    """
    if isinstance(voice_settings, VoiceSettings):
        return {
            "stability": voice_settings.stability,
            "similarity_boost": voice_settings.similarity_boost,
            "style": voice_settings.style,
            "use_speaker_boost": voice_settings.use_speaker_boost,
        }
    return voice_settings


def download_audio_from_elevenlabs(
    elevenlabs_api_key: str,
    voice_id: str,
    **kwargs
) -> BytesIO:
    """
    Makes a request to the ElevenLabs API to convert text to speech and streams the audio.
    """
    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {
        "Accept": "application/json",
        "xi-api-key": elevenlabs_api_key
    }

    try:
        response = requests.post(tts_url, headers=headers, json=kwargs, stream=True)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error during text-to-speech conversion: {e}")
        raise

    audio_stream = BytesIO()
    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
        if chunk:
            audio_stream.write(chunk)

    return audio_stream, response.headers.get('request-id', uuid.uuid4())


def save_audio_locally(
    audio_stream: BytesIO,
    output_folder: str,
    filename: str
) -> str:
    """
    Saves the audio stream locally to the specified folder.
    """
    os.makedirs(output_folder, exist_ok=True)
    filepath = os.path.join(output_folder, filename)

    with open(filepath, "wb") as f:
        f.write(audio_stream.getvalue())

    logger.info(f"Audio file saved locally at {filepath}")
    return filepath


def text_to_speech(
    output_folder: Optional[str] = None,
    elevenlabs_api_key: Optional[str] = None,
    aws_s3_bucket_name: Optional[str] = None,
    aws_s3_output_folder: Optional[str] = None,
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    aws_region_name: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Convert text to speech and save/upload the audio file to AWS S3 or locally based on provided parameters.
    """
    elevenlabs_api_key = elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY")
    if not elevenlabs_api_key:
        raise ValueError("ELEVENLABS_API_KEY not provided and not set in environment variables.")

    # Ensure required parameters are present
    for param in ["text", "voice_id"]:
        if param not in kwargs:
            raise ValueError(f"Missing required parameter: {param}")

    if "voice_settings" in kwargs:
        kwargs["voice_settings"] = convert_voice_settings(kwargs["voice_settings"])

    # Get the audio stream from ElevenLabs API
    audio_stream, request_id = download_audio_from_elevenlabs(elevenlabs_api_key, **kwargs)
    filename = f"{request_id}.mp3"

    result = {"id": request_id}

    # Check if AWS S3 credentials and bucket name are provided
    aws_s3_auth_provided = all(
        [
            aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_region_name or os.getenv("AWS_REGION_NAME"),
            aws_s3_bucket_name or os.getenv("AWS_S3_BUCKET_NAME"),
        ]
    )

    # Save locally if output_folder is provided
    if output_folder:
        result["file_name"] = save_audio_locally(audio_stream, output_folder, filename)

    # Upload to S3 if AWS credentials are provided
    if aws_s3_auth_provided:
        s3_client = get_s3_client(aws_access_key_id, aws_secret_access_key, aws_region_name)
        upload_audio_stream_to_s3(audio_stream, s3_client, aws_s3_bucket_name, filename, aws_s3_output_folder)

        s3_file_key = os.path.join(aws_s3_output_folder or "", filename)
        signed_url = generate_presigned_url(s3_client, aws_s3_bucket_name, s3_file_key)
        
        result.update({
            "s3_file_name": s3_file_key,
            "s3_bucket_name": aws_s3_bucket_name,
            "s3_presigned_url": signed_url,
        })

    return result

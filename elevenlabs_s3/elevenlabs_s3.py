import os
import uuid
import logging
from io import BytesIO
from typing import Optional, Any, Dict

from elevenlabs import ElevenLabs, VoiceSettings
import boto3

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_elevenlabs_client(elevenlabs_api_key: Optional[str] = None) -> ElevenLabs:
    """
    Initializes the ElevenLabs client.

    Args:
        elevenlabs_api_key (Optional[str]): ElevenLabs API key.

    Returns:
        ElevenLabs: An instance of the ElevenLabs client.
    """
    elevenlabs_api_key = elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY")
    if not elevenlabs_api_key:
        raise ValueError("ELEVENLABS_API_KEY not provided and not set in environment variables.")
    return ElevenLabs(api_key=elevenlabs_api_key)


def get_s3_client(
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    aws_region_name: Optional[str] = None,
) -> boto3.client:
    """
    Initializes the AWS S3 client.

    Args:
        aws_access_key_id (Optional[str]): AWS Access Key ID.
        aws_secret_access_key (Optional[str]): AWS Secret Access Key.
        aws_region_name (Optional[str]): AWS Region Name.

    Returns:
        boto3.client: An instance of the S3 client.
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
) -> None:
    """
    Uploads the audio stream to AWS S3.

    Args:
        audio_stream (BytesIO): The audio stream to upload.
        s3_client: The S3 client.
        bucket_name (str): The S3 bucket name.
        s3_file_name (str): The name of the file in S3.
    """
    audio_stream.seek(0)
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

    Args:
        s3_client: The S3 client.
        bucket_name (str): The S3 bucket name.
        s3_file_name (str): The name of the file in S3.
        expires_in (int): Time in seconds for the presigned URL to remain valid.

    Returns:
        str: The presigned URL.
    """
    signed_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": s3_file_name},
        ExpiresIn=expires_in,
    )
    return signed_url


def text_to_speech(
    text: str,
    output_folder: Optional[str] = None,
    elevenlabs_api_key: Optional[str] = None,
    aws_s3_bucket_name: Optional[str] = None,
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    aws_region_name: Optional[str] = None,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
    voice_settings: Optional[VoiceSettings] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Convert text to speech and save/upload the audio file according to specified parameters.

    Args:
        text (str): The text to convert to speech.
        output_folder (Optional[str]): The folder where to save the audio file.
        elevenlabs_api_key (Optional[str]): The ElevenLabs API key.
        aws_s3_bucket_name (Optional[str]): The AWS S3 bucket name.
        aws_access_key_id (Optional[str]): AWS Access Key ID.
        aws_secret_access_key (Optional[str]): AWS Secret Access Key.
        aws_region_name (Optional[str]): AWS Region Name.
        voice_id (Optional[str]): The voice ID to use.
        model_id (Optional[str]): The model ID to use.
        voice_settings (Optional[VoiceSettings]): Voice settings to use.
        **kwargs: Additional keyword arguments to pass to the ElevenLabs text_to_speech function.

    Returns:
        Dict[str, Any]: Information about the saved/uploaded audio file.
    """
    # Initialize ElevenLabs client
    try:
        client = get_elevenlabs_client(elevenlabs_api_key)
    except ValueError as e:
        logger.error(e)
        raise

    # Default parameters
    voice_id = voice_id or "pNInz6obpgDQGcFmaJgB"
    model_id = model_id or "eleven_turbo_v2_5"
    voice_settings = voice_settings or VoiceSettings(
        stability=0.0,
        similarity_boost=1.0,
        style=0.0,
        use_speaker_boost=True,
    )

    # Text-to-speech conversion
    try:
        response = client.text_to_speech.convert(
            voice_id=voice_id,
            optimize_streaming_latency="0",
            output_format="mp3_22050_32",
            text=text,
            model_id=model_id,
            voice_settings=voice_settings,
            **kwargs,
        )
    except Exception as e:
        logger.error(f"Error during text-to-speech conversion: {e}")
        raise

    # Read audio data into BytesIO
    audio_stream = BytesIO()
    for chunk in response:
        if chunk:
            audio_stream.write(chunk)
    audio_stream.seek(0)

    # Check AWS S3 authorization
    aws_s3_auth_provided = all(
        [
            aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_region_name or os.getenv("AWS_REGION_NAME"),
            aws_s3_bucket_name or os.getenv("AWS_S3_BUCKET_NAME"),
        ]
    )

    result = {}

    if output_folder:
        # Output folder is specified
        if aws_s3_auth_provided:
            # Save in both local folder and S3
            filename = f"{uuid.uuid4()}.mp3"
            filepath = os.path.join(output_folder, filename)
            os.makedirs(output_folder, exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(audio_stream.getvalue())
            logger.info(f"Audio file saved at {filepath}")
            result["file_path"] = filepath

            # Upload to S3
            try:
                s3_client = get_s3_client(
                    aws_access_key_id, aws_secret_access_key, aws_region_name
                )
            except ValueError as e:
                logger.error(e)
                raise

            aws_s3_bucket_name = aws_s3_bucket_name or os.getenv("AWS_S3_BUCKET_NAME")
            s3_file_name = filename

            upload_audio_stream_to_s3(
                audio_stream, s3_client, aws_s3_bucket_name, s3_file_name
            )

            signed_url = generate_presigned_url(
                s3_client, aws_s3_bucket_name, s3_file_name
            )

            logger.info(f"Presigned URL: {signed_url}")

            result.update(
                {
                    "s3_file_name": s3_file_name,
                    "s3_bucket_name": aws_s3_bucket_name,
                    "s3_presigned_url": signed_url,
                }
            )
        else:
            # Save only in local folder
            filename = f"{uuid.uuid4()}.mp3"
            filepath = os.path.join(output_folder, filename)
            os.makedirs(output_folder, exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(audio_stream.getvalue())
            logger.info(f"Audio file saved at {filepath}")
            result["file_path"] = filepath
    else:
        # Output folder not specified
        if aws_s3_auth_provided:
            # Save only to S3
            try:
                s3_client = get_s3_client(
                    aws_access_key_id, aws_secret_access_key, aws_region_name
                )
            except ValueError as e:
                logger.error(e)
                raise

            aws_s3_bucket_name = aws_s3_bucket_name or os.getenv("AWS_S3_BUCKET_NAME")
            filename = f"{uuid.uuid4()}.mp3"
            s3_file_name = filename

            upload_audio_stream_to_s3(
                audio_stream, s3_client, aws_s3_bucket_name, s3_file_name
            )

            signed_url = generate_presigned_url(
                s3_client, aws_s3_bucket_name, s3_file_name
            )

            logger.info(f"Presigned URL: {signed_url}")

            result.update(
                {
                    "s3_file_name": s3_file_name,
                    "s3_bucket_name": aws_s3_bucket_name,
                    "s3_presigned_url": signed_url,
                }
            )
        else:
            # Save in default folder
            output_folder = "."
            filename = f"{uuid.uuid4()}.mp3"
            filepath = os.path.join(output_folder, filename)
            with open(filepath, "wb") as f:
                f.write(audio_stream.getvalue())
            logger.info(f"Audio file saved at {filepath}")
            result["file_path"] = filepath

    return result

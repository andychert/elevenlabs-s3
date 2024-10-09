# ElevenLabs S3 Package

This package combines the ElevenLabs text-to-speech functionality with AWS S3 uploading capabilities.

## Installation

```bash
pip install elevenlabs_s3
```

## Usage

```python
from elevenlabs_s3 import VoiceSettings, text_to_speech

# Call the function
result = text_to_speech(
    text="Hello, this is a test.",
    elevenlabs_api_key="YOUR_ELEVENLABS_API_KEY",
    output_folder="audio_files", # Specify if you want to save locally
    aws_s3_bucket_name="your-s3-bucket", # Specify if you want to upload to S3
    aws_access_key_id="YOUR_AWS_ACCESS_KEY_ID",
    aws_secret_access_key="YOUR_AWS_SECRET_ACCESS_KEY",
    aws_region_name="YOUR_AWS_REGION",
    voice_id="YOUR_VOICE_ID",
    voice_settings=VoiceSettings(
        stability=0.1,
        similarity_boost=0.3,
        style=0.2,
    )
)

print(result)

```

## Rules

- If the folder where to save the audio file is specified and AWS S3 authorization data is not specified, then save only in the folder.
- If the folder where to save the audio file and AWS S3 authorization data is specified, then save in S3 and in the folder.
- If no folder is specified where to save the audio file and AWS S3 authorization data is specified, save only to S3.
- If no folder is specified where to save the audio file and AWS S3 authorization data is not specified, save only in the default folder.

## License

This project is licensed under the MIT License.

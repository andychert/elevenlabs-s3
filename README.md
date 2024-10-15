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
    voice_id="YOUR_VOICE_ID"
    output_folder="local_files", # Specify if you want to save locally
    # Specify if you want to upload to S3
    aws_s3_output_folder="s3_files",
    aws_s3_bucket_name="your-s3-bucket",
    aws_access_key_id="YOUR_AWS_ACCESS_KEY_ID",
    aws_secret_access_key="YOUR_AWS_SECRET_ACCESS_KEY",
    aws_region_name="YOUR_AWS_REGION",
)

print(result)

"""
Elevenlabs ID: `I8xNqL3yp2LqoGrqUdyV`
Example: `previous_request_ids=["I8xNqL3yp2LqoGrqUdyV"]`

{
   "id": "I8xNqL3yp2LqoGrqUdyV",
   "file_name":"local_files/I8xNqL3yp2LqoGrqUdyV.mp3",
   "s3_file_name":"s3_files/I8xNqL3yp2LqoGrqUdyV.mp3",
   "s3_bucket_name":"mybucket",
   "s3_presigned_url":"https://mybucket.s3.amazonaws.com/I8xNqL3yp2LqoGrqUdyV.mp3?AWSAccessKeyId=AKIAVY2PHBT7JH2FX7K2&Signature=DGDRWa6GJeTXIyhihW%2BOEymTTpo%3D&Expires=1728922077"
}
"""

```

## Rules

- If the folder where to save the audio file is specified and AWS S3 authorization data is not specified, then save only in the folder.
- If the folder where to save the audio file and AWS S3 authorization data is specified, then save in S3 and in the folder.
- If no folder is specified where to save the audio file and AWS S3 authorization data is specified, save only to S3.
- If no folder is specified where to save the audio file and AWS S3 authorization data is not specified, save only in the default folder.

## License

This project is licensed under the MIT License.

from elevenlabs_s3 import text_to_speech

result = text_to_speech(
    text="Hello, this is a test.",
    voice_id="Alice"
)

print(result)
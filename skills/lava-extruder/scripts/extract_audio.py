#!/usr/bin/env python3
"""
extract_audio.py — Transcribe audio files (.mp3, .wav, .m4a, .mp4, .ogg, .flac) to Markdown.
Usage: extract_audio.py <input_audio> [output.md]

Implements the user-approved dual-fallback pipeline:
1. Tier 1: OpenAI Whisper (CLI 'whisper' or python 'whisper' library) for local high-accuracy transcription.
2. Tier 2: Python 'speech_recognition' library (Google Speech Recognition / Sphinx) as lightweight speech fallback.
3. Tier 3: Metadata extraction via ffprobe/ffmpeg/exiftool (duration, sample rate, channels, format) if no speech engine is available.
"""

import sys
import os
import subprocess
import tempfile
import json


def get_audio_metadata(input_path: str) -> dict:
    meta = {}
    # Try ffprobe
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", input_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            fmt = data.get("format", {})
            if "duration" in fmt:
                dur_sec = float(fmt["duration"])
                mins, secs = divmod(dur_sec, 60)
                meta["Duration"] = f"{int(mins)}m {int(secs)}s ({dur_sec:.1f}s)"
            if "format_long_name" in fmt:
                meta["Format"] = fmt["format_long_name"]
            if "bit_rate" in fmt:
                meta["Bitrate"] = f"{int(fmt['bit_rate']) // 1000} kbps"
            for st in data.get("streams", []):
                if st.get("codec_type") == "audio":
                    meta["Codec"] = st.get("codec_name", "")
                    meta["Channels"] = st.get("channels", "")
                    meta["SampleRate"] = f"{st.get('sample_rate', '')} Hz"
                    break
            return meta
    except Exception:
        pass

    # Try exiftool
    try:
        res = subprocess.run(["exiftool", "-s3", "-Duration", input_path], capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            meta["Duration"] = res.stdout.strip()
    except Exception:
        pass

    return meta


def transcribe_via_whisper(input_path: str) -> str | None:
    # 1. Try python whisper package
    try:
        import whisper
        print("Transcribing with OpenAI Whisper (Python)...", file=sys.stderr)
        model = whisper.load_model("base")
        result = model.transcribe(input_path)
        text = result.get("text", "").strip()
        if text:
            return text
    except ImportError:
        pass
    except Exception as e:
        print(f"Notice: Python whisper error: {e}", file=sys.stderr)

    # 2. Try whisper CLI
    if subprocess.run(["which", "whisper"], capture_output=True).returncode == 0:
        print("Transcribing with OpenAI Whisper CLI...", file=sys.stderr)
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = ["whisper", input_path, "--output_format", "txt", "--output_dir", tmpdir, "--model", "base"]
            res = subprocess.run(cmd, capture_output=True)
            base = os.path.splitext(os.path.basename(input_path))[0]
            txt_file = os.path.join(tmpdir, f"{base}.txt")
            if os.path.exists(txt_file):
                with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
                if content:
                    return content

    return None


def transcribe_via_speech_recognition(input_path: str) -> str | None:
    try:
        import speech_recognition as sr
        from pydub import AudioSegment

        print("Transcribing with SpeechRecognition fallback...", file=sys.stderr)
        # Convert audio to wav if not already wav
        r = sr.Recognizer()
        ext = os.path.splitext(input_path)[1].lower()

        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp_wav:
            if ext != ".wav":
                sound = AudioSegment.from_file(input_path)
                sound.export(tmp_wav.name, format="wav")
                wav_path = tmp_wav.name
            else:
                wav_path = input_path

            with sr.AudioFile(wav_path) as source:
                audio_data = r.record(source)
                try:
                    text = r.recognize_google(audio_data)
                    if text:
                        return text
                except sr.UnknownValueError:
                    return "*(SpeechRecognition could not understand audio)*"
                except sr.RequestError as e:
                    print(f"SpeechRecognition API request failed: {e}", file=sys.stderr)
    except ImportError:
        pass
    except Exception as e:
        print(f"SpeechRecognition error: {e}", file=sys.stderr)

    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_audio.py <input_audio> [output.md]", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else f"{input_path}.extracted.md"

    if not os.path.isfile(input_path):
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    basename = os.path.basename(input_path)
    title = os.path.splitext(basename)[0]

    # 1. Metadata
    meta = get_audio_metadata(input_path)

    # 2. Transcribe
    transcript = transcribe_via_whisper(input_path)
    used_method = "OpenAI Whisper"

    if not transcript:
        transcript = transcribe_via_speech_recognition(input_path)
        used_method = "SpeechRecognition"

    # 3. Format Markdown
    md_lines = [
        f"# Audio: {title}\n",
        f"- **File:** `{basename}`",
    ]
    for k, v in meta.items():
        md_lines.append(f"- **{k}:** {v}")

    md_lines.append("\n---\n")
    md_lines.append("## Audio Transcript\n")

    if transcript:
        md_lines.append(f"*(Transcribed via {used_method})*\n")
        md_lines.append(transcript)
    else:
        md_lines.append("*(No speech transcription available)*\n")
        md_lines.append("To enable audio transcription, install one of:\n")
        md_lines.append("- `pip install openai-whisper` (Recommended, high-accuracy local speech-to-text)\n")
        md_lines.append("- `pip install SpeechRecognition pydub` (Lightweight fallback)")

    final_md = "\n".join(md_lines).strip() + "\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_md)

    lines = len(final_md.splitlines())
    print(f"Done. Extracted audio notes ({lines} lines) to {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

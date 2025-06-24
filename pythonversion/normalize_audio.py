import os
from pydub import AudioSegment

class AudioNormalizer:
    def __init__(self, target_dbfs: float = -30.0, reduce_db: float = -6.0):
        self.target_dbfs = target_dbfs
        self.reduce_db = reduce_db

    def normalize_audio_file(self, file_path: str):
        if not file_path.lower().endswith(('.mp3', '.wav')):
            print(f"Ignoriere: {file_path}")
            return

        print(f"Bearbeite: {file_path}")

        # Lade Audio
        if file_path.lower().endswith('.mp3'):
            audio = AudioSegment.from_mp3(file_path)
        else:
            audio = AudioSegment.from_wav(file_path)

        # Normalisieren auf Ziel-dBFS
        normalized = self._match_target_amplitude(audio, self.target_dbfs)

        # Lautstärke weiter reduzieren (~50%)
        final_audio = normalized.apply_gain(self.reduce_db)

        # Speichern (überschreibt Original)
        output_format = "mp3" if file_path.lower().endswith('.mp3') else "wav"
        final_audio.export(file_path, format=output_format)

        print(f"✓ Fertig: {file_path}")

    def normalize_folder(self, folder_path: str):
        for filename in os.listdir(folder_path):
            path = os.path.join(folder_path, filename)
            if os.path.isfile(path):
                self.normalize_audio_file(path)

    def _match_target_amplitude(self, sound: AudioSegment, target_dBFS: float) -> AudioSegment:
        change_in_dBFS = target_dBFS - sound.dBFS
        return sound.apply_gain(change_in_dBFS)

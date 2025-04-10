import os
from pathlib import Path
from faster_whisper import WhisperModel
from moviepy.editor import VideoFileClip, concatenate_videoclips
import numpy as np
import cv2
import datetime
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def detect_scene_changes(video_path, threshold=30):
    """비디오에서 장면 전환을 감지합니다."""
    cap = cv2.VideoCapture(video_path)
    prev_frame = None
    scene_changes = []
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if prev_frame is not None:
            # 프레임 간 차이 계산
            diff = cv2.absdiff(frame, prev_frame)
            diff_mean = np.mean(diff)
            
            # 장면 전환 감지
            if diff_mean > threshold:
                scene_changes.append(frame_count)
                
        prev_frame = frame.copy()
        frame_count += 1
        
    cap.release()
    return scene_changes

def generate_subtitles(video_path, output_srt_path):
    """Whisper를 사용하여 자막을 생성합니다."""
    # Whisper 모델 설정
    model_name = os.getenv('WHISPER_MODEL', 'base')
    device = os.getenv('WHISPER_DEVICE', 'cpu')
    compute_type = os.getenv('WHISPER_COMPUTE_TYPE', 'int8')
    
    # Whisper 모델 로드
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    
    # 음성 인식 수행
    segments, _ = model.transcribe(video_path, language="ko")
    
    # SRT 파일 생성
    with open(output_srt_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments, start=1):
            start = str(datetime.timedelta(seconds=int(segment.start)))
            end = str(datetime.timedelta(seconds=int(segment.end)))
            
            # SRT 형식으로 작성
            f.write(f"{i}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{segment.text}\n\n")
    
    return output_srt_path

def process_video(video_path):
    """비디오를 처리하여 자동 컷 편집과 자막을 생성합니다."""
    # 출력 디렉토리 생성
    output_dir = Path(os.getenv('OUTPUT_DIR', 'outputs'))
    output_dir.mkdir(exist_ok=True)
    
    # 파일명 추출
    video_name = Path(video_path).stem
    
    # 장면 전환 감지
    scene_changes = detect_scene_changes(video_path)
    
    # 비디오 클립 로드
    video = VideoFileClip(video_path)
    
    # 장면별로 비디오 분할
    clips = []
    start_time = 0
    
    for change in scene_changes:
        end_time = change / video.fps
        clip = video.subclip(start_time, end_time)
        clips.append(clip)
        start_time = end_time
    
    # 마지막 장면 추가
    if start_time < video.duration:
        clips.append(video.subclip(start_time, video.duration))
    
    # 비디오 합치기
    final_video = concatenate_videoclips(clips)
    
    # 편집된 비디오 저장
    output_video_path = str(output_dir / f"{video_name}_edited.mp4")
    final_video.write_videofile(output_video_path, codec='libx264')
    
    # 자막 생성
    output_srt_path = str(output_dir / f"{video_name}_subtitles.srt")
    generate_subtitles(video_path, output_srt_path)
    
    # 리소스 정리
    video.close()
    final_video.close()
    
    return {
        'video_path': output_video_path,
        'subtitle_path': output_srt_path
    }
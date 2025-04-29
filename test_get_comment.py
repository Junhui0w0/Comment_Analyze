import func_GetComments

# 동영상 ID 입력
video_id = "Zwyo_QaQncM"  # 실제 동영상 ID로 교체
top_20 = func_GetComments.get_top_comments(video_id)
print('\n'.join(top_20))

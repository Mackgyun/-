# 노트북을 서버로 쓰기 위한 전원 설정 (전원 연결 시에만 적용, 배터리일 때는 기존 절전 유지)
# 관리자 권한 PowerShell에서 실행
powercfg /change standby-timeout-ac 0      # 전원 연결 시 절전 안 함
powercfg /change hibernate-timeout-ac 0    # 전원 연결 시 최대 절전 안 함
powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0   # 전원 연결 시 덮개 닫아도 아무것도 안 함
powercfg /setactive SCHEME_CURRENT
Write-Host "전원 설정 완료. 덮개를 닫을 때는 반드시 전원을 연결해 두세요."
Write-Host "Windows Update는 '사용 시간'을 설정해 업무 시간 재부팅을 피하고, 재부팅돼도 자동 실행이 다시 켭니다."

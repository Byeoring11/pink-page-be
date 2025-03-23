import sys
import os
import asyncio
import re

# 현재 스크립트 기준으로 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.infrastructures.ssh import (
    SSHConnectionConfig, SSHCredential, SSHClientImpl, SSHConnectionError,
    SFTPClientImpl
)


async def test_ssh():
    ssh_client = SSHClientImpl()
    sftp_client = SFTPClientImpl(ssh_client)
    credential = SSHCredential(
        host='localhost',
        port=2222,
        username='root',
        password='root'
    )

    params = SSHConnectionConfig(
        credential=credential
    )

    try:
        await ssh_client.connect(params)
        print("SSH 연결 성공!")
        await sftp_client.connect(params)
        print("SFTP 연결 성공!")
        shell = await ssh_client.create_shell()
        print("인터랙티브 Shell 생성 성공!")
        ##################################################################################
        # result = await ssh_client.execute_command("ls -al")
        # print(result)
        # result = await ssh_client.execute_command("cd .. && ls -al")
        # print(result)
        # result = await ssh_client.execute_command("ls -al")
        # print(result)
        ##################################################################################

        # await sftp_client.upload_file("C:\\Projects\\pink-page\\pp-backend-fastapi\\app\\main.py", "/root/main.py")
        # await sftp_client.upload_directory("C:/Projects/pink-page/pp-backend-fastapi/app/api", "/root/api")
        # await sftp_client.download_file("/root/api/dependencies.py", "C:\\Users\\jihye\\Downloads\\TTest\\test.py")
        # list = await sftp_client.list_directory("/root")
        await shell.send_command('./long_running_script.sh')
        
        # 완료 감지를 위한 변수
        complete_output = ""
        start_time = asyncio.get_event_loop().time()
        command_completed = False
        
        # 스트리밍 방식으로 출력 읽기
        async for chunk in shell.read_stream():
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - start_time
            
            # 출력 누적 및 표시
            complete_output += chunk
            print(f"[{elapsed:.1f}초] 수신: {chunk}", end="")
            
            # 명령어 완료 감지 (프롬프트가 다시 나타남)
            if "작업 완료!" in chunk and re.search(shell._prompt, chunk):
                print(f"\n\n명령어 실행이 완료되었습니다! (경과 시간: {elapsed:.1f}초)")
                command_completed = True
                break
                
            # 대체 종료 조건: 프롬프트만 확인
            if re.search(shell._prompt, chunk):
                print(f"\n\n프롬프트가 감지되었습니다. 명령어가 완료된 것 같습니다. (경과 시간: {elapsed:.1f}초)")
                command_completed = True
                break
            
            # 타임아웃 체크 (예: 180초 이상 걸리면 강제 종료)
            if elapsed > 180:
                print("\n\n타임아웃: 명령어가 너무 오래 실행되고 있습니다. 중단합니다.")
                await shell.send_command("\x03")  # Ctrl+C 전송
                break
        
        if command_completed:
            print("명령어가 성공적으로 완료되었습니다.")
        else:
            print("명령어가 정상적으로 완료되지 않았습니다.")
        
        # 추가 명령어로 제대로 작동하는지 확인
        print("\n추가 명령어 테스트...")
        await shell.send_command("echo '쉘이 여전히 작동합니다!'")
        confirmation = await shell.read_output(timeout=5.0)
        print(f"확인 메시지: {confirmation}")

        await shell.close_shell()
        print("인터랙티브 Shell 종료 성공!")
    except SSHConnectionError as e:
        print(f"SSH 연결 실패: {e}")
    finally:
        await sftp_client.disconnect()
        print("SFTP 연결 종료됨.")
        await ssh_client.disconnect()
        print("SSH 연결 종료됨.")

if __name__ == "__main__":
    asyncio.run(test_ssh())  # 비동기 실행 유지

import sys
import os
import asyncio

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
        list = await sftp_client.list_directory("/root")
        print(list)
    except SSHConnectionError as e:
        print(f"SSH 연결 실패: {e}")
    finally:
        await sftp_client.disconnect()
        print("SFTP 연결 종료됨.")
        await ssh_client.disconnect()
        print("SSH 연결 종료됨.")

if __name__ == "__main__":
    asyncio.run(test_ssh())  # 비동기 실행 유지

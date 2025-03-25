import asyncio
from fastapi import WebSocket
from app.infrastructures.websocket.services.websocket_service import WebSocketService
from app.infrastructures.ssh import SSHClientImpl, SSHConnectionConfig, SSHConnectionError, SSHCommandError
from app.domains.deud.schemas.websocket_task_schema import TaskLogMessage
from app.domains.deud.schemas.ssh_schema import SSHServerCommandProfile
from app.core.logger import logger
from app.core.config import settings


class DeudSSHService:
    SERVER_PROFILES: dict[int, SSHServerCommandProfile] = {
        1: SSHServerCommandProfile(
            name="wdexgm1p",
            setup_steps=[
                {"command": "wd", "expect": "choice please :"},
                {"command": "2", "delay": 1.0}
            ],
            command_builder=lambda cusno_list: f"vmyp_postgresql_dat_ddts.sh {','.join(cusno_list)}",
            success_indicator="[SUCC] PostgreSQL load data unload Process"
        ),
        2: SSHServerCommandProfile(
            name="edwap1t",
            setup_steps=[
                {"command": "2", "delay": 1.0}
            ],
            command_builder=lambda _: "vmyp_postgresql_dat_transfer.sh",
            success_indicator="[SUCC] PostgreSQL load data transfer Process"
        ),
        3: SSHServerCommandProfile(
            name="mypap1d",
            setup_steps=[],
            command_builder=lambda _: "sh bmyp_postgresql_dat_odst.sh",
            success_indicator="[SUCC] PostgreSQL load data odst Process"
        )
    }

    def __init__(self, websocket_service: WebSocketService):
        self._websocket_service = websocket_service
        self._ssh = SSHClientImpl()

    async def execute_shell_controller(self, websocket: WebSocket, server_type: int, cusno_list: list[str]) -> None:
        if (profile := self.SERVER_PROFILES.get(server_type)) is None:
            raise ValueError(f"Invalid server type: {server_type}")

        try:
            await self._establish_connection(server_type)
            await self._execute_server_operations(websocket, profile, cusno_list)
        except SSHConnectionError as e:
            raise e
        except SSHCommandError as e:
            raise e
        finally:
            await self._ssh.disconnect()

    async def _establish_connection(self, server_type: int) -> None:
        """SSH 연결"""
        config = SSHConnectionConfig(
            host=settings.SERVERS[server_type],
            username=settings.HIWARE_ID,
            password=settings.HIWARE_PW
        )

        await self._ssh.connect(config)

    async def _execute_server_operations(self, websocket: WebSocket, profile: SSHServerCommandProfile, cusno_list: list[str]) -> None:
        """인터랙티브 Shell 연결 및 커맨드 실행
        1. 서버 셋업
        2. 대응답 커맨드 실행
        """
        command = profile.command_builder(cusno_list)

        async with self._ssh.create_shell() as shell:
            await self._execute_setup_sequence(shell, profile)
            await self._execute_main_command(shell, websocket, profile, command)

    async def _execute_setup_sequence(self, shell, profile: SSHServerCommandProfile) -> None:
        """대응답 커맨드 실행 전 서버 셋업
        wdexgm1p: wd -> expect("choice please:") -> 2 -> delay 1s
        edwap1t: 2 -> delay 1s
        """
        for step in profile.setup_steps:
            await shell.send_command(step["command"])

            if expect_pattern := step.get("expect"):
                await shell.expect(expect_pattern)

            if delay := step.get("delay"):
                await asyncio.sleep(delay)

    async def _execute_main_command(self, shell, websocket: WebSocket, profile: SSHServerCommandProfile, command: str) -> None:
        """대응답 커맨드 실행 및 chunk 실시간 웹소켓 전송"""
        await shell.send_command(command)

        start_time = asyncio.get_event_loop().time()
        success_flag = False

        async for output_chunk in shell.read_stream():
            await self._handle_output_chunk(
                websocket=websocket,
                profile=profile,
                chunk=output_chunk,
                start_time=start_time,
                success_flag=success_flag,
                success_indicator=profile.success_indicator
            )

            if profile.success_indicator in output_chunk:
                success_flag = True
                break

    async def _handle_output_chunk(
        self,
        websocket: WebSocket,
        profile: SSHServerCommandProfile,
        chunk: str,
        start_time: float,
        success_flag: bool,
        success_indicator: str
    ) -> None:
        """실시간 output chunk 클라이언트 웹소켓 전송"""
        elapsed = asyncio.get_event_loop().time() - start_time

        log_data = {
            "server": profile.name,
            "elapsed": f"{elapsed:.2f}s",
            "chunk": chunk.strip()
        }

        if success_indicator in chunk:
            logger.info("대응답 Shell 실행 완료")
        elif not success_flag:
            logger.debug("대응답 Shell 실행 중", **log_data)

        await self._websocket_service.send_message(
            websocket,
            TaskLogMessage(
                serverType=profile.name,
                value={"message": chunk.strip()}
            )
        )

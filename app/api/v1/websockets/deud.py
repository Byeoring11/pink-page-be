from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from app.infrastructures.websocket.services.websocket_service import WebSocketService
from app.domains.deud.services.task_coordinator import TaskCoordinator
from app.domains.deud.schemas.deud_schema import ActionType
from app.core.logger import logger
from app.api.dependencies import (
    get_websocket_service,
    get_task_coordinator
)

router = APIRouter()


@router.websocket("/deud")
async def deud_websocket_endpoint(
    websocket: WebSocket,
    websocket_service: WebSocketService = Depends(get_websocket_service),
    task_coordinator: TaskCoordinator = Depends(get_task_coordinator)
):
    """
    DEUD 모듈 웹소켓 엔드포인트

    라우터는 연결 관리와 메시지 라우팅만 담당하고
    실제 비즈니스 로직은 서비스/코디네이터에 위임
    """
    await websocket_service.connect(websocket)
    await task_coordinator.inform_task_state(websocket)

    try:
        while True:
            # 클라이언트 메시지 수신
            client_message = await websocket_service.receive_message(websocket)
            logger.info(f"Received message: {client_message}")

            # 메시지 타입에 따른 처리 라우팅
            if client_message.action == ActionType.START_TASK:
                await task_coordinator.process_start_request(
                    websocket,
                    client_message.serverType,
                    client_message.cusnoList
                )

            elif client_message.action == ActionType.CANCEL_TASK:
                await task_coordinator.process_cancel_request(
                    websocket,
                    client_message.serverType
                )

            elif client_message.action == ActionType.GET_STATUS:
                # 상태 조회 기능은 필요시 추가
                pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {id(websocket)}")

        # 클라이언트 연결 해제 처리
        await task_coordinator.handle_client_disconnect(websocket)

        # 웹소켓 등록 해제
        await websocket_service.disconnect(websocket)

    except Exception as e:
        logger.error(f"Unhandled exception in websocket endpoint: {str(e)}")

        # 오류 발생 시 정리 작업
        await task_coordinator.handle_client_disconnect(websocket)
        await websocket_service.disconnect(websocket)

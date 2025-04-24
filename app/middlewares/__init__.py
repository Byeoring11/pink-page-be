from typing import List
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from .session_context import SessionContextMiddleware


def setup_middlewares() -> List[Middleware]:
    middlewares = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],     # 허용할 오리진 목록
            allow_credentials=True,  # 쿠키, 인증 정보를 포함한 요청을 허용
            allow_methods=["*"],     # 허용할 HTTP 메서드 (GET, POST, PUT, DELETE 등)
            allow_headers=["*"],     # 허용할 HTTP 헤더
        ),
        Middleware(SessionContextMiddleware)
    ]
    return middlewares


__all__ = [
    'setup_middlewares',
    'SessionContextMiddleware'
]

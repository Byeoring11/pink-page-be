from fastapi import APIRouter

from domain.deud.schema import DeudResponse, DeudRequset

router = APIRouter()


@router.post("/commands", response_model=DeudResponse)
async def invoke_shell_in_server(request: DeudRequset):
    print(request)
    return DeudResponse()